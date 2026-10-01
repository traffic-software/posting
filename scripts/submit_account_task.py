"""Submit a prompt-only browser task and poll the deployed API."""

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from dotenv import load_dotenv


ERROR_MESSAGES = {
    "Credential encryption is unavailable": "Credential encryption is unavailable",
    "Task service is not configured": "Server model configuration is incomplete",
    "Task worker is unavailable": "Server task worker is unavailable",
    "Write actions are disabled": "Enable ENABLE_WRITE_ACTIONS on the server to allow writes",
    "Unauthorized": "Check TASK_API_TOKEN",
    "Invalid task request": "Invalid task request",
    "Task capacity reached": "Server task capacity reached",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=UUID, help="Poll without submitting a new task")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    base_url = os.getenv("TASK_API_URL", "https://webagent.elgrowth.com").rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https" or not parsed.hostname
        or parsed.username is not None or parsed.password is not None
        or parsed.path not in ("", "/") or parsed.query or parsed.fragment
    ):
        print("TASK_API_URL must be an HTTPS origin without credentials", file=sys.stderr)
        return 1
    token = os.getenv("TASK_API_TOKEN", "") or getpass.getpass("API token: ")
    if not token:
        print("API token is required", file=sys.stderr)
        return 1

    def display(data) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False).replace(token, "[REDACTED]")

    task_id = str(args.task_id) if args.task_id else None
    with httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {token}"}, timeout=30) as client:
        try:
            if task_id is None:
                print("Describe the task for your own/authorized account in the prompt.")
                print("Prompt contents, including any credentials, go to the model and task database.")
                print("Typing/clicking requires ENABLE_WRITE_ACTIONS=true on the server.")
                prompt = getpass.getpass("Task prompt (hidden): ").strip()
                if not prompt or len(prompt) > 4000:
                    print("Prompt must contain 1 to 4000 characters", file=sys.stderr)
                    return 1
                response = client.post("/run-task", json={"prompt": prompt})
                del prompt
                if response.status_code != 202:
                    print(f"Submission failed: HTTP {response.status_code}", file=sys.stderr)
                    try:
                        detail = response.json().get("detail")
                        if isinstance(detail, str) and detail in ERROR_MESSAGES:
                            print(ERROR_MESSAGES[detail], file=sys.stderr)
                    except (ValueError, AttributeError):
                        pass
                    return 1
                task_id = response.json()["task_id"]
                print(f"Accepted task: {task_id}", flush=True)

            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                response = client.get(f"/task-status/{task_id}")
                response.raise_for_status()
                data = response.json()
                print(f"Status: {data['status']}", flush=True)
                if data["status"] in ("COMPLETED", "FAILED"):
                    print(display(data))
                    print("Inspect observed output; COMPLETED alone does not prove login succeeded.")
                    return 0 if data["status"] == "COMPLETED" else 1
                time.sleep(min(3, max(0, deadline - time.monotonic())))
        except httpx.HTTPStatusError as exc:
            print(f"Polling failed: HTTP {exc.response.status_code}", file=sys.stderr)
            return 1
        except httpx.RequestError:
            print("Connection failed. No request details were logged.", file=sys.stderr)
            if task_id is None:
                print("Submission outcome may be unknown; do not retry side-effecting work blindly.", file=sys.stderr)
            return 1
        except (ValueError, KeyError, TypeError):
            print("Invalid input or unexpected response; details omitted.", file=sys.stderr)
            return 1
        except (EOFError, KeyboardInterrupt):
            print("Stopped locally; an already submitted task is not cancelled.", file=sys.stderr)
            return 1
    print(f"Polling timed out; poll task {task_id} again with --task-id.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
