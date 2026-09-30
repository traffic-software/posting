# VPS deployment

The separate **vps deply** GitHub Action builds the app image on GitHub's Linux runner, transfers it to the VPS over SSH and starts the app and Selenium with Docker Compose. Trigger it manually from the `deep-worker` branch. Railway deployment remains independent.

## Prepare the VPS

Use an **amd64 Linux** server with Docker Engine and the `docker compose` plugin installed. Allocate enough memory for Chrome (the Selenium container reserves 2 GB shared memory). Create an SSH deployment user with permission to run Docker, then create `/opt/posting` owned by that user. Docker group membership effectively grants root-level access; use a dedicated account and protect its SSH credentials. Ensure port 8000 on the host is free. No public ports are required: app binds to `127.0.0.1:8000`, Selenium is only on the Compose network.

Create `/opt/posting/.env` on the VPS, readable only by the deployment user (for example `chmod 600 /opt/posting/.env`). Use [`.env.example`](../.env.example) as a template, supplying real `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME`, `ALLOWED_HOSTS` (approved exact hostnames), and a long random `TASK_API_TOKEN`. Set `ENABLE_WRITE_ACTIONS=false` unless explicitly needed for approved targets. The VPS Compose file sets `REQUIRE_TASK_API_TOKEN=true`; a missing token prevents the app from starting. Never commit or send this `.env` through GitHub Actions. If exposing the API externally, configure a separate HTTPS reverse proxy with rate limiting and authentication; do not change the localhost binding or publish Selenium directly.

## GitHub configuration

Create the GitHub environment `vps`. Configure these **environment** secrets and variables (or repository-level values if your policy requires it):

| Type | Name | Value |
| --- | --- | --- |
| Secret | `VPS_SSH_PASSWORD` | SSH password for the deployment user; required |
| Secret | `VPS_KNOWN_HOSTS` | Verified SSH host key entry for the VPS, including the port when non-default |
| Variable | `VPS_HOST` | VPS DNS hostname or IPv4 address |
| Variable | `VPS_USER` | SSH deployment username |
| Variable | `VPS_SSH_PORT` | Optional SSH port; defaults to 22 |

Verify the server fingerprint using a trusted channel before saving the known-hosts entry. For port 22 use `hostname ssh-ed25519 ...`; for a custom port use `[hostname]:port ssh-ed25519 ...`. `ssh-keyscan` can retrieve a candidate key, but its output **must** be fingerprint-checked independently before trusting it. For password login, the VPS SSH server must allow password authentication for `VPS_USER`. Store the password only in the GitHub secret, never in a workflow file or repository variable. This workflow uses password authentication only; `VPS_SSH_KEY` is not needed.

## Deploy and verify

In GitHub Actions choose **vps deply → Run workflow → deep-worker**. The action runs tests, builds `posting-app:sha-<commit>` for `linux/amd64`, loads it on the VPS, transfers `compose.vps.yaml`, and starts the stack. The first deploy pulls `selenium/standalone-chrome:4.31.0`; Docker Hub network access is needed on the VPS. It waits for both containers and checks `/ready` against the exact commit SHA. A failed run is not a verified deployment; inspect the action logs and `docker compose -f /opt/posting/compose.vps.yaml -p posting-vps ps` on the VPS.

On the VPS, check `curl -fsS http://127.0.0.1:8000/ready`. Try `curl -i http://127.0.0.1:8000/task-status/00000000-0000-0000-0000-000000000000`: without a bearer token it should return 401. Run a real task only with an approved destination and model endpoint.

The named `posting-vps_tasks_data` volume holds `/data/tasks.db` across deployments. **Do not** use `docker compose down -v` or delete the volume without a backup. The app runs as the non-root image user; the image owns the `/data` directory and Docker initializes a newly created named volume from it. Existing volumes must already be writable by that user. The workflow leaves older image tags on disk for rollback: on the VPS, set `APP_IMAGE=posting-app:sha-<previous-commit>` when running `docker compose -f compose.vps.yaml up -d --no-build --wait` in `/opt/posting`. Confirm `/ready` reports the previous revision; never delete the volume to roll back.
