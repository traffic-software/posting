# Browser Task API

এই repository-র পুরোনো `GCW.py` / `ps_lib/` worker অপরিবর্তিত রেখে নতুন FastAPI + DeepAgents browser agent + local Chromium + Xvfb + PyAutoGUI task API যোগ করা হয়েছে। আর্কিটেকচার ও DFD: [plan/implementation-plan.md](plan/implementation-plan.md), [plan/dfd.md](plan/dfd.md)। GHCR ও Railway deployment: [docs/railway-deployment.md](docs/railway-deployment.md)। VPS deployment: [docs/vps-deployment.md](docs/vps-deployment.md)।

## Optional screenshot-grounded visual clicks

Set `ENABLE_BROWSER_VISION=true` only when your configured OpenAI-compatible endpoint and `MODEL_NAME` accept actual image input. No model/provider is changed automatically. The opt-in sends masked browser-content PNG image blocks directly in tool messages to that provider: visible page/account information may still be present. Input/textarea/select/contenteditable/private regions are covered temporarily without changing values, but masking cannot redact every sensitive page text. Cross-frame pages, shadow/custom-element regions, active animations, tainted/WebGL canvases, uncertain geometry and DPR other than 1 are rejected. Supported 2D canvas pixels are fingerprinted so redraws invalidate old targets.

`capture_browser_screenshot` returns an in-memory content-only PNG (maximum 1920×1200 and 2 MB) plus an opaque 15-second one-use `screenshot_id`. When normal DOM discovery is insufficient, the model may call `click_screenshot_coordinate(screenshot_id, x, y)` using pixels in that image, not desktop coordinates. Clicks require existing server/task write permission, challenge/destination checks, a fresh unchanged document/window/viewport/scroll/control epoch, and a safe live hit target. Secret/file/form input controls and frames are not visual click targets. Any attempted click consumes its token; navigation, interaction, mutation or manual resume requires a new image. One physical left click is dispatched; its receipt is not proof of success. No new typing, drag/drop, file or OS actions are enabled.

Images are not hosted, written to disk or added to observations/diagnostic prompts/task results. They remain in the in-memory agent message history until the task ends. **External tracing/callbacks may capture full model/tool messages**: disable tracing for sensitive vision tasks or apply separately reviewed provider-side retention controls; application redaction does not sanitize third-party tracing. Provider image rejection stops visual execution with a capability limitation, invalidates tokens and leaves normal DOM tools available for a new task. Live configured-provider vision support is unverified unless separately tested; automated checks use mock providers and synthetic browser data only. Existing user UC flags and local driver safety checks are unchanged.

Visual-feature verification in WSL: final focused safety/agent/account regressions **135 passed in 6.15s**; real synthetic normal-mode canvas/image-adapter plus focused regressions **95 passed in 20.94s**. Full current-state default suite: **372 passed, 2 failed, 8 skipped in 14.40s**; the two existing runtime kwargs failures expect UC disabled while the user retains UC enabled. The synthetic visual integration explicitly forces normal mode only inside its isolated test fixture, without changing application flags or bypassing local driver identity checks; it is not UC-mode or live-provider certification. Images are delivered as actual multimodal ToolMessage blocks through the installed ChatOpenAI adapter, not stringified base64. Test coverage includes one-use/expiry/bounds/NaN/bools, geometry/document/scroll/mutation/manual-epoch invalidation, canvas redraws, masking restoration, image redaction, write/tool availability and provider rejection. No external provider request was made.

## File uploads, downloads and expiring direct links

Optional `ENABLE_FILE_TRANSFERS=true` enables URL-sourced uploads and task-scoped downloads of any file type as opaque bytes—no execution, installation or archive extraction. Completed output files appear in the top-level `artifacts` array of the authenticated task-status response with expiring direct download URLs; these links require no Authorization header, so anyone holding a link can download until expiry. Input-only and partial files are never published. Configuration, request examples, quotas and deployment precautions: [docs/file-transfers.md](docs/file-transfers.md).

## চালু করা

