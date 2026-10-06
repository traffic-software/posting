import json
import time
from types import SimpleNamespace

import httpx
import pytest
from langchain_core.tools import ToolException
from langchain_core.utils.function_calling import convert_to_openai_tool

from app.web_research import research_tools


ACCOUNT_ID = "a" * 32
TOKEN = "server-secret-token"


def settings(**overrides):
    values = {
        "enable_web_search": True,
        "cloudflare_account_id": ACCOUNT_ID,
        "cloudflare_api_token": TOKEN,
        "cloudflare_web_search_gateway": "default",
        "cloudflare_web_search_provider": "ceramic",
        "web_search_timeout_seconds": 10,
        "max_web_search_calls": 3,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def tool_for(handler, *, config=None, deadline=None, context=None):
    search = research_tools(
        config or settings(),
        deadline if deadline is not None else time.monotonic() + 60,
        context,
        transport=httpx.MockTransport(handler),
    )[0]
    search.handle_tool_error = False
    return search


def test_openai_compatible_name_payload_and_bounded_results():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.host == "api.cloudflare.com"
        assert request.url.path == (
            f"/client/v4/accounts/{ACCOUNT_ID}/ai/websearch/"
        )
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        return httpx.Response(200, json={"items": [
            {"url": "https://example.com/article", "title": "A", "description": "B"},
            {"url": "http://127.0.0.1/info", "title": "C", "description": "D"},
        ], "metadata": {"query": "public documentation"}})

    search = tool_for(handler)
    schema = convert_to_openai_tool(search)
    assert schema["function"]["name"] == "web-search"
    assert schema["function"]["parameters"]["properties"]["query"]["maxLength"] == 1024

    result = json.loads(search.invoke({"query": "public documentation", "reason": "compare APIs", "limit": 8}))
    assert json.loads(requests[0].content) == {"query": "public documentation", "provider": "ceramic", "limit": 8, "options": {"gateway": {"id": "default"}}}
    assert result["results"] == [{"url": "https://example.com/article", "title": "A", "description": "B"}]
    assert "untrusted" in result["note"].lower()


def test_disabled_or_missing_configuration_never_requests_network():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"results": []})

    disabled = tool_for(handler, config=settings(enable_web_search=False))
    with pytest.raises(ToolException, match="disabled"):
        disabled.invoke({"query": "anything"})
    missing = tool_for(handler, config=settings(cloudflare_account_id="not-an-account-id"))
    with pytest.raises(ToolException, match="configured"):
        missing.invoke({"query": "anything"})
    assert calls == 0


def test_rejects_context_and_credential_queries_without_request():
    calls = 0

    class Context:
        def redact(self, value):
            return value.replace("task-password", "[REDACTED]")

        def check_alive(self):
            pass

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"results": []})

    search = tool_for(handler, context=Context())
    for query in ("task-password", "api_key=abc123456789", "Bearer abcdefghijklmnop"):
        with pytest.raises(ToolException):
            search.invoke({"query": query})
    assert calls == 0


def test_deadline_and_call_cap_prevent_extra_requests():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(500, json={"errors": [{"message": TOKEN}]})

    expired = tool_for(handler, deadline=time.monotonic() - 1)
    with pytest.raises(ToolException, match="time limit"):
        expired.invoke({"query": "anything"})
    capped = tool_for(handler, config=settings(max_web_search_calls=1))
    with pytest.raises(ToolException, match="service request failed"):
        capped.invoke({"query": "first"})
    with pytest.raises(ToolException, match="call limit"):
        capped.invoke({"query": "second"})
    assert calls == 1


def test_malformed_secret_and_oversized_responses_are_safe_and_bounded():
    def malformed(request):
        return httpx.Response(200, content=("x" * (64 * 1024 + 1)))

    search = tool_for(malformed)
    with pytest.raises(ToolException, match="too large") as error:
        search.invoke({"query": "bounded response"})
    assert TOKEN not in str(error.value)

    def result_handler(request):
        return httpx.Response(200, json={"result": {"results": [
            {"url": "https://example.com/?access_token=leak", "title": "bad", "description": "bad"},
            {"url": "http://127.0.0.1/admin", "title": "bad", "description": "bad"},
            {"url": "https://example.net/", "title": "t" * 900, "description": "d" * 3000},
        ]}})

    result = json.loads(tool_for(result_handler).invoke({"query": "safe result"}))
    assert len(result["results"]) == 1
    assert len(result["results"][0]["title"]) == 500
    assert len(result["results"][0]["description"]) == 2000


def test_invalid_provider_response_and_context_secret_are_not_disclosed():
    class Context:
        def redact(self, value):
            return value.replace("context-secret", "[REDACTED]")

        def check_alive(self):
            pass

    def handler(request):
        return httpx.Response(200, json={"result": {"unexpected": TOKEN}})

    with pytest.raises(ToolException, match="invalid response") as error:
        tool_for(handler, context=Context()).invoke({"query": "normal research"})
    assert TOKEN not in str(error.value)
    assert "context-secret" not in str(error.value)


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500])
def test_provider_errors_are_recoverable_in_agent_mode(status):
    def handler(request):
        return httpx.Response(status, json={"errors": [{"message": TOKEN}]})

    search = research_tools(settings(), time.monotonic() + 60, transport=httpx.MockTransport(handler))[0]
    result = search.invoke({"query": "public documentation"})
    assert "service request failed" in result and TOKEN not in result


def test_timeout_and_server_secrets_are_safe():
    requests = []

    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout(TOKEN, request=request)

    search = tool_for(handler)
    with pytest.raises(ToolException, match="credential"):
        search.invoke({"query": TOKEN})
    with pytest.raises(ToolException, match="service request failed") as error:
        search.invoke({"query": "public documentation"})
    assert len(requests) == 1 and TOKEN not in str(error.value)


def test_deadline_expiring_during_response_and_cancelled_context_prevent_results():
    class Context:
        active = True

        def redact(self, value):
            return value

        def check_alive(self):
            if not self.active:
                raise RuntimeError("cancelled")

    ctx = Context()

    def handler(request):
        ctx.active = False
        return httpx.Response(200, json={"items": []})

    with pytest.raises(ToolException, match="no longer active"):
        tool_for(handler, context=ctx).invoke({"query": "public documentation"})


def test_sensitive_result_excerpts_are_omitted():
    def handler(request):
        return httpx.Response(200, json={"items": [{"url": "https://example.com/", "title": "Documentation", "description": "password=private-value"}]})

    result = json.loads(tool_for(handler).invoke({"query": "public documentation"}))
    assert "private-value" not in str(result)
    assert "SENSITIVE EXCERPT OMITTED" in result["results"][0]["description"]
