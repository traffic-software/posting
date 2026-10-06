# Agent file uploads, downloads and direct links

The optional file capability transfers any file type as **opaque bytes**, including video, audio, documents, archives and software. It does not execute, install, extract or preview downloaded content. A filename or MIME type is not evidence that a file is safe.

## Configuration

Set these values in your private `.env` and restart the service:

```dotenv
ENABLE_FILE_TRANSFERS=true
TASK_API_TOKEN=YOUR_LONG_RANDOM_API_TOKEN
ARTIFACT_PUBLIC_BASE_URL=https://YOUR_API_HOST
ARTIFACT_LINK_SIGNING_KEY=YOUR_PERSISTENT_RANDOM_SECRET_AT_LEAST_32_ASCII_CHARACTERS
CREDENTIAL_FERNET_KEY=YOUR_PERSISTENT_FERNET_KEY
ENABLE_WRITE_ACTIONS=true
```

Generate independent keys locally; do not reuse your API token as a signing key:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

The first command generates the link-signing key; the second generates the encryption key for URL-based upload grants. Keep both persistent and private. Changing the signing key invalidates existing download links. Upload sources require the persistent Fernet key. Existing queued encrypted credentials also depend on this key, so do not casually replace an existing one.

For local WSL testing, use `ARTIFACT_PUBLIC_BASE_URL=http://127.0.0.1:8001`. Production requires an externally reachable HTTPS base URL; the server does not derive it from request Host headers. A localhost URL is only reachable on the machine opening it.

`run-wsl.sh` stores artifacts under `$HOME/.local/share/posting/manual/artifacts`. Compose uses `/data/artifacts` on the existing durable data volume. Do not remove that volume if files must survive restart.

Default limits:

| Setting | Default |
| --- | --- |
| `ARTIFACT_RETENTION_SECONDS` | 86400 (24 hours) |
| `ARTIFACT_MAX_FILE_BYTES` | 536870912 (512 MiB) |
| `ARTIFACT_MAX_TASK_BYTES` | 1073741824 (1 GiB) |
| `ARTIFACT_MAX_STORAGE_BYTES` | 5368709120 (5 GiB) |
| `ARTIFACT_MAX_FILES_PER_TASK` | 10 |
| `ARTIFACT_MAX_OBJECTS` | 1000 |
| `FILE_SOURCE_TTL_SECONDS` | 3600 |
| `FILE_NETWORK_TIMEOUT_SECONDS` | 10 |
| `FILE_DOWNLOAD_WAIT_SECONDS` | 10 |

Adjust limits deliberately for larger files. The task deadline still applies; a large transfer can time out. A download wait returning `pending` is not permission to click again.

## URL-sourced uploads

Send source URLs in structured fields, **not in the prompt**. Sources must be public HTTPS URLs without embedded username/password. Private, loopback, link-local and metadata destinations are rejected, including redirect destinations. Signed URLs are accepted as server-held secrets, encrypted while queued, and fetched lazily during task execution. Source servers receive the request but no browser cookies or caller-provided Authorization headers.

```json
{
  "prompt": "Open https://studio.example.com/upload, upload the reference source into the video file input, and report whether the website accepted it. Do not publish anything.",
  "allow_write_actions": true,
  "upload_sources": [
    {
      "id": "reference",
      "url": "https://cdn.example.com/reference.mp4",
      "filename": "reference.mp4"
    }
  ],
  "upload_origins": ["https://studio.example.com"]
}
```

Submit this JSON to `POST /run-task` with `Authorization: Bearer YOUR_TASK_API_TOKEN`. Replace example hosts with your actual authorized source and destination. Destination origin grants are exact: scheme, host and port matter. Uploads need both server write enablement and task write consent. Account login, when needed, uses the existing profile/credential features separately.

The agent uses `list_upload_sources`, `fetch_upload_source`, `inspect_file_inputs` and `upload_file`. Dedicated inspection supports hidden real `input[type=file]` elements; generic click/type tools still cannot open OS file pickers or accept arbitrary filesystem paths. File assignment alone does not prove that the website accepted or saved the upload. Input-only files do not receive public download links and are removed when task cleanup completes.

## Downloads

A public direct fetch needs explicit download consent:

```json
{
  "prompt": "Download https://downloads.example.com/release.zip and report the resulting file. Do not run or extract it.",
  "allow_file_downloads": true
}
```

For authenticated website or same-origin Blob downloads, also grant writes because the agent must click a page control:

```json
{
  "prompt": "Open https://studio.example.com/exports and download the existing video using its Download button. Do not generate or publish anything.",
  "allow_file_downloads": true,
  "allow_write_actions": true
}
```

`download_file` streams public HTTPS bytes without account cookies. `download_link` reads an observed link server-side so a signed href need not be copied into the model's arguments. `download_from_element` arms one browser download and performs one inspected click; `wait_for_download` observes it without re-clicking. Browser downloads retain browser authentication internally. If reliable download-event transport is unavailable, the native capability reports unavailable instead of guessing from a stable file size.

Only fully verified and atomically stored output files become artifacts. Partial, canceled or oversized downloads have no links. Already completed output artifacts may remain available even when another part of the task fails; their presence does not imply the entire task succeeded.

## Response and direct links

Read `GET /task-status/{task_id}` with the task API bearer token. The response has a separate top-level `artifacts` array; links are generated by the server, not the model:

```json
{
  "task_id": "YOUR_TASK_UUID",
  "status": "COMPLETED",
  "result": {"output": "The requested file was downloaded."},
  "error": null,
  "artifacts": [
    {
      "id": "OPAQUE_ARTIFACT_ID",
      "name": "release.zip",
      "size_bytes": 12345,
      "media_type": "application/zip",
      "sha256": "FILE_SHA256",
      "download_url": "https://YOUR_API_HOST/task-artifacts/OPAQUE_ARTIFACT_ID/download?expires=EXPIRY&signature=SIGNATURE",
      "expires_at": "SERVER_GENERATED_EXPIRY"
    }
  ]
}
```

The illustrative values above are placeholders; copy the real `download_url` unchanged. Open it in a browser or download it without an Authorization header. HEAD and valid HTTP Range requests are supported. Responses force attachment handling with no-store/nosniff protections; this does not make malicious bytes harmless.

**A direct link is a bearer capability: anyone holding it can download the file until expiry.** Do not share it publicly unless that is intentional. Link expiry does not extend on a status read and cannot exceed file retention. Expired, tampered, missing or unavailable artifacts return 404. Ready outputs survive service restart until expiry when storage and the signing key remain intact.

## Deployment security

- Protect task submission and task-status access with `TASK_API_TOKEN`, TLS and appropriate rate limits. File tasks require configured task authentication even in otherwise local development setups.
- Disable query-string logging for `/task-artifacts/` at your reverse proxy, CDN and monitoring layers. Application access-log filtering is not a substitute for controlling upstream logs. Never put artifact links or source signatures in workflow memory or search queries.
- Apply browser/container network egress controls blocking internal, private, loopback and metadata destinations. Server-side source fetching pins validated public addresses, but post-event browser checks are **not** a complete browser SSRF boundary and cannot undo an earlier network request.
- Do not place artifact storage in a web-server document root or expose its directory directly. Only the capability-checked API should serve output files.
- Transfers are authorized file operations, not permission to bypass CAPTCHA, access controls or website restrictions. Local self-signed integration fixtures do not justify disabling production TLS verification.
