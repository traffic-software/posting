"""Submit a read-only Gmail sign-in page check and poll the deployed API."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv


PROMPT = """Use navigate_to_page to open https://mail.google.com/ and inspect
only the resulting Gmail or Google sign-in page using the provided read-only tools.
Report the observed page title, visible sign-in text, and whether an email or phone
input field can be confirmed. If the provided tools cannot confirm the input field,
say that it could not be verified; do not infer its presence from prior knowledge.
Do not enter credentials, click buttons, submit forms, sign in, or read mailbox data.
If Google presents a CAPTCHA, consent screen, browser warning, or access restriction,
report it accurately and do not bypass it. Do not invent observations or claim that
login succeeded. This task checks the sign-in page only, not account authentication."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", help="Poll an existing task instead of submitting another")
    parser.add_argument("--timeout", type=int, default=240, help="Polling timeout in seconds")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    token = os.getenv("TASK_API_TOKEN", "").strip()
    if not token:
        print("Missing TASK_API_TOKEN in .env or environment", file=sys.stderr)
        return 1

    def display(value: str) -> str:
        return value.replace(token, "[REDACTED]")

    with httpx.Client(
        base_url="https://webagent.elgrowth.com",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
        follow_redirects=False,
    ) as client:
        task_id = args.task_id
        try:
            if not task_id:
                response = client.post("/run-task", json={"prompt": PROMPT})
                if response.status_code != 202:
                    print(f"Submission failed: HTTP {response.status_code}", file=sys.stderr)
                    return 1
                task_id = response.json()["task_id"]
                print(f"Accepted task: {display(task_id)}", flush=True)
                print("Keep this ID to poll again without submitting another paid task.")

            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                response = client.get(f"/task-status/{task_id}")
                response.raise_for_status()
                data = response.json()
                status = data["status"]
                print(f"Status: {display(status)}", flush=True)
                if status in ("COMPLETED", "FAILED"):
                    print(display(json.dumps(data, indent=2, ensure_ascii=False)))
                    if status == "COMPLETED":
                        print("Page check completed; inspect the observations or Google restrictions. No login was attempted.")
                        return 0
                    return 1
                time.sleep(min(3, max(0, deadline - time.monotonic())))
        except httpx.HTTPStatusError as exc:
            print(f"Polling failed: HTTP {exc.response.status_code}", file=sys.stderr)
            return 1
        except httpx.RequestError:
            print("API connection failed; no token or request details were logged.", file=sys.stderr)
            return 1
        except (ValueError, KeyError, TypeError):
            print("Unexpected API response", file=sys.stderr)
            return 1

    print(f"Polling timed out. Task {display(task_id)} may still be running.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
