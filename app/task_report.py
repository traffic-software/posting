import json
import re
from concurrent.futures import CancelledError


class TaskExecutionFailure(RuntimeError):
    def __init__(self, result: dict, message: str = "Task execution failed"):
        super().__init__(message)
        self.result = result


# Public diagnostics contain fixed messages, never provider/browser exception text.
_FAILURES = {
    "task_cancelled": ("cancel", "The task was cancelled."),
    "application_shutdown": ("cancel", "The application shut down and cancelled execution."),
    "application_restart": ("interrupted", "An application restart interrupted execution; the original exception is unavailable."),
    "credentials_expired": ("control", "Queued task credentials expired before execution."),
    "file_sources_expired": ("control", "Queued task file-source grants expired before execution."),
    "task_deadline": ("timeout", "The task execution deadline was reached."),
    "operation_timeout": ("timeout", "An execution operation timed out; the task deadline is not confirmed as the cause."),
    "agent_step_limit": ("step", "The agent reached its execution step limit."),
    "model_timeout": ("model", "The model service did not respond within its timeout."),
    "model_authentication": ("model", "The model service rejected the configured authentication."),
    "model_rate_limit": ("model", "The model service rejected the request due to a rate or quota limit."),
    "model_connection": ("model", "A connection to the model service could not be established."),
    "model_error": ("model", "A model invocation failed."),
    "model_image_unavailable": ("model", "The model invocation with image input failed; image capability is unverified."),
    "browser_runtime": ("browser", "The local browser/display runtime could not proceed."),
    "browser_operation": ("browser", "The browser service could not complete an operation."),
    "tool_error": ("tool", "A tool invocation failed."),
    "task_control": ("control", "Task control or credential availability prevented execution."),
    "preflight_rejected": ("configuration", "Task prerequisites were not satisfied; execution did not start."),
    "unknown_failure": ("unknown", "Execution stopped due to an unclassified exception."),
}
_PHASES = {"preflight", "browser_startup", "agent_setup", "agent_execution", "model", "tool", "verification", "context_setup", "storage", "worker", "execution"}
_EXCEPTION_TYPES = {"RuntimeError", "ValueError", "TypeError", "KeyError", "IndexError", "AttributeError", "AssertionError", "OSError", "TimeoutError", "InvalidToken", "ValidationError", "TaskControlError", "TaskDeadlineExceeded", "GraphRecursionError", "ToolException", "VisualGuardError", "BrowserPolicyStop", "BrowserRuntimeError", "WebDriverException", "APITimeoutError", "AuthenticationError", "RateLimitError", "APIConnectionError", "APIError", "CancelledError", "OtherException"}


def diagnostic(code: str, phase: str, *, tool: str | None = None) -> dict:
    code = code if isinstance(code, str) and code in _FAILURES else "unknown_failure"
    phase = phase if isinstance(phase, str) and phase in _PHASES else "execution"
    category, message = _FAILURES[code]
    result = {"category": category, "phase": phase, "code": code, "message": message}
    if isinstance(tool, str) and re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,79}", tool):
        result["tool"] = tool
    return result


def tool_blocker(code, tool) -> dict:
    from app.visual_targets import VISUAL_GUARD_MESSAGES
    from app.selenium_tools import RECOVERY_MESSAGES
    messages = {**VISUAL_GUARD_MESSAGES, **RECOVERY_MESSAGES}
    code = code if isinstance(code, str) and code in messages else "tool_stop"
    result = {"code": code, "message": messages.get(
        code, "A tool reported a blocker; this is not necessarily the termination cause.",
    )}
    if isinstance(tool, str) and re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,79}", tool):
        result["tool"] = tool
    return result


def failure_diagnostics(exc: Exception, context=None, *, phase: str = "execution") -> dict:
    from langchain_core.tools import ToolException
    from langgraph.errors import GraphRecursionError
    from openai import APIConnectionError, APITimeoutError, APIError, AuthenticationError, RateLimitError
    from selenium.common.exceptions import WebDriverException
    from app.browser_runtime import BrowserRuntimeError
    from app.task_context import TaskControlError, TaskDeadlineExceeded

    tool = None
    recorded_code = None
    if context is not None:
        phase, tool, recorded_code = context.failure_origin(exc, phase)
    if isinstance(exc, CancelledError) or (context is not None and context.cancelled.is_set()):
        code = "task_cancelled"
    elif isinstance(exc, TaskDeadlineExceeded):
        code = "task_deadline"
    elif isinstance(exc, GraphRecursionError):
        code = "agent_step_limit"
    elif isinstance(recorded_code, str) and recorded_code in _FAILURES:
        code = recorded_code
    elif isinstance(exc, APITimeoutError) or (phase == "model" and isinstance(exc, TimeoutError)):
        code = "model_timeout"
    elif isinstance(exc, AuthenticationError):
        code = "model_authentication"
    elif isinstance(exc, RateLimitError):
        code = "model_rate_limit"
    elif isinstance(exc, APIConnectionError):
        code = "model_connection"
    elif isinstance(exc, APIError) or phase == "model":
        code = "model_error"
    elif isinstance(exc, TimeoutError):
        code = "operation_timeout"
    elif isinstance(exc, TaskControlError):
        code = "task_control"
    elif isinstance(exc, BrowserRuntimeError):
        code = "browser_runtime"
    elif isinstance(exc, WebDriverException):
        code = "browser_operation"
    elif isinstance(exc, ToolException) or phase == "tool":
        code = "tool_error"
    else:
        code = "unknown_failure"
    result = diagnostic(code, phase, tool=tool)
    name = type(exc).__name__
    result["exception_type"] = name if name in _EXCEPTION_TYPES else "OtherException"
    if context is not None:
        stopped = [event for event in context.observations() if event["outcome"] == "stopped"]
        if stopped:
            event = stopped[-1]
            # Only allowlisted visual messages are copied; other blockers stay categorical.
            result["last_tool_blocker"] = tool_blocker(event.get("code"), event.get("tool"))
    return result


def normalize_diagnostics(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    result = diagnostic(value.get("code"), value.get("phase"), tool=value.get("tool"))
    exception_type = value.get("exception_type")
    if isinstance(exception_type, str) and exception_type in _EXCEPTION_TYPES:
        result["exception_type"] = exception_type
    blocker = value.get("last_tool_blocker")
    if isinstance(blocker, dict):
        result["last_tool_blocker"] = tool_blocker(blocker.get("code"), blocker.get("tool"))
    return result


def output_result(text: str, diagnostics: dict | None = None) -> dict:
    # Bound the entire serialized result: Unicode and JSON escaping vary.
    text = str(text)
    result = {"output": ""}
    if diagnostics is not None:
        result["diagnostics"] = normalize_diagnostics(diagnostics)
    low, high = 0, min(len(text), 6000)
    while low < high:
        middle = (low + high + 1) // 2
        result["output"] = text[:middle]
        if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) <= 8000:
            low = middle
        else:
            high = middle - 1
    result["output"] = text[:low]
    return result


def failure_result(reason: str = "Execution stopped before the requested outcome could be verified.", diagnostics: dict | None = None) -> dict:
    return output_result(
        f"The task did not complete. {reason} "
        "No additional agent analysis is available. The requested action's success is not confirmed.",
        diagnostics,
    )