1. `.env.example` অনুসরণ করে **নিজের** `.env` তৈরি করুন। আপনার বিদ্যমান `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME` রাখুন। Public website browse করার জন্য domain allowlist configure করতে হবে না। Base URL-র model-কে tool calling সমর্থন করতে হবে। `.env` Git বা Docker image-এ যায় না।
2. `docker compose up --build -d` চালান। App `127.0.0.1:8000`-তে; Chromium ও virtual display একই non-root app container-এ। `docker compose ps`-এ app healthy হওয়া পর্যন্ত অপেক্ষা করুন।
3. `.env`-এ `TASK_API_TOKEN` সেট করলে প্রতিটি task request-এ `Authorization: Bearer <token>` পাঠাতে হবে। Public interface-এ publish করার আগে token, reverse proxy/TLS এবং rate limiting নিশ্চিত করুন; ডিফল্ট localhost binding রেখে দিন।

```bash
curl -sS -X POST http://127.0.0.1:8000/run-task \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_TASK_API_TOKEN' \
  -d '{"prompt":"Open https://example.com and report the page heading"}'
# {"task_id":"...","status":"PENDING"}  (HTTP 202)

curl -sS http://127.0.0.1:8000/task-status/YOUR_TASK_ID \
  -H 'Authorization: Bearer YOUR_TASK_API_TOKEN'
# status: PENDING / PROCESSING / COMPLETED / FAILED
```

`TASK_API_TOKEN` ফাঁকা থাকলে উদাহরণের Authorization header বাদ দিতে পারেন, তবে তখন শুধু trusted local environment ব্যবহার করুন। Railway deployment-এ `REQUIRE_TASK_API_TOKEN=true` বাধ্যতামূলক। `GET /health` API ও task DB/worker পরীক্ষা করে; `GET /ready` অতিরিক্তভাবে local Chromium/ChromeDriver/Xvfb prerequisites পরীক্ষা করে (browser launch নয়)। ভুল UUID-তে 422, অজানা UUID-তে 404, capacity পূর্ণ হলে 429। API-তে কোনো ফল সফলভাবে সেভ হলে app restart-এর পরেও একই ID-তে পাওয়া যায়।

## WSL Ubuntu — Docker ছাড়া manual tasks

This machine's native Linux setup uses Ubuntu's Python 3.14.4, an isolated venv at `/home/md_soriful_islam/.local/share/posting/.venv`, `requirements.lock`, and matching Chrome for Testing/ChromeDriver **154.0.8037.92**. The Windows `.venv` is unchanged. Linux desktop prerequisites and noVNC assets are installed inside Ubuntu.

From this repository, `./run-wsl.ps1` starts the API in the foreground on **127.0.0.1:8001** (optional `-Port` override); Ctrl+C stops it. It reads the existing `.env` without displaying secrets and overrides the database to `/home/md_soriful_islam/.local/share/posting/manual/tasks.db`, separate from existing tasks. This launcher targets the provisioned Ubuntu user `md_soriful_islam`; it is not a fresh-machine installer.

- Open `http://127.0.0.1:8001/docs`, expand `POST /run-task`, choose **Try it out**, and submit your own prompt. If `TASK_API_TOKEN` is configured, put `Bearer <your token>` in the `authorization` header input. Use the returned ID with `GET /task-status/{task_id}` and the same header.
- `/health` and `/ready` are local checks; `/ready` checks prerequisites, not a full browser launch or model connectivity. Real task submission uses the configured model and can incur charges.
- The WSL-only Xvfb wrapper uses Linux abstract sockets to avoid WSLg's reserved filesystem socket directory. Ephemeral browser files use the short Linux-native `$HOME/.posting-runtime` path; persistent profiles use `$HOME/.local/share/posting/manual/profiles`, not a Windows mount. `PYVIRTUALDISPLAY_DISPLAYFD=0` keeps abstract-only Xvfb on high display numbers so Xlib/Openbox/Chrome cannot collide with WSLg's filesystem `:0` socket.
- Keep the service localhost-only. No real task/model request is sent by the launcher.

## Local development — code edit করলে auto-reload

