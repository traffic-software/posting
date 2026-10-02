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

Prompt-এ workflow দিন, password নয়। Structured `credentials` ও exact HTTPS login origins দিয়ে authorized account task পাঠানো যায়। Task-specific proxy support বন্ধ; non-null `proxy` request reject হয়। Server ও task—দুই জায়গায় write permission প্রয়োজন। Test-এ encryption key না দিলে app temporary key তৈরি করে; production/restart recovery-র জন্য persistent key configure করুন। Request format, secure client ও সীমাবদ্ধতা: [docs/account-tasks.md](docs/account-tasks.md)। Anti-detect/security bypass বা proxy-auth plugin যোগ করা হয়নি।

Optional structured credential `totp_secret` দিলে PyOTP দিয়ে authenticator-app 2FA support পাওয়া যায়: `fill_totp(selector, submit_selector, credential_id)` OTP সরাসরি Selenium দিয়ে fill ও submit করে। `inspect_totp_form` supported field selectors খুঁজে দেয়; single numeric field ও ছয়টি digit box support আছে। Code `TOTP.now()` দিয়ে তৈরি হয়। Seed/code model-কে দেওয়া হয় না; secure CLI mode: `.venv/Scripts/python.exe scripts/submit_account_task.py --account`। Prompt-এ seed দেবেন না। Standard local Selenium-ই ব্যবহৃত হয়; undetected-chromedriver যোগ করা হয়নি। CAPTCHA, SMS/email/recovery ও suspicious-login challenge-এ থামে। বিস্তারিত [account task docs](docs/account-tasks.md#authenticator-app-totp)।

Username/password দেওয়ার আগে agent `inspect_login_form(credential_id)` দিয়ে actual DOM-এর visible/editable input ও continuation button-এর structural selector নেয়; page text দেখে selector অনুমান করতে বলা হয় না। Username → Next → password transition-এর পরে আবার inspect করে। Discovery values/labels/HTML ফেরত দেয় না, এবং ambiguous controls হলে অনুমান করে action নেওয়া নয়।

## একই container-এ browser ও PyAutoGUI

API, standard Chromium/ChromeDriver এবং task-scoped Xvfb একই app image-এ থাকে। Browser চালুর আগে `pyvirtualdisplay` display তৈরি করে এবং Openbox window manager ready হয়; তারপর Chrome ও PyAutoGUI একই DISPLAY-তে কাজ করে। এক সময়ে একটি task desktop ব্যবহার করে; শেষে browser/profile/display cleanup হয়। Linux container ছাড়া real runtime চালানো হয় না—Windows host desktop fallback নেই। `--workers 1` ও এক replica বজায় রাখুন।

Agent `inspect_page` → discovered control → click/type/hover/scroll/key → outcome inspection অনুসরণ করে। `hover_element`, `scroll_element`, `press_key` ও সাধারণ click/type PyAutoGUI adapter ব্যবহার করে; সব interaction write gates মানে। Arbitrary coordinates, desktop shortcuts, file dialogs, clipboard এবং screenshot uploads দেওয়া হয় না। ASCII text PyAutoGUI দিয়ে, nonsecret Unicode text Selenium দিয়ে দেওয়া হয়। Password/OTP dedicated guarded Selenium tools দিয়েই যায়।

Image rebuild/redeploy প্রয়োজন; পুরোনো Selenium service আর প্রয়োজন নেই। Existing production container সরানো/deploy করা আলাদা operational action; migration আগে active task শেষ ও data backup নিশ্চিত করুন। `CHROMIUM_BINARY`, `CHROMEDRIVER_BINARY`, `BROWSER_WINDOW_WIDTH/HEIGHT` local config, default screen `1024×768`। `/ready` শুধু prerequisites যাচাই করে; real browser smoke test আলাদা।

## Browser policy ও সীমা

- Agent runtime `deepagents.create_deep_agent` ব্যবহার করে। Planning (`write_todos`), task-local virtual filesystem ও planning-only subagent আছে; filesystem backend `StateBackend`, তাই host filesystem বা shell access দেওয়া হয় না। Subagent-এর browser/credential tools নেই; browser actions শুধু main agent-এর policy-checked Selenium tools দিয়ে হয়। Virtual files task শেষ হলে persist করা হয় না।
- যেকোনো public HTTP(S) website browse করা যায়; domain allowlist লাগে না। Embedded credentials, localhost/local নাম ও non-public IP নিষিদ্ধ। DNS-এর কোনো address private/non-public হলে URL reject হয়। Website-এর login, access control বা anti-bot restriction bypass করা হয় না।
- URL validation সম্পূর্ণ SSRF isolation নয়: **redirect request আগেই পাঠানো হতে পারে**, browser subresource request আলাদাভাবে যাচাই হয় না এবং DNS rebinding সম্ভব। Public deployment-এ app container-এর জন্য network-level egress firewall/proxy দিয়ে private/internal, loopback, link-local, metadata ও non-public network access আটকাতে হবে। App-side DNS check Chrome-এর connection-এর বিকল্প নয়।
- ডিফল্টে শুধু `navigate_to_page` ও `extract_text` আছে। `ENABLE_WRITE_ACTIONS=true` দিলে `click_element` ও `fill_element` tool পাওয়া যাবে; এরা form submit/বাহ্যিক side effect ঘটাতে পারে। অনুমোদিত test site ছাড়া enable করবেন না। CAPTCHA bypass বা legacy worker tool দেওয়া হয়নি।
- প্রতিটি task আলাদা Remote WebDriver session ব্যবহার করে। Model request, page load ও agent step-এর সীমা আছে; task wall-clock budget **hard kill নয়**—কোনো external call আটকে থাকলে thread তাৎক্ষণিক বন্ধ হবে না। Provider-এর error/credentials API response-এ ফেরত দেওয়া হয় না।
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
docker run --rm --shm-size=2g --security-opt "seccomp=$PWD/tests/chromium-test-seccomp.json" -e RUN_LOCAL_BROWSER_INTEGRATION=1 -e PYTHONPATH=/srv/app -v "$PWD/tests:/verification:ro" --entrypoint python posting-local-browser:verification -m pytest -q /verification/test_local_browser_integration.py
```

Normal unit-test runs skip these three tests. The test-only seccomp profile preserves Moby's default deny policy and other restrictions while allowing `clone`, `setns` and `unshare` for Chromium's namespace sandbox. Baseline: https://raw.githubusercontent.com/moby/profiles/main/seccomp/default.json (SHA-256 `6416b47770785a41ac59073cdc77d9fe98517df2799dc83ef207e622de3053f6`). Chrome sandbox stays enabled; the container is not privileged. This is an explicitly approved isolated-test configuration, not a production Compose/daemon policy change. Do not apply it to production without a separate security review and authorization.

`/ready` checks prerequisites only; it does not prove Chromium can launch or that PyAutoGUI coordinates work. Default Docker seccomp can still block Chromium startup. A failed image build or skipped integration test is not a verified browser deployment.
