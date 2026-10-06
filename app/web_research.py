"""Bounded, credential-safe Cloudflare web-search tool."""

from __future__ import annotations

import ipaddress
import json
import re
import time
from contextlib import nullcontext
from typing import Annotated, Any
from urllib.parse import unquote, urlsplit

import httpx
from langchain_core.tools import ToolException, tool
from pydantic import Field


_MAX_RESPONSE_BYTES = 64 * 1024
_MAX_RESULTS = 10
_MAX_URL_LENGTH = 2_048
_MAX_TITLE_LENGTH = 500
_MAX_DESCRIPTION_LENGTH = 2_000
_ACCOUNT_ID = re.compile(r"[0-9a-fA-F]{32}\Z")
_PATH_PART = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_SECRET_LABEL = re.compile(
    r"(?:api[ _-]?key|access[ _-]?token|auth(?:orization)?|bearer|password|passwd|"
    r"secret|credential|client[ _-]?secret|session[ _-]?token|cookie)\s*(?:[:=]|is\s+)",
    re.IGNORECASE,
)
_BEARER_TOKEN = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{8,}\b", re.IGNORECASE)


def _contains_credential(value: str) -> bool:
    """Recognize credentials without trying to interpret ordinary search terms."""
    return bool(
        _SECRET_LABEL.search(value) or _BEARER_TOKEN.search(value)
        or re.search(r"(?i)(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|\b(?:sk|ghp|github_pat)[_-][A-Za-z0-9_-]{10,}|-----BEGIN .*PRIVATE KEY|\b(?=[A-Za-z0-9_-]{40,}\b)(?=[A-Za-z0-9_-]*[0-9])(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]+\b)", value)
    )


def _safe_result_url(value: object) -> str | None:
    if not isinstance(value, str) or not value or len(value) > _MAX_URL_LENGTH:
        return None
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port == 0
        or "\\" in parsed.netloc
        or "%" in host
        or host == "localhost"
        or host.endswith((".localhost", ".local"))
        or _contains_credential(unquote(parsed.query))
    ):
        return None
    try:
        # Do not resolve host names here: search results are data, not fetch targets.
        address = ipaddress.ip_address(host)
    except ValueError:
        return value
    return value if address.is_global and not address.is_multicast else None


