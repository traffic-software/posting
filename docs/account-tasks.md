# Authorized account tasks

This feature uses **standard Remote Selenium**, not undetected ChromeDriver or anti-detect tooling. It does not spoof fingerprints, rotate proxies, bypass CAPTCHA/MFA/2FA, or work around blocked-login warnings. Task-specific proxies are disabled; browser sessions use the Selenium host's existing network configuration. Use only accounts and workflows you are authorized to automate.

The repository exposes an API and an interactive Python client; it does not include a frontend. A frontend can send the structured JSON below over HTTPS. The current shared bearer token is for one trusted operator: it is not per-user identity or task ownership. Add those protections before building a public multi-user credential-submission service.

## Server prerequisites

Keep `TASK_API_TOKEN` and `REQUIRE_TASK_API_TOKEN=true` on public deployments. Structured credentials always require configured API authentication, including locally.

Login entry needs both:

- server `ENABLE_WRITE_ACTIONS=true` (explicit opt-in; also permits side-effecting browser tools);
- request `allow_write_actions=true`.

Neither deployment files nor the client automatically enable server writes. Read-only requests continue to work with writes disabled. For legacy prompt-only requests, the existing global write setting retains its behavior; explicitly use `allow_write_actions=false` to impose a task-level read-only ceiling.

On the server, configure:

```text
CREDENTIAL_FERNET_KEY=<generated-server-secret>
CREDENTIAL_TTL_SECONDS=900
```

Generate a key on a trusted server with the installed environment:

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Save it only in the server's secret configuration, protect `.env` permissions, and do not send it to the client, model, repository, chat or logs. This command prints the new secret: use a private terminal. Missing/invalid keys reject credential submissions with 503. Changing the key invalidates pending encrypted tasks; plan rotation rather than silently replacing it.

## Request shape

```json
{
  "prompt": "Open https://login.example/signin. Use credential ID account to sign in to my authorized account. Report the observed outcome; stop at any security challenge.",
  "allow_write_actions": true,
  "credentials": [
    {
      "id": "account",
      "origins": ["https://login.example"],
      "username": "YOUR_ACCOUNT_IDENTIFIER",
      "password": "YOUR_ACCOUNT_PASSWORD"
    }
  ]
}
```

POST to `/run-task` with the existing bearer token. Response remains a task ID and `PENDING`; poll `/task-status/{task_id}`. Status responses never include the submitted context or encrypted blob. Validation errors return generic 422 messages rather than reflecting request fields.

- `credentials` are optional. Up to five credential IDs are supported; each permits up to five exact HTTPS origins. Omit `proxy` or set it to `null`; any non-null proxy request is rejected with 422.
- Origins contain no path/query/fragment. Port differences matter. Cross-origin SSO requires explicitly listing each trusted credential-entry origin; do not add origins merely because an untrusted page asks for them.
- The agent receives credential IDs and allowed origins, **not username/password values**. `fill_credential(selector, credential_id, field)` enters them directly through Selenium. Entry is restricted to top-level input fields at an allowed origin; password values require password inputs.
- Challenges/restrictions are prohibited by agent instructions, with conservative checks before credential-task writes. These checks are not a universal challenge detector. A restricted site may result in a failed task or a completed explanation rather than successful login. Inspect the output: `COMPLETED` alone does not prove authentication succeeded.
- Page contents and requested operations can still reach the configured model provider. Do not request sensitive mailbox/account content unless you accept that disclosure. Known credential values are redacted from text tool results and final output as defense in depth, not a complete data-loss-prevention guarantee.
- Never put secrets in the **prompt**, credential **ID**, URLs, selectors or proxy host. Prompts and final outputs persist; arbitrary secrets in natural-language instructions cannot be reliably detected or automatically protected.

## Credential lifecycle

Structured username/password values are encrypted with Fernet before SQLite insertion. The worker decrypts them after claim; default TTL is 900 seconds and configurable from 60 to 3600 seconds. Values remain scoped to the running task; browser closure is attempted on exit and cookies/profiles are not persisted by this feature. Graceful app shutdown cancels the active task, clears its live encrypted credentials and attempts to delete its registered browser session. Tools honor cancellation, including sessions created after cancellation. Compose grants the app 60 seconds to stop; increase deployment grace if browser transport timeouts are raised. Hard kills, server crashes or an unreachable Selenium service can still leave a remote browser until Selenium cleans it up; configure a server-side idle session timeout. Outstanding model calls cannot be force-killed by this thread-based worker.

Unexpired pending tasks retain encrypted credentials across restarts. Completion, failure, expiry cleanup and interrupted-processing recovery clear the live credential columns. Interrupted processing is failed, not automatically retried. Pending expiry cleanup runs in the worker. TTL is also checked before credential entry.

Clearing a SQLite column is **logical deletion**, not forensic erasure: WAL files, backups or memory copies may retain ciphertext/data. Protect the database, encryption key, server, Selenium control channel and backup policy accordingly. No browser automation can keep a password secret from the trusted login page receiving it; compromised pages/scripts at an allowed origin remain a risk.

## Proxy support disabled

The app does not configure Selenium proxy capabilities. Non-null `proxy` submissions are rejected at request validation; previously queued proxy tasks fail before a browser session is created rather than silently running without their requested proxy. Legacy proxy context decoding is retained only to reject those pending tasks safely.

This does not change the Selenium host's network configuration or any infrastructure-level proxy. Continue to enforce network-level egress restrictions against internal, loopback, private, link-local, metadata and other non-public destinations. Application DNS validation and a private Compose network alone do not prevent SSRF, DNS rebinding, redirects or browser subresource access.

## Interactive client

From Windows Git Bash:

```bash
cd /d/posting
.venv/Scripts/python.exe scripts/submit_account_task.py
```

The script now uses the **simple prompt-only flow**: it loads the API token from project `.env` (or prompts securely), asks for one hidden task prompt and sends only `{"prompt": "..."}`. No separate account, origins, proxy or credential-encryption setup is needed for this client. Typing/clicking still requires server `ENABLE_WRITE_ACTIONS=true`; the client cannot override that setting. Entering the prompt submits the task and can incur model API charges.

If username/password are included in the prompt, they are sent to the model provider and persisted in the task database **without the structured-credential encryption described above**. Hidden terminal entry prevents echo/history exposure, not model/database disclosure. Outputs may also contain sensitive account information; do not share them unredacted. The API still supports optional structured credentials for clients that need them; task-specific proxies are disabled. Only recognized, fixed server error messages are displayed; arbitrary response error bodies are omitted.

Optional `TASK_API_URL` defaults to `https://webagent.elgrowth.com`. It must use HTTPS. The client does not configure the server's write gate or encryption key.

If polling stops, reuse the returned ID rather than repeating a paid/side-effecting task:

```bash
.venv/Scripts/python.exe scripts/submit_account_task.py --task-id RETURNED_UUID
```

If submission times out before an ID is received, its outcome may be unknown; do not blindly retry a write task. Credentials in this client are transient in process memory, not guaranteed securely erased.

## Verification

Unit tests use synthetic credentials, fake drivers/model responses and mocked DNS. They do not log in to real platforms or contact real proxies. Before production, perform an explicitly authorized controlled login integration test, verify effective egress restrictions, and check that non-null proxy requests are rejected. Test CAPTCHA/2FA/restriction stops without attempting bypass. Real Chrome/site compatibility has not been established by unit tests.
