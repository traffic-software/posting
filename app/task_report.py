import json


class TaskExecutionFailure(RuntimeError):
    def __init__(self, result: dict, message: str = "Task execution failed"):
        super().__init__(message)
        self.result = result


def output_result(text: str) -> dict:
    # Bound the serialized result, not characters: Unicode and JSON escaping vary.
    text = str(text)
    low, high = 0, min(len(text), 6000)
    while low < high:
        middle = (low + high + 1) // 2
        if len(json.dumps({"output": text[:middle]}, ensure_ascii=False).encode("utf-8")) <= 8000:
            low = middle
        else:
            high = middle - 1
    return {"output": text[:low]}


def failure_result(reason: str = "Execution stopped before the requested outcome could be verified.") -> dict:
    return output_result(
        f"The task did not complete. {reason} "
        "No additional agent analysis is available. The requested action's success is not confirmed."
    )