প্রথমবার development container চালান:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build -d
```

এরপর `app/`-এর Python files edit/save করলে Uvicorn polling দিয়ে পরিবর্তন শনাক্ত করে app process স্বয়ংক্রিয়ভাবে restart করবে। Container চলতে থাকবে; প্রতিবার build বা run command দিতে হবে না। `app/` read-only bind mount হয়, host `.env`/virtualenv/repository পুরোটা mount হয় না। Existing non-root user, localhost port **8000**, healthcheck এবং `tasks_data` database volume বজায় থাকে।

Reload logs দেখুন:

```bash
docker compose -f compose.yaml -f compose.dev.yaml logs -f app
```

- `requirements.txt`/`requirements.lock`, Dockerfile বা browser/OS packages বদলালে উপরের `up --build -d` আবার চালাতে হবে। Dependency input বদলালে lockfile-ও regenerate করুন। Environment/Compose configuration বদলালে container recreate প্রয়োজন; Python reload তা apply করে না।
- Auto-reload **শুধু local development**-এর জন্য। Code edit চলমান browser task interrupt করতে পারে এবং viewer disconnect হবে; active task শেষ করে edit করুন। এটি seamless task migration নয়।
- বন্ধ করতে `docker compose -f compose.yaml -f compose.dev.yaml down` চালান। **`down -v` চালাবেন না**—এটি database volume মুছে দেয়।
- Reload ছাড়া আগের setup: `docker compose up --build -d`। Development override explicit opt-in; production Compose/Dockerfile command পরিবর্তন করা হয়নি।

## অসম্পূর্ণ কাজের রিপোর্ট

নতুন execution failure-এ `result: null`-এর বদলে `result.output`-এ ব্যাখ্যা থাকে। Browser বন্ধ করার পরে একই configured model-কে সীমিত, redacted tool observations দিয়ে একবার বিশ্লেষণ করতে বলা হয়—কী চেষ্টা হয়েছে, কোথায় থেমেছে, কোন কারণ evidence দিয়ে জানা যাচ্ছে এবং কী যাচাই হয়নি। এই reporting call-এর timeout সর্বোচ্চ ১০ সেকেন্ড; এটি browser action বা task retry করে না। Model unavailable হলে বা shutdown/restart/credential expiry হলে factual fallback থাকে; agent analysis পাওয়া যায়নি বলা হয়। Raw exception, credentials বা OTP প্রকাশ করা হয় না।

উদাহরণ (শুধু illustration, কোনো নির্দিষ্ট task-এর diagnosis নয়):

```json
{
  "status": "FAILED",
  "result": {
    "output": "পেজ খোলার চেষ্টা করেছি, কিন্তু browser service operation শেষ করতে পারেনি। পেজের তথ্য বা login outcome যাচাই করা যায়নি। Website কেন ব্যর্থ হয়েছে তা পাওয়া evidence থেকে নিশ্চিত নয়।"
  },
  "error": "Task execution failed"
}
```

`COMPLETED` মানে agent execution শেষ হয়েছে, requested login/action নিশ্চিত সফল হয়েছে নয়। স্বাভাবিক final response-এও অসম্পূর্ণ কাজের কারণ এবং observed outcome বলতে agent-কে নির্দেশ দেওয়া হয়। পুরোনো FAILED record-এর observations সংরক্ষিত না থাকলে পুরোনো task-এর কারণ পুনর্গঠন করা হয় না।

## Account login

Prompt-এ workflow দিন, password নয়। Structured `credentials` ও exact HTTPS login origins দিয়ে authorized account task পাঠানো যায়। Task-specific proxy support বন্ধ; non-null `proxy` request reject হয়। Server ও task—দুই জায়গায় write permission প্রয়োজন। Test-এ encryption key না দিলে app temporary key তৈরি করে; production/restart recovery-র জন্য persistent key configure করুন। Request format, secure client ও সীমাবদ্ধতা: [docs/account-tasks.md](docs/account-tasks.md)। সাধারণ Selenium WebDriver backend ব্যবহার করা হয়, তবে CAPTCHA/2FA/access-control bypass বা proxy-auth plugin যোগ করা হয়নি।

Optional structured credential `totp_secret` দিলে PyOTP দিয়ে authenticator-app 2FA support পাওয়া যায়: `fill_totp(selector, submit_selector, credential_id)` OTP সরাসরি Selenium দিয়ে fill ও submit করে। `inspect_totp_form` supported field selectors খুঁজে দেয়; single numeric field ও ছয়টি digit box support আছে। Code `TOTP.now()` দিয়ে তৈরি হয়। Seed/code model-কে দেওয়া হয় না; secure CLI mode: `.venv/Scripts/python.exe scripts/submit_account_task.py --account`। Prompt-এ seed দেবেন না। Local browser সাধারণ Selenium দিয়ে চালু হয়; credential/TOTP tools আগের Selenium-compatible interface ব্যবহার করে। CAPTCHA, SMS/email/recovery ও suspicious-login challenge-এ থামে। বিস্তারিত [account task docs](docs/account-tasks.md#authenticator-app-totp)।

Username/password দেওয়ার আগে agent `inspect_login_form(credential_id)` দিয়ে actual DOM-এর visible/editable input ও continuation button-এর structural selector নেয়; page text দেখে selector অনুমান করতে বলা হয় না। Username → Next → password transition-এর পরে আবার inspect করে। Discovery values/labels/HTML ফেরত দেয় না, এবং ambiguous controls হলে অনুমান করে action নেওয়া নয়।

## একই container-এ browser ও PyAutoGUI

API, Selenium-backed Chromium/ChromeDriver এবং task-scoped Xvfb একই app image-এ থাকে। Browser চালুর আগে `pyvirtualdisplay` display তৈরি করে এবং Openbox window manager ready হয়; তারপর Chrome ও PyAutoGUI একই DISPLAY-তে কাজ করে। এক সময়ে একটি task desktop ব্যবহার করে; শেষে browser/profile/display cleanup হয়। Linux container ছাড়া real runtime চালানো হয় না—Windows host desktop fallback নেই। `--workers 1` ও এক replica বজায় রাখুন।

Agent `inspect_page` → discovered control → click/type/hover/scroll/key → outcome inspection অনুসরণ করে। `hover_element`, `scroll_element`, `press_key` ও সাধারণ click/type PyAutoGUI adapter ব্যবহার করে; সব interaction write gates মানে। Arbitrary coordinates, desktop shortcuts, file dialogs, clipboard এবং screenshot uploads দেওয়া হয় না। ASCII text PyAutoGUI দিয়ে, nonsecret Unicode text Selenium দিয়ে দেওয়া হয়। Password/OTP dedicated guarded Selenium tools দিয়েই যায়।

Image rebuild/redeploy প্রয়োজন; পুরোনো Selenium service আর প্রয়োজন নেই। Existing production container সরানো/deploy করা আলাদা operational action; migration আগে active task শেষ ও data backup নিশ্চিত করুন। `CHROMIUM_BINARY`, `CHROMEDRIVER_BINARY`, `BROWSER_WINDOW_WIDTH/HEIGHT` local config, default screen `1024×768`। `/ready` শুধু prerequisites যাচাই করে; real browser smoke test আলাদা।

Guarded `double_click_element`, `drag_element`, `select_all_text` এবং ordinary `contenteditable` fill support-ও আছে। Optional Cloudflare `web-search` অপরিচিত/অস্পষ্ট কাজে public documentation খুঁজতে সাহায্য করে। Optional workflow memory একই profile ও HTTPS origin-এর যাচাইকৃত semantic flow task DB-তে রাখে; শুধু `COMPLETED` বা model-এর দাবি দিয়ে save হয় না। Configuration, caller-defined success criteria, privacy ও limitations: [agent capability docs](docs/agent-capabilities.md)।

### Browser compatibility ও login সীমাবদ্ধতা

Docker base `python:3.14.8-slim`। Slim image-এ desktop runtime libraries explicitly install করে official Chrome for Testing **154.0.8037.92** browser এবং একই exact version-এর ChromeDriver `/opt/chrome-for-testing`-এ install করা হয়। `/usr/bin/chromium` এবং `/usr/bin/chromedriver` নতুন pair-এ link করা; existing configuration বদলাতে হবে না। Build exact versions ও missing shared libraries যাচাই করে। CfT Linux64-এর জন্য **linux/amd64** প্রয়োজন; native arm64 supported নয়।

পরের update-এ Dockerfile-এর `CFT_VERSION` official Stable metadata অনুযায়ী বদলান: https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json । Browser ও driver একই version-এ রাখুন। একবার rebuild/recreate করতে হবে; Python code edits-এর auto-reload আগের মতো থাকবে:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build -d
docker compose exec app sh -c 'chromium --version; chromedriver --version'
```

