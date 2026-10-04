# Browser Task API

এই repository-র পুরোনো `GCW.py` / `ps_lib/` worker অপরিবর্তিত রেখে নতুন FastAPI + DeepAgents browser agent + local Chromium + Xvfb + PyAutoGUI task API যোগ করা হয়েছে। আর্কিটেকচার ও DFD: [plan/implementation-plan.md](plan/implementation-plan.md), [plan/dfd.md](plan/dfd.md)। GHCR ও Railway deployment: [docs/railway-deployment.md](docs/railway-deployment.md)। VPS deployment: [docs/vps-deployment.md](docs/vps-deployment.md)।

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

### Browser compatibility ও login সীমাবদ্ধতা

Docker base `python:3.14.8-slim`। Slim image-এ desktop runtime libraries explicitly install করে official Chrome for Testing **154.0.8037.92** browser এবং একই exact version-এর ChromeDriver `/opt/chrome-for-testing`-এ install করা হয়। `/usr/bin/chromium` এবং `/usr/bin/chromedriver` নতুন pair-এ link করা; existing configuration বদলাতে হবে না। Build exact versions ও missing shared libraries যাচাই করে। CfT Linux64-এর জন্য **linux/amd64** প্রয়োজন; native arm64 supported নয়।

পরের update-এ Dockerfile-এর `CFT_VERSION` official Stable metadata অনুযায়ী বদলান: https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json । Browser ও driver একই version-এ রাখুন। একবার rebuild/recreate করতে হবে; Python code edits-এর auto-reload আগের মতো থাকবে:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build -d
docker compose exec app sh -c 'chromium --version; chromedriver --version'
```

Python 3.14 slim base ব্যবহার করা হয়; UC ও তার `setuptools<81` compatibility shim সরানো হয়েছে। Version/library checks browser launch compatibility প্রমাণ করে না—নিচের synthetic integration tests চালান।

Selenium integration Google sign-in নিশ্চিত করে না। Browser age, hosting IP reputation ও Google account/security policy-র কারণে “This browser or app may not be secure” rejection থাকতে পারে। Rejection/CAPTCHA/2FA controls bypass করা এই পরিবর্তনের উদ্দেশ্য নয়; supported up-to-date browser-এ manual login বা service-এর official OAuth/API workflow ব্যবহার করুন। Live viewer read-only—সেখান থেকে manual login করা যায় না।

## Live display viewer — browser থেকে দেখা

`/desktop`-এ authenticated **read-only** noVNC viewer আছে। Container চললে পেজ খোলা যায়; task চললে active virtual display দেখা যায়, idle-এ কোনো desktop stream থাকে না। পরের task শুরু হলে valid session reconnect করে। Viewer দিয়ে mouse/keyboard/clipboard control দেওয়া যায় না।

নিজের `.env`-এ আলাদা viewer configuration দিন; token এখানে বা task prompt-এ পাঠাবেন না:

```dotenv
DISPLAY_VIEWER_ENABLED=true
DISPLAY_VIEWER_TOKEN=replace-with-a-separate-long-random-token
DISPLAY_VIEWER_ORIGIN=http://127.0.0.1:8001
DISPLAY_VIEWER_SESSION_SECONDS=900
```

Image rebuild এবং container recreate প্রয়োজন। Existing local manual-test API port 8001 হলে browser-এ **http://127.0.0.1:8001/desktop** খুলে viewer token দিয়ে login করুন। `localhost` ও `127.0.0.1` ভিন্ন origin: configured origin-এর exact URL ব্যবহার করুন। Remote viewer-এর জন্য HTTPS origin প্রয়োজন; VPS উদাহরণ `https://webagent.elgrowth.com/desktop`। Nginx-এর updated `/desktop/ws` upgrade location apply না হলে live stream connect হবে না।

Security: viewer token task API token থেকে আলাদা; cookie HttpOnly/SameSite=Strict, remote HTTPS-এ Secure, bounded lifetime। Raw VNC/noVNC ports publish হয় না—একই API port দিয়ে authenticated WebSocket proxy চলে, backend container loopback-only। Pixels model/task-result/database/logs-এ পাঠানো বা সেভ করা হয় না। তবে live screen-এ account identifiers বা অন্য sensitive তথ্য দেখা যেতে পারে; শুধু trusted operator-কে access দিন এবং screenshot/share করবেন না। এই single-operator viewer per-user/per-task authorization system নয়।

Feature default-এ disabled। Viewer failure task execution বন্ধ করবে না। Task শেষে its VNC backend ও existing stream বন্ধ হয়; display/profile cleanup আগের মতো থাকে। Production deploy বা Docker security-policy change স্বয়ংক্রিয়ভাবে করা হয় না; test-only seccomp profile-এর অনুমোদন production-এ প্রযোজ্য নয়।

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

Synthetic page tests do not use real credentials, external sites or a model endpoint. After building the image, run inside the Linux image (Linux shell example):

```bash
docker build -t posting-local-browser:verification .
docker run --rm --network none --shm-size=2g --security-opt "seccomp=$PWD/tests/chromium-test-seccomp.json" -e RUN_LOCAL_BROWSER_INTEGRATION=1 -e PYTHONPATH=/srv/app -v "$PWD/tests:/verification:ro" --entrypoint python posting-local-browser:verification -m pytest -q /verification/test_local_browser_integration.py
```

Normal unit-test runs skip these three tests. The test-only seccomp profile preserves Moby's default deny policy and other restrictions while allowing `clone`, `setns` and `unshare` for Chromium's namespace sandbox. Baseline: https://raw.githubusercontent.com/moby/profiles/main/seccomp/default.json (SHA-256 `6416b47770785a41ac59073cdc77d9fe98517df2799dc83ef207e622de3053f6`). The container is not privileged. This is an explicitly approved isolated-test configuration, not a production Compose/daemon policy change. Do not apply it to production without a separate security review and authorization.

The image copies the noVNC `core` and `vendor` modules with symlinks resolved; obsolete Flash assets are not needed. Browser tasks use standard Selenium WebDriver with an explicit local `Service(CHROMEDRIVER_BINARY)`, avoiding Selenium Manager and runtime driver downloads. The system driver is not patched or copied. Each task has fresh Chrome options and an isolated temporary profile. Standard automation identity is retained and `--no-sandbox` is not added. Cleanup closes the driver and stops its owned service, including failed startup, before removing task files. The viewer negotiates noVNC's `binary` WebSocket subprotocol when offered, while still accepting clients without a subprotocol. Viewer disconnects during socket cleanup are treated as normal disconnects.

`/ready` checks prerequisites only; it does not prove Chromium can launch or that PyAutoGUI coordinates work. Default Docker seccomp can still block Chromium startup. A failed image build or skipped integration test is not a verified browser deployment.

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
