"""Submit a browser task in prompt-only or secure account mode and poll the API."""

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


def account_payload(prompt: str, secrets: set[str]) -> dict:
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    from app.schemas import LoginCredential, TaskRequest

    credential_id = input("Credential ID [account]: ").strip() or "account"
    origins = [value.strip() for value in input("Authorized HTTPS origins (comma-separated): ").split(",")]
    if input("I am authorized to use this account and permit login writes [yes/no]: ").strip().lower() != "yes":
        raise ValueError("Account consent required")
    username = getpass.getpass("Account username (hidden): ")
    password = getpass.getpass("Account password (hidden): ")
    seed = getpass.getpass("Authenticator Base32 secret (hidden; blank if unused): ")
    secrets.update(value for value in (username, password, seed) if value)
    credential = LoginCredential(id=credential_id, origins=origins, username=username, password=password, totp_secret=seed or None)
    normalized_seed = credential.totp_secret.get_secret_value() if credential.totp_secret else None
    if normalized_seed:
        secrets.add(normalized_seed)
    if any(value in prompt or value in credential_id for value in secrets):
        raise ValueError("Keep credentials out of the prompt and ID")
    request = TaskRequest(prompt=prompt, allow_write_actions=True, credentials=[credential])
    return {
        "prompt": request.prompt,
        "allow_write_actions": True,
        "credentials": [{
            "id": credential.id, "origins": credential.origins,
            "username": credential.username.get_secret_value(),
            "password": credential.password.get_secret_value(), "totp_secret": normalized_seed,
        }],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--task-id", type=UUID, help="Poll without submitting a new task")
    mode.add_argument("--account", action="store_true", help="Collect encrypted structured account credentials separately from the task prompt")
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

    secrets = {token}

    def display(data) -> str:
        text = json.dumps(data, indent=2, ensure_ascii=False)
        for secret in sorted(secrets, key=len, reverse=True):
            escaped = json.dumps(secret, ensure_ascii=False)[1:-1]
            text = text.replace(escaped, "[REDACTED]").replace(secret, "[REDACTED]")
        return text

    task_id = str(args.task_id) if args.task_id else None
    with httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {token}"}, timeout=30) as client:
        try:
            if task_id is None:
                print("Describe the task for your own/authorized account in the prompt.")
                print("Keep credentials out of the prompt; prompt contents go to the model and task database.")
                if args.account:
                    print("Account mode collects secrets separately; the server encrypts them before queueing.")
                print("Typing/clicking requires ENABLE_WRITE_ACTIONS=true on the server.")
                prompt = getpass.getpass("Task prompt (hidden): ").strip()
                if not prompt or len(prompt) > 4000:
                    print("Prompt must contain 1 to 4000 characters", file=sys.stderr)
                    return 1
                payload = account_payload(prompt, secrets) if args.account else {"prompt": prompt}
                try:
                    response = client.post("/run-task", json=payload)
                finally:
                    del payload, prompt
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