Python 3.14 slim base ব্যবহার করা হয়; UC ও তার `setuptools<81` compatibility shim সরানো হয়েছে। Version/library checks browser launch compatibility প্রমাণ করে না—নিচের synthetic integration tests চালান।

Selenium integration Google sign-in নিশ্চিত করে না। Browser age, hosting IP reputation ও Google account/security policy-র কারণে “This browser or app may not be secure” rejection থাকতে পারে। Rejection/CAPTCHA/2FA controls bypass করা এই পরিবর্তনের উদ্দেশ্য নয়; supported up-to-date browser-এ manual login বা service-এর official OAuth/API workflow ব্যবহার করুন। Agent-running mode remains backend read-only. The profile panel supports owner-only standalone manual browsing and bounded task manual-control handoff; website acceptance of manual Google login is not guaranteed.

### SeleniumBase migration status

SeleniumBase **4.55.0** `Driver()` in normal headed Chrome mode is the sole runtime backend: no `BROWSER_BACKEND` selector, raw-Selenium fallback, UC or CDP mode. The application still owns Xvfb/Openbox, PyAutoGUI, the read-only viewer and task cleanup. Existing tool permissions, URL/credential guards, readiness and write behavior are unchanged; broader SeleniumBase helper adoption is deferred.

Docker provisions a root-owned `seleniumbase/drivers/chromedriver` symlink to `/usr/bin/chromedriver` and sets `SE_OFFLINE=true` plus `SE_CHROMEDRIVER=/usr/bin/chromedriver` to prevent Selenium Manager fallback downloads. Preflight requires an executable package slot resolving to the configured driver (`samefile`) and an exact full browser/driver version match. Startup passes that exact `driver_version` and verifies the returned driver's service executable identity; it does not silently select another backend or download a replacement on preflight failure.

