# Railway deployment (GHCR + Selenium)

Target branch: `deep-worker`. Image: `ghcr.io/traffic-software/posting-app:deep-worker`. Railway Hobby cannot pull a private GHCR package: after the first GitHub Actions publish, change the GHCR package visibility to **Public**. The image contains only `app/` and pinned dependencies; never add `.env` to the build context.

## 1. Prepare GitHub

Commit the new deployment files and targeted application changes explicitly to `deep-worker`, then push that branch. Review `git diff --cached` before committing; avoid sweeping unrelated work into the deployment commit. The earlier `py/` and `g2.spec` deletions are already present in commit `7a642bb`, so this deployment commit must not silently change them again. The workflow runs tests, builds `linux/amd64`, and publishes both `:deep-worker` and `:sha-<commit>` using `GITHUB_TOKEN` (`packages: write`). After the first successful publish, open the GitHub package page under `traffic-software/posting-app` and change its visibility to **Public**. Verify an unauthenticated pull can see it before creating the Railway app image service.

The deploy job is disabled until the GitHub repository variable `RAILWAY_ENABLED` equals `true`; publishing does not require Railway credentials.

## 2. Complete the Railway project

The project **`posting-browser-agent`** already exists in your Railway workspace (project ID `2b92fd9e-4c9c-4d49-8587-95fa1a9d7db2`, production environment ID `be1ff1ff-a1c2-45db-ab5e-f800f2ebb766`). Its empty **`app`** service exists (ID `6d744e5a-30b8-4634-84d1-8b7ebfe61982`). Do **not** create another project or app service. No Selenium service, app image source, volume, public domain, or variables have been configured yet.

In the Railway project UI, add a Docker Image service named **`selenium`** using `selenium/standalone-chrome:4.31.0`. Add a volume to the existing **`app`** service mounted at `/data`; a volume created on a different service will not persist `tasks.db`. After the first GHCR package is Public, set the existing app service's Docker image source to `ghcr.io/traffic-software/posting-app:deep-worker`. The local Railway CLI 5.28.1 panicked during volume creation on Windows, and service creation from the Selenium image was blocked by the command permission policy; use the Railway UI rather than assuming either action succeeded.

Keep the Selenium service **private** (no generated/public domain, TCP proxy, or VNC exposure). Place `app` and `selenium` in the same project **and environment** so `selenium.railway.internal` resolves. Set Selenium resources high enough for headless Chrome and verify its `/status` shows `value.ready=true`; Compose `shm_size` is not inherited by Railway. Set one app replica only: SQLite and the in-process task worker are not safe for multi-replica deployment.

In the **app** service, configure a Railway HTTP health check path `/ready` (wait for both DB/worker and Selenium). Generate a public Railway domain for app only, targeting app port 8000. The image honors Railway's `PORT` with default 8000; set `PORT=8000` if the domain/health routing needs an explicit port. Do not configure image auto-updates if GitHub Actions is responsible for redeploys.

## 3. Configure Railway service variables

Set non-secret values in the app service:

```text
DATABASE_PATH=/data/tasks.db
SELENIUM_REMOTE_URL=http://selenium.railway.internal:4444/wd/hub
PORT=8000
RAILWAY_RUN_UID=0
REQUIRE_TASK_API_TOKEN=true
ENABLE_WRITE_ACTIONS=false
```

Railway volumes mount as root; `RAILWAY_RUN_UID=0` lets this image write `/data/tasks.db` despite its default non-root `USER app`. Treat the mounted SQLite volume (which contains prompts/results) as sensitive; Railway volume data persists across redeploys, but a volume service has downtime during redeploy. Do not use an app replica count above one. If root runtime is unacceptable, replace it with a tested startup ownership strategy before removing `RAILWAY_RUN_UID=0`.

In the Railway **app service UI**, set `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME`, and a long random `TASK_API_TOKEN` as secret variables. Do not paste values into GitHub workflow, Dockerfile, logs, docs, or chat. No domain allowlist is required: browser tools permit public HTTP(S) websites and reject local/non-public literal or DNS-resolved addresses. These application checks do not cover browser subresources, pre-validation redirects or DNS rebinding; enforce Selenium network-level egress restrictions against internal, loopback, private, link-local and metadata destinations before exposing arbitrary browsing. A private Selenium service alone does not restrict its outbound traffic. Model must support tool calls. `/health` and `/ready` intentionally require no API token, while task POST/GET require the bearer token. Public deployment without a task token fails at startup.

For optional authorized account tasks, set `CREDENTIAL_FERNET_KEY` as a secret service variable, keep it stable while encrypted tasks are pending, and use `CREDENTIAL_TTL_SECONDS` (default 900). Server writes and task-level consent must both be enabled for credential entry. Fixed proxies use source-IP allowlisting; a provider must support Railway's actual stable egress arrangement before use—do not assume the public app domain or VPS IP is the Railway egress IP. See [account-tasks.md](account-tasks.md) for the API contract and limitations. No anti-detection/security bypass is implemented.

## 4. Enable automated deployment

Once the image is Public and the Railway app/Selenium/volume/variables/domain are healthy, create a **Railway project token** for its production environment. In GitHub repository settings add:

| Type | Name | Value |
| --- | --- | --- |
| Secret | `RAILWAY_TOKEN` | Railway project token, not an account-wide API token |
| Variable | `RAILWAY_PROJECT_ID` | `2b92fd9e-4c9c-4d49-8587-95fa1a9d7db2` |
| Variable | `RAILWAY_ENVIRONMENT_ID` | `be1ff1ff-a1c2-45db-ab5e-f800f2ebb766` |
| Variable | `RAILWAY_APP_SERVICE_ID` | `6d744e5a-30b8-4634-84d1-8b7ebfe61982` |
| Variable | `RAILWAY_APP_URL` | Public HTTPS app origin, no path |
| Variable | `RAILWAY_ENABLED` | `true` **only after** all above are ready |

The workflow pushes the new branch image before calling `railway redeploy --from-source`; the installed Railway CLI 5.28.1 supports this flag. It polls `GET /ready` until the response's `revision` equals the triggering commit SHA. A skipped deploy job before enablement is intentional. A failed health/revision check means the release has **not** been verified; inspect Railway deployment logs, image visibility, `/data` permissions and Selenium `/status`.

## 5. Smoke check and rollback

```bash
curl -fsS https://YOUR_APP_DOMAIN/ready
curl -i https://YOUR_APP_DOMAIN/task-status/00000000-0000-0000-0000-000000000000
# With TASK_API_TOKEN required, the second request must return 401.
curl -sS -X POST https://YOUR_APP_DOMAIN/run-task \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_TASK_API_TOKEN' \
  -d '{"prompt":"Read the heading of an approved demo page"}'
# Poll GET /task-status/{task_id} with the same bearer token.
```

Only run a live task after explicitly approving its destination and data sent to the model endpoint. Confirm completed result still resolves by ID after an app redeploy. For rollback, connect the app service source to a previously published `:sha-<commit>` image and redeploy; do not remove the volume. Avoid `railway down`, project deletion, or volume deletion unless you intend to lose service/data.

References: [Railway private registries](https://docs.railway.com/guides/private-container-registry), [private networking](https://docs.railway.com/networking/private-networking/how-it-works), [volumes](https://docs.railway.com/volumes), [healthchecks](https://docs.railway.com/deployments/healthchecks), [GitHub Container Registry](https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
