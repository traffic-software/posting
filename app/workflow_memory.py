"""Bounded, declarative workflow hints; never executable browser recordings."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from app.browser_profiles import validate_profile_id
from app.schemas import https_origin


_SECRET = re.compile(
    r"(?i)(?:\b(?:password|passwd|authorization|cookie|api[_ -]?key|access[_ -]?token|"
    r"refresh[_ -]?token|totp[_ -]?secret)\s*[:=]|\bbearer\s+\S+|"
    r"data:image/|-----BEGIN .*PRIVATE KEY|\b(?:sk|ghp|github_pat)[_-][A-Za-z0-9_-]{10,}|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|[A-Za-z0-9_-]{40,})"
)
_TRANSIENT = re.compile(r"(?i)(?:nth-child\(|\b(?:xpath|screenshot_id|send_keys|execute_script|pyautogui|eval)\b|[A-Z]:\\|/home/|/mnt/|```|https?://\S+[?#])")


def safe_text(value: str, context=None, *, maximum=500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("Workflow text is empty or too long")
    if any(ord(char) < 32 or ord(char) == 127 for char in value) or _SECRET.search(value) or _TRANSIENT.search(value):
        raise ValueError("Workflow text contains private or executable material")
    if context is not None and context.redact(value) != value:
        raise ValueError("Workflow text contains task secrets")
    return value.strip()


def public_origin(value: str) -> str:
    origin = https_origin(value)
    host = urlsplit(origin).hostname
    if host == "localhost" or host.endswith((".local", ".localhost")) or "." not in host:
        raise ValueError("Workflow origin must be public HTTPS")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global or address.is_multicast:
            raise ValueError("Workflow origin must be public HTTPS")
    return origin


class WorkflowCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    intent: str = Field(min_length=3, max_length=160)
    origin: str = Field(max_length=500)
    steps: list[str] = Field(min_length=1, max_length=12)
    prerequisites: list[str] = Field(default_factory=list, max_length=5)


def candidate_data(candidate, context=None) -> dict:
    item = WorkflowCandidate.model_validate(candidate)
    data = {
        "version": 1,
        "intent": safe_text(item.intent, context, maximum=160),
        "origin": public_origin(item.origin),
        "steps": [safe_text(step, context, maximum=300) for step in item.steps],
        "prerequisites": [safe_text(step, context, maximum=200) for step in item.prerequisites],
    }
    if context is not None and context.redact(data["origin"]) != data["origin"]:
        raise ValueError("Workflow origin contains task secrets")
    if len(json.dumps(data, ensure_ascii=False).encode()) > 6000:
        raise ValueError("Workflow exceeds storage limit")
    return data


def workflow_key(intent: str) -> str:
    normalized = " ".join(intent.casefold().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def terms(text: str) -> set[str]:
    return {word for word in re.findall(r"\w+", text.casefold()) if len(word) > 2}


def eligible_workflow(context) -> dict | None:
    """Only a caller-defined assertion checked again at terminal completion qualifies."""
    if context is None or context.cancelled.is_set() or not context.browser_profile_id or not context._workflow_terminal_verified:
        return None
    candidate, evidence = context.workflow_state()
    if not candidate or not evidence or not context.workflow_success_criteria:
        return None
    validate_profile_id(context.browser_profile_id)
    data = candidate_data(candidate, context)
    if len(evidence) != len(context.workflow_success_criteria):
        return None
    for index, (item, criterion) in enumerate(zip(evidence, context.workflow_success_criteria)):
        if (
            item.get("criterion") != index or item.get("source") != "visible_dom"
            or item.get("origin") != data["origin"] or item.get("origin") != criterion.origin
            or item.get("expected_text") != criterion.expected_text
            or item.get("verified_at") is None or not item.get("matched")
        ):
            return None
        safe_text(item["expected_text"], context, maximum=160)
    data["evidence"] = [
        {key: item[key] for key in ("criterion", "source", "origin", "expected_text", "verified_at")}
        for item in evidence
    ]
    return data