**Accepted security tradeoff:** normal SeleniumBase Chrome adds `--no-sandbox` and certificate/SSL-error ignore behavior upstream. The user explicitly accepted this behavior; it is **not security parity** with the previous launcher. `enable_ws=True` does not restore the Linux sandbox or TLS certificate validation. Container restrictions and application/viewer guards remain necessary but do not replace those protections. See the [implementation record and verification checklist](plan/seleniumbase-migration-plan.md).

## Live display viewer — browser থেকে দেখা

`/desktop` is the authenticated **browser profile and live desktop panel**. Create a display label, select a profile and choose **Open browser** to launch headed Chrome on a neutral page without an agent task or model call. Navigate and authenticate directly inside Chrome using mouse/keyboard. **Close browser** gracefully saves Chrome's state, tears down the desktop and releases the runtime/profile leases. No password/OTP fields, cookie export or profile deletion endpoints are provided.

Profiles persist independently: reopening A restores A's state; B has its own directory. Existing requests without a profile ID still use disposable temporary profiles. One browser owns the runtime; switching profiles requires closing first. Manual sessions default to **30 minutes**, also bounded by viewer-cookie expiry and **60 seconds** disconnected grace. A live authenticated desktop socket keeps the owner connected; status polling alone does not extend disconnected grace. Logout closes manual access. Expiry is warned in the panel's last minute. `MANUAL_BROWSER_SECONDS`, `TASK_MANUAL_SECONDS` (default **10 minutes**) and `MANUAL_DISCONNECTED_GRACE_SECONDS` configure these limits. If the viewer cookie expires sooner, manual browsing ends sooner.

Submit tasks with the selected opaque ID (not a path):

```json
{"prompt":"Open https://example.com and report the heading", "browser_profile_id":"0123456789abcdef0123456789abcdef"}
```

Use your actual panel-generated ID and task API Bearer token; persistent-profile tasks require configured task authentication. Add `"allow_write_actions":true` only with explicit task consent and server `ENABLE_WRITE_ACTIONS=true`. CLI: `scripts/submit_account_task.py --browser-profile ID --prompt "Your task"` (optional `--allow-write-actions`); this mode submits **no structured credentials**. For WSL, set the client destination to `TASK_API_URL=http://127.0.0.1:8001`; profile-only mode permits loopback HTTP, while credential submission still requires HTTPS. The existing legacy account-test mode is unrelated and should not be used for manual-profile tasks.

Tasks may queue while standalone browsing is open but stay `PENDING` without consuming their execution budget. Close browsing to wake the worker. Chrome restarts intentionally for task reuse of the same profile; a live manual WebDriver is never transferred to the agent.

During a running task, **Take manual control** requests a pause. A complete bounded tool/model action finishes before input is enabled; no new model calls, tools or screenshots run during acknowledged manual control. Database status stays `PROCESSING`; the panel exposes `pause_requested`, `manual`, `resuming` separately. Only acknowledged manual time is excluded from the shared execution budget; cancellation and credential expiry remain binding. **Resume agent** first revokes input, retires sockets, resets held X11 keys/buttons and starts a new backend read-only generation, then takes a fresh page observation before releasing the agent. Manual timeout/owner expiry/failed handoff fails and closes the task instead of silently resuming while someone is typing.

