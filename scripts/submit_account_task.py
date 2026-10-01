"""Submit an authorized account task using secure interactive credential entry."""

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
    secrets = [token]

    def display(data) -> str:
        text = json.dumps(data, indent=2, ensure_ascii=False)
        for secret in sorted(secrets, key=len, reverse=True):
            if secret:
                text = text.replace(secret, "[REDACTED]")
        return text

    task_id = str(args.task_id) if args.task_id else None
    with httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {token}"}, timeout=30) as client:
        try:
            if task_id is None:
                print("Only use your own/authorized account. Do not put credentials in the prompt.")
                prompt = input("Task prompt (refer to credential ID 'account'): ").strip()
                origins = input("Exact allowed HTTPS login origins (comma-separated): ").split(",")
                username = getpass.getpass("Account username (hidden): ")
                password = getpass.getpass("Account password (hidden): ")
                secrets.extend([username, password])
                proxy_host = input("Fixed IP-allowlisted proxy host (blank for none): ").strip()
                proxy = None
                if proxy_host:
                    scheme = input("Proxy scheme [http/socks5]: ").strip() or "http"
                    proxy = {"scheme": scheme, "host": proxy_host, "port": int(input("Proxy port: "))}
                print("This task permits browser writes and may incur model API charges.")
                if input("Authorize this task? Type yes: ").strip().lower() != "yes":
                    print("Cancelled; no task submitted.")
                    return 0
                payload = {
                    "prompt": prompt, "allow_write_actions": True,
                    "credentials": [{
                        "id": "account", "origins": [origin.strip() for origin in origins],
                        "username": username, "password": password,
                    }],
                    "proxy": proxy,
                }
                response = client.post("/run-task", json=payload)
                if response.status_code != 202:
                    print(f"Submission failed: HTTP {response.status_code}; response body omitted.", file=sys.stderr)
                    return 1
                task_id = response.json()["task_id"]
                print(f"Accepted task: {task_id}", flush=True)
                del payload, username, password

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
            print("Connection failed. No request or credential details were logged.", file=sys.stderr)
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