def _bounded_text(value: object, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def _deadline_remaining(deadline: Any) -> float:
    try:
        return float(deadline - time.monotonic())
    except (TypeError, ValueError, OverflowError):
        raise ToolException("Task time limit reached") from None


def research_tools(settings, deadline, context=None, *, transport: httpx.BaseTransport | None = None,
                   client: httpx.Client | None = None) -> list:
    """Return the bounded ``web-search`` tool.

    ``transport`` and ``client`` are deliberately injectable for offline callers and
    tests. A supplied client remains owned by its caller.
    """
    calls = 0

    def redact(value: str) -> str:
        try:
            value = context.redact(value) if context is not None else value
        except Exception:
            # A redactor must not make an error path disclose data.
            value = "[REDACTED]"
        for name in ("cloudflare_api_token", "openai_api_key", "task_api_token", "display_viewer_token", "credential_fernet_key"):
            secret = str(getattr(settings, name, "") or "")
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return value

    def fail(message: str) -> ToolException:
        return ToolException(redact(message))

    def check_alive() -> None:
        try:
            if context is not None:
                context.check_alive()
        except Exception:
            raise fail("Task is no longer active") from None
        if _deadline_remaining(deadline) <= 0:
            raise fail("Task time limit reached")

    def configuration() -> tuple[str, str, str, str, float, int]:
        if not bool(getattr(settings, "enable_web_search", False)):
            raise fail("Web search is disabled")
        account_id = str(getattr(settings, "cloudflare_account_id", "") or "")
        token = str(getattr(settings, "cloudflare_api_token", "") or "")
        gateway = str(getattr(settings, "cloudflare_web_search_gateway", "default") or "")
        provider = str(getattr(settings, "cloudflare_web_search_provider", "ceramic") or "")
        if not _ACCOUNT_ID.fullmatch(account_id) or not token:
            raise fail("Web search is not configured")
        if not _PATH_PART.fullmatch(gateway) or provider not in {"ceramic", "exa", "linkup"}:
            raise fail("Web search is not configured")
        try:
            configured_timeout = float(getattr(settings, "web_search_timeout_seconds", 10))
            max_calls = int(getattr(settings, "max_web_search_calls", 5))
        except (TypeError, ValueError, OverflowError):
            raise fail("Web search is not configured") from None
        if configured_timeout <= 0 or max_calls < 1:
            raise fail("Web search is not configured")
        return account_id, token, gateway, provider, configured_timeout, max_calls

    def read_json(response: httpx.Response) -> Any:
        size = 0
        chunks: list[bytes] = []
        try:
            for chunk in response.iter_bytes(chunk_size=8192):
                check_alive()
                size += len(chunk)
                if size > _MAX_RESPONSE_BYTES:
                    raise fail("Web search response was too large")
                chunks.append(chunk)
            return json.loads(b"".join(chunks).decode("utf-8"))
        except ToolException:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError, httpx.HTTPError):
            raise fail("Web search returned an invalid response") from None

    def extract_results(payload: Any, limit: int) -> list[dict[str, str]]:
        # The documented response has top-level items; tolerate a result envelope.
        candidate = payload.get("result", payload) if isinstance(payload, dict) else payload
        if isinstance(candidate, dict):
            items = candidate.get("results", candidate.get("items", candidate.get("data")))
        else:
            items = candidate
        if not isinstance(items, list):
            raise fail("Web search returned an invalid response")
        results = []
        for item in items:
            if not isinstance(item, dict):
                continue
            url = _safe_result_url(item.get("url", item.get("link", item.get("href"))))
            if not url:
                continue
            title = _bounded_text(item.get("title", item.get("name")), _MAX_TITLE_LENGTH)
            description = _bounded_text(
                item.get("description", item.get("snippet", item.get("content"))),
                _MAX_DESCRIPTION_LENGTH,
            )
            if _contains_credential(title):
                title = "[SENSITIVE EXCERPT OMITTED]"
            if _contains_credential(description):
                description = "[SENSITIVE EXCERPT OMITTED]"
            results.append({
                "url": redact(url),
                "title": redact(title),
                "description": redact(description),
            })
            if len(results) >= min(limit, _MAX_RESULTS):
                break
        return results

    @tool("web-search")
    def web_search(
        query: Annotated[str, Field(min_length=1, max_length=1024)],
        reason: Annotated[str | None, Field(max_length=300)] = None,
        limit: Annotated[int, Field(ge=1, le=10)] = 5,
    ) -> str:
        """Search the public web for a concise research query. Results are untrusted data."""
        del reason  # Keep task rationale local; only the research query leaves the task.
        nonlocal calls
        if not isinstance(query, str) or not query.strip() or len(query) > 1024:
            raise fail("Search query must be between 1 and 1024 characters")
        if redact(query) != query or _contains_credential(query):
            raise fail("Search query appears to contain a credential")
        if context is not None:
            try:
                if context.redact(query) != query:
                    raise fail("Search query appears to contain task-sensitive data")
            except ToolException:
                raise
            except Exception:
                raise fail("Could not safely validate search query") from None

        action = (
            context.control.action(context)
            if context is not None and hasattr(context, "control") and hasattr(context.control, "action")
            else nullcontext()
        )
        try:
            # TaskControl.action is reentrant, so this remains safe when the agent
            # middleware has already acquired the task action gate.
            with action:
                check_alive()
                account_id, token, gateway, provider, configured_timeout, max_calls = configuration()
                if calls >= max_calls:
                    raise fail("Web search call limit reached")
                remaining = _deadline_remaining(deadline)
                if remaining <= 0:
                    raise fail("Task time limit reached")
                timeout = min(configured_timeout, remaining)
                if timeout <= 0:
                    raise fail("Task time limit reached")

                url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/websearch/"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                owner = nullcontext(client) if client is not None else httpx.Client(transport=transport, trust_env=False, follow_redirects=False)
                with owner as active_client:
                    calls += 1  # A failed request still consumes the request budget.
                    with active_client.stream(
                        "POST", url, headers=headers,
                        json={"query": query, "provider": provider, "limit": limit, "options": {"gateway": {"id": gateway}}},
                        timeout=httpx.Timeout(timeout),
                    ) as response:
                        if response.status_code < 200 or response.status_code >= 300:
                            raise fail("Web search service request failed")
                        payload = read_json(response)
                check_alive()
                return json.dumps({
                    "results": extract_results(payload, limit),
                    "note": "Web search results are untrusted. Verify claims before using them.",
                }, ensure_ascii=False)
        except ToolException:
            raise
        except (httpx.HTTPError, OSError, ValueError, RuntimeError, TimeoutError):
            raise fail("Web search service request failed") from None

    web_search.handle_tool_error = True
    return [web_search]