WSL profiles live beneath `$HOME/.local/share/posting/manual/profiles`, outside the Windows mount. Compose persists `/data/browser_profiles` in `tasks_data`. Linux profile directories use mode 700 and metadata/lease files 600; IDs and symlink containment are checked and concurrent filesystem leases are rejected. Chrome's lock files are never automatically deleted. Session material is excluded from Git/build context. Back up the volume privately; `down -v` destroys both tasks and profiles. Restart/reload retains profiles but interrupts live sessions and processing tasks; unfinished writes are not retried automatically. Keep **one process, one worker, one replica**.

নিজের `.env`-এ আলাদা viewer configuration দিন; token এখানে বা task prompt-এ পাঠাবেন না:

```dotenv
DISPLAY_VIEWER_ENABLED=true
DISPLAY_VIEWER_TOKEN=replace-with-a-separate-long-random-token
DISPLAY_VIEWER_ORIGIN=http://127.0.0.1:8001
DISPLAY_VIEWER_SESSION_SECONDS=1800
```

Image rebuild এবং container recreate প্রয়োজন। Existing local manual-test API port 8001 হলে browser-এ **http://127.0.0.1:8001/desktop** খুলে viewer token দিয়ে login করুন। `localhost` ও `127.0.0.1` ভিন্ন origin: configured origin-এর exact URL ব্যবহার করুন। Remote viewer-এর জন্য HTTPS origin প্রয়োজন; VPS উদাহরণ `https://webagent.elgrowth.com/desktop`। Nginx-এর updated `/desktop/ws` upgrade location apply না হলে live stream connect হবে না।

Security: the viewer token is a **privileged signed-in-account credential**, separate from the task API token. Cookies are HttpOnly/SameSite=Strict (Secure on remote HTTPS), with bounded expiry. Profile/control mutations and profile listing require the exact configured Origin. WebSocket sessions are authenticated, generation-bound and loopback-only; raw VNC ports are not published. Agent mode uses x11vnc `-viewonly` server-side, not just noVNC UI flags. Interactive generations accept only their authenticated owner cookie; other viewer sessions cannot connect. Mode changes retire old sockets. Wayland environment filtering remains enabled for both modes. Clipboard synchronization/import/export remains disabled (no paste feature); mouse and keyboard are enabled only after backend manual readiness. Viewer pixels are not saved or sent to the model. Trust every operator holding either privileged token; this is not a multi-user account authorization product. Manual navigation is operator-driven and is not subject to the agent's URL/write gates; maintain deployment network egress isolation.

Feature default-এ disabled। Initial read-only viewer failure does not stop a browser task, but standalone manual startup or a mode-transition failure fails closed. At task/session completion, its VNC backend and streams stop; ephemeral profiles are removed and persistent profiles are retained. Production deploy বা Docker security-policy change স্বয়ংক্রিয়ভাবে করা হয় না; test-only seccomp profile-এর অনুমোদন production-এ প্রযোজ্য নয়।

## Browser policy ও সীমা

- Agent runtime `deepagents.create_deep_agent` ব্যবহার করে। Planning (`write_todos`), task-local virtual filesystem ও planning-only subagent আছে; filesystem backend `StateBackend`, তাই host filesystem বা shell access দেওয়া হয় না। Subagent-এর browser/credential tools নেই; browser actions শুধু main agent-এর policy-checked Selenium tools দিয়ে হয়। Virtual files task শেষ হলে persist করা হয় না।
- যেকোনো public HTTP(S) website browse করা যায়; domain allowlist লাগে না। Embedded credentials, localhost/local নাম ও non-public IP নিষিদ্ধ। DNS-এর কোনো address private/non-public হলে URL reject হয়। Website-এর login, access control বা anti-bot restriction bypass করা হয় না।
- URL validation সম্পূর্ণ SSRF isolation নয়: **redirect request আগেই পাঠানো হতে পারে**, browser subresource request আলাদাভাবে যাচাই হয় না এবং DNS rebinding সম্ভব। Public deployment-এ app container-এর জন্য network-level egress firewall/proxy দিয়ে private/internal, loopback, link-local, metadata ও non-public network access আটকাতে হবে। App-side DNS check Chrome-এর connection-এর বিকল্প নয়।
- ডিফল্টে শুধু `navigate_to_page` ও `extract_text` আছে। `ENABLE_WRITE_ACTIONS=true` দিলে `click_element` ও `fill_element` tool পাওয়া যাবে; এরা form submit/বাহ্যিক side effect ঘটাতে পারে। অনুমোদিত test site ছাড়া enable করবেন না। CAPTCHA bypass বা legacy worker tool দেওয়া হয়নি।
- প্রতিটি task আলাদা local Selenium WebDriver session ব্যবহার করে। Model request, page load ও agent step-এর সীমা আছে; task wall-clock budget **hard kill নয়**—কোনো external call আটকে থাকলে thread তাৎক্ষণিক বন্ধ হবে না। Provider-এর error/credentials API response-এ ফেরত দেওয়া হয় না।
- Task DB named volume `tasks_data`-তে `/data/tasks.db`; `docker compose down` এটি রাখে, কিন্তু `docker compose down -v` volume **মুছে দেয়**। আগে backup করুন। পুরোনো `ps_lib/databases.db` এই নতুন task DB নয়। User prompt ও final output DB-তে থাকে; sensitive prompt পাঠানো ও retention policy আলাদাভাবে বিবেচনা করুন। Restart-এ মাঝপথে থাকা PROCESSING task FAILED হয়, PENDING task আবার worker নেয়; write operation-এ duplicate side effect এড়াতে automatic retry হয় না।
- একটি app process/worker ও SQLite MVP; horizontal scaling বা durable queue/ownership দরকার হলে PostgreSQL ও dedicated queue/worker নিন।

