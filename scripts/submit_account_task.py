"""Submit the configured Gmail login test and poll the API."""

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

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
    credential_id = "account"
    origins = ["https://accounts.google.com", "https://mail.google.com"]
    username = "rmansa082@gmail.com"
    password = "PDSAKLZXCa"
    seed = "suse vtgn ohir znkr h4tu u2m3 6ftp v4wy"
    secrets.update(value for value in (username, password, seed) if value)
    normalized_seed = "".join(seed.split()).upper()
    secrets.add(normalized_seed)
    return {
        "prompt": prompt,
        "allow_write_actions": True,
        "credentials": [{
            "id": credential_id, "origins": origins,
            "username": username,
            "password": password, "totp_secret": seed,
        }],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", help="Poll an existing task without submitting again")
    parser.add_argument("--browser-profile", help="Persistent profile ID from the authenticated desktop panel")
    parser.add_argument("--prompt", help="Task prompt for a selected profile; no embedded credentials are submitted")
    parser.add_argument("--allow-write-actions", action="store_true", help="Explicit task write consent for profile tasks")
    parser.add_argument("--account", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    if args.browser_profile:
        import re
        if not re.fullmatch(r"[a-f0-9]{32}", args.browser_profile) or not args.prompt or not args.prompt.strip():
            parser.error("--browser-profile requires a valid panel profile ID and --prompt")
    elif args.prompt or args.allow_write_actions:
        parser.error("--prompt and --allow-write-actions require --browser-profile")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    base_url = os.getenv("TASK_API_URL", "http://127.0.0.1:8000").rstrip("/")
    try:
        parsed = urlsplit(base_url)
        loopback_profile = (args.browser_profile and parsed.scheme == "http"
                            and parsed.hostname in {"127.0.0.1", "localhost", "::1"})
        valid_origin = (
            (parsed.scheme == "https" or loopback_profile) and parsed.hostname
            and parsed.port != 0 and parsed.username is None and parsed.password is None
            and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
        )
    except ValueError:
        valid_origin = False
    if not valid_origin:
        print("TASK_API_URL must be an HTTPS origin without credentials (profile-only mode also permits loopback HTTP)", file=sys.stderr)
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
                print("Submitting a selected-profile task." if args.browser_profile else "Submitting the configured Gmail login test.")
                prompt = """"Sign in to my authorized Gmail account using structured credential ID account.

1. Open https://accounts.google.com/.
2. Inspect the visible page and identify the account identifier field.
3. Use fill_credential with credential ID account and field username.
4. Continue to the password page. Use fill_credential with credential ID
   account and field password, then continue.
5. If Google requests an authenticator-app code, use inspect_totp_form
   with credential ID account to discover supported OTP input and submit
   selectors.
6. Use fill_totp with those selectors and credential ID account.
   The tool must generate the current 30-second OTP from the supplied
   structured TOTP secret and enter it directly. Never request, repeat
   or expose the password, shared secret or generated OTP.
7. After submission, inspect the resulting page. If authentication
   succeeds, navigate to https://mail.google.com/ and confirm that the
   Gmail inbox interface is visible. Do not read email contents, send
   messages or change account settings.
8. Report only the observed outcome. Do not claim successful login
   merely because a button was clicked or an OTP was submitted.

If no authenticator-app challenge appears, do not invent or force one.
Report whether Gmail was reached and whether authenticator 2FA was used.
Stop on CAPTCHA, suspicious-login warnings, access restrictions,
unsupported forms, SMS/email verification, recovery requests or device
approval. Do not bypass restrictions or blindly retry a failed login.
"""
                if args.browser_profile:
                    prompt = args.prompt.strip()
                    payload = {"prompt": prompt, "browser_profile_id": args.browser_profile}
                    if args.allow_write_actions:
                        payload["allow_write_actions"] = True
                else:
                    payload = account_payload(prompt, secrets)
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