## Testing

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.lock  # Windows Git Bash
.venv/Scripts/python.exe -m pytest -q tests
# Linux/macOS: .venv/bin/python -m pytest -q tests
```

Tests fake model/browser ব্যবহার করে, তাই credentials, live site বা network লাগে না। Live smoke test করার আগে একটি public test URL নির্বাচন ও tool-calling endpoint configure করুন; তারপর POST ও GET দিয়ে result যাচাই করুন। Deploy/cleanup-এর আগে [plan/unnecessary-files.md](plan/unnecessary-files.md)-এ তালিকাভুক্ত পুরোনো ফাইল ও বর্তমান tracked deletion যাচাই করুন—এই feature কোনো legacy file মুছে দেয়নি।

### Local-browser integration verification

2026-10-04 verification: **290 focused Windows tests passed** (not the full suite); `uv pip check` passed. The alternate `posting:seleniumbase-smoke` image, based on existing `posting:selenium-verification` with the exact new lock and root-owned driver symlink, passed **5 Linux integration tests in 83.53s**, non-root with `--network none --shm-size=1g`. Coverage included desktop actions/cleanup, worker-thread startup and cross-thread cancellation/recovery, synthetic agent tools and authenticated read-only viewer sessions; provisioning hooks received zero calls. Openbox's one-pixel geometry variance was accepted with DPR 1 verified. **The clean Dockerfile build remains uncertified** because apt DNS resolution failed. Linux constructor-failure cleanup and production egress controls remain untested; see the [verification record](plan/seleniumbase-migration-plan.md).

Synthetic page tests do not use real credentials, external sites or a model endpoint. After building the image, run inside the Linux image (Linux shell example):

```bash
docker build -t posting-local-browser:verification .
docker run --rm --network none --shm-size=2g --security-opt "seccomp=$PWD/tests/chromium-test-seccomp.json" -e RUN_LOCAL_BROWSER_INTEGRATION=1 -e PYTHONPATH=/srv/app -v "$PWD/tests:/verification:ro" --entrypoint python posting-local-browser:verification -m pytest -q /verification/test_local_browser_integration.py
```

Normal unit-test runs skip these opt-in tests. The retained test-only seccomp profile preserves Moby's default deny policy and other restrictions while allowing `clone`, `setns` and `unshare`. Those allowances do not re-enable Chromium's namespace sandbox when SeleniumBase launches with `--no-sandbox`. Baseline: https://raw.githubusercontent.com/moby/profiles/main/seccomp/default.json (SHA-256 `6416b47770785a41ac59073cdc77d9fe98517df2799dc83ef207e622de3053f6`). The container is not privileged. This is an explicitly approved isolated-test configuration, not a production Compose/daemon policy change. Do not apply it to production without a separate security review and authorization.

The image copies the noVNC `core` and `vendor` modules with symlinks resolved; obsolete Flash assets are not needed. Browser tasks use SeleniumBase's normal headed `Driver()` and the preprovisioned package-local ChromeDriver symlink, with exact-version and executable-identity checks described above. The system driver is not patched or copied. Tasks without a profile ID have an isolated temporary profile; selected persistent profiles are leased and retained after graceful Chrome shutdown. Normal WebDriver automation identity remains unchanged. Upstream sandbox disabling and certificate-error bypass are accepted exceptions, not security parity. Cleanup closes the driver and stops its owned service, including failed startup, before removing task files. The viewer negotiates noVNC's `binary` WebSocket subprotocol when offered, while still accepting clients without a subprotocol. Viewer disconnects during socket cleanup are treated as normal disconnects.

`/ready` checks prerequisites only; it does not prove Chromium can launch or that PyAutoGUI coordinates work. Default Docker seccomp can still block Chromium startup. A failed image build or skipped integration test is not a verified browser deployment.

### Persistent profiles and manual-control verification

WSL verification (2026-10-05): **359 tests passed, zero failures/skips** with the full suite and `RUN_LOCAL_BROWSER_INTEGRATION=1`, using `$HOME/.local/share/posting/.venv/bin/python`, before a subsequent external edit enabled `undetectable`, `uc` and `uc_subprocess` in the runtime. Those current flags contradict the approved normal-WebDriver/UC-off plan and the migration descriptions below; the earlier real-browser result does not certify that externally changed runtime. The implementer preserved the external edit rather than reverting it. The final current-state default suite reported **353 passed, 2 failed, 7 skipped** in 23.64 seconds; both failures are the existing normal-mode argument assertions in `test_desktop_runtime.py`. Final focused profile/session/viewer/driver-safety/client checks reported **87 passed** in 10.28 seconds. No local-driver safety check was bypassed and no current-UC real-browser certification is claimed. The strengthened history-UI and paused synthetic logout/login integration assertions were added after the normal-mode full run and remain unverified in the current UC runtime. The synthetic noVNC panel test creates profile A, opens Chrome without an agent/model, types/clicks a synthetic local login through noVNC, closes and observes retained state in a queued task's new Chrome instance. It also verifies profile B isolation, reopening persistence/history, task manual-control transitions, fresh resume observation, wrong-owner/stale sockets and raw RFB input blocked by agent-mode x11vnc. No real-account authentication was performed; Google login acceptance remains unverified. Default runs skip the seven real-browser integration tests unless explicitly enabled.

Run the full suite from a directory without a real `.env`, with launcher-equivalent non-secret WSL runtime settings:

```bash
cd /tmp
export PYTHONPATH=/mnt/d/posting PATH="/mnt/d/posting/scripts/wsl-bin:$PATH"
export PYVIRTUALDISPLAY_DISPLAYFD=0 TMPDIR="$HOME/.posting-runtime"
export CHROMIUM_BINARY="$HOME/.local/share/posting/browser/chrome-linux64/chrome"
export CHROMEDRIVER_BINARY="$HOME/.local/share/posting/browser/chromedriver-linux64/chromedriver"
export SE_OFFLINE=true SE_CHROMEDRIVER="$CHROMEDRIVER_BINARY"
export DISPLAY_VIEWER_ASSETS=/opt/posting-novnc RUN_LOCAL_BROWSER_INTEGRATION=1
"$HOME/.local/share/posting/.venv/bin/python" -m pytest -q /mnt/d/posting/tests
```

The panel test binds `127.0.0.1:8001` when free, otherwise an ephemeral loopback port. It uses synthetic tokens and a local fixture, never the configured model or legacy account helper's credentials. Tests replace that helper's legacy account payload with synthetic values. Manual typing/navigation through Chrome is operator-driven; tests place the exact local fixture before sending noVNC login input and block HTTPS in synthetic desktop sessions to avoid accidental external searches. Existing SeleniumBase sandbox/TLS exceptions remain the accepted migration tradeoff, not a new security relaxation.

### Dynamic element readiness

Browser tools wait for the particular target, not for network idle. Read targets
must be visible; click targets must also be enabled and unobscured; fill targets
must also be editable. Offscreen targets may be scrolled into view once per live
target. Readiness is checked immediately and then every 100ms, returning as soon
as the target is ready. The existing browser timeout and remaining task deadline
bound the wait, and cancellation/policy checks continue during polling.

A readiness timeout reports the last blocker and asks the agent to inspect the
current page/form again; that invocation has not clicked or entered data. Waiting
never retries click, clear, typing or submission. Existing live-control identity,
credential-origin, TOTP and desktop focus checks remain in force. Readiness is not
a guarantee against subsequent DOM changes or future network activity.
