# বিদ্যমান প্রজেক্টে Deep Agents + Selenium টাস্ক API: বাস্তবায়ন পরিকল্পনা

> এই পরিকল্পনা অনুযায়ী নতুন `app/`, `Dockerfile`, `compose.yaml` ও tests যুক্ত করা হয়েছে; পুরোনো worker/deleted ফাইলগুলো স্পর্শ করা হয়নি। বাস্তব model+browser integration চালিয়ে দেখা এবং container build যাচাই এখনও বাকি। [DFD (Level 0–2)](dfd.md) এবং [অপ্রয়োজনীয় ফাইলের যাচাই-তালিকা](unnecessary-files.md) দেখুন।

## ১. বর্তমান অবস্থা ও সীমারেখা

- প্রজেক্টে Selenium-ভিত্তিক পুরোনো worker আছে: `GCW.py`, `ps_lib/GCW.py`, `ps_lib/browser.py`, `ps_lib/uc.py`। এগুলো নির্দিষ্ট account/post workflow, স্থানীয় ChromeDriver, proxy ও বিদ্যমান SQLite-নির্ভর; সাধারণ উদ্দেশ্যের browser tool নয়। `GCW.py` import-এর পরে dependency install এবং top-level অসীম worker loop চালায়; নতুন API থেকে import করা যাবে না।
- `Dockerfile`-এ বর্তমান browser-সহ base image এবং পুরোনো dependency setup আছে; API চালানোর command, Compose, নির্দিষ্ট dependency manifest, task-status API ও task-result store নেই। পুরোনো browser helper-এ স্থানীয় `webdriver.Chrome(...)` আছে; Docker-এর দ্বিতীয় Selenium container-এ সংযোগ করতে আলাদা `webdriver.Remote` adapter প্রয়োজন।
- `ps_lib/ps_setup.py` পুরোনো domain-এর database (`ps_lib/databases.db`) নিজে তৈরি করে এবং network verification করে। Task tracking-এর জন্য এই DB/constructor পুনর্ব্যবহার না করে আলাদা task DB ব্যবহার করা নিরাপদ।
- স্থানীয় `.env`-এ `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME` নাম উপস্থিত; কোনো মান পরিকল্পনায় লেখা হয়নি। মডেল endpoint সত্যিই tool calling সমর্থন করে কিনা প্রথম integration smoke test-এ যাচাই করতে হবে।
- **কাজ শুরুর আগে Git যাচাই:** এই পরিকল্পনা তৈরির সময় tracked `g2.spec` ও `py/`-এর ২৪টি ফাইল working tree-তে deleted দেখাচ্ছে, অথচ প্রাথমিক status snapshot clean ছিল। এগুলো কে/কেন সরিয়েছেন তা নিশ্চিত না করে restore, stage বা cleanup করা যাবে না। `.env` ও `.claude/` untracked; `.env` বর্তমানে `.gitignore`-এ নেই—পরবর্তী বাস্তবায়নে secrets নিরাপত্তার জন্য এটি ঠিক করতে হবে।

## ২. প্রস্তাবিত কাঠামো

```text
Client ──POST /run-task──> FastAPI app ──INSERT PENDING──> SQLite tasks DB (mounted volume)
                    │             └── enqueue in-process bounded worker (single app process)
                    │                        └── Deep Agent + task-scoped Selenium tools
                    │                                      └── webdriver.Remote ──> Selenium Standalone Chrome
Client ──GET /task-status/{task_id}──> FastAPI app ──SELECT──> SQLite tasks DB
```

**প্রাথমিক ডিফল্ট:** FastAPI + SQLite + একটি in-process worker ও DB-তে সীমিত PENDING backlog, Compose-এ `app` ও `selenium`—মোট দুই container। FastAPI `BackgroundTasks`-কে durable queue হিসেবে ধরা হবে না: restart-এর পরে running কাজ পুনরুদ্ধার করতে startup reconciliation এবং DB-তে PENDING claim logic লাগবে। ছোট single-instance deployment-এ এটি যথেষ্ট; একাধিক app replica বা নিশ্চিত at-least-once dispatch প্রয়োজন হলে পরবর্তী ধাপে PostgreSQL + আলাদা queue/worker (তখন দুই-container সীমা বদলাবে)। Celery এখনই নয়।

**নতুন ফাইলের প্রস্তাব** (নাম বাস্তবায়নে সামঞ্জস্য করা যাবে): `app/main.py` (API/lifespan), `app/schemas.py` (request/response), `app/storage.py` (SQLite), `app/worker.py` (queue/runner), `app/agent.py` (Deep Agent), `app/selenium_tools.py` (tool factory), `app/config.py` (env), `requirements.txt`, `compose.yaml`, `tests/`। বর্তমান `ps_lib/` অক্ষত থাকবে; ভবিষ্যতে নির্দিষ্ট অংশ reuse করতে চাইলে বিচ্ছিন্ন করে tests-সহ migration।

## ৩. ধাপে ধাপে বাস্তবায়ন

### ধাপ ০ — নিরাপত্তা ও বর্তমান repo baseline

1. ২৫টি tracked deletion-এর কারণ নিশ্চিত করুন; এই পরিবর্তনগুলো পরিকল্পনার অংশ নয়। পুরোনো worker চালানোর প্রয়োজন আছে কি না নির্ধারণ করুন; cleanup-এর আগে এর ওপর নির্ভরশীলতা পরীক্ষা করুন।
2. `.env`, DB, browser profile, screenshots/logs এবং `.claude/` build context ও Git-এর বাইরে রাখুন; `.env.example`-এ কেবল variable-এর নাম/placeholder দিন। বিদ্যমান source-এ hard-coded credential আছে—উন্মুক্ত credential হলে rotate/replace ও history audit আলাদা অনুমোদিত কাজ; কোনো গোপন মান task result/log-এ যাবে না।
3. LLM endpoint, browser target sites এবং externally visible actions-এর অনুমোদিত scope ঠিক করুন। Default tool set-এ CAPTCHA bypass, anti-detection, arbitrary shell/remote code execution বা legacy account worker expose করবেন না।

### ধাপ ১ — Docker ও dependency setup

1. নির্দিষ্ট Python version-ভিত্তিক app Dockerfile তৈরি/বর্তমানটি প্রতিস্থাপন, pinned/tested `fastapi`, `uvicorn`, `deepagents`, `langchain-openai`, `selenium`, `pydantic-settings` ও test dependency manifest; build-এ `.env` কপি নয়। পুরোনো Dockerfile-এর hard-coded credentials ও browser-in-app setup বহন নয়।
2. Compose: `app` (API), `selenium` (`selenium/standalone-chrome`-এর tested pinned tag); `SE_REMOTE_URL=http://selenium:4444/wd/hub` (Selenium 4-এর `/` endpoint-ও যাচাই করা যাবে), Chrome headless, healthcheck/wait/retry, `shm_size`, app-এর `/data`-তে named volume। Selenium port বাইরে publish নয়; API কেবল প্রয়োজনীয় interface-এ expose। Compose `env_file` বা runtime secrets দিয়ে env inject হবে; image-এর ভিতর যাবে না।
3. Docker ছাড়া unit test চালানোর পথ রাখুন; live integration test শুধু Compose-এ।

### ধাপ ২ — task DB ও lifecycle

1. আলাদা SQLite file `/data/tasks.db`; `tasks` schema: `task_id TEXT PRIMARY KEY` (UUID), `prompt TEXT` (সংবেদনশীল হলে retention/redaction নীতি), `status TEXT CHECK(status IN ('PENDING','PROCESSING','COMPLETED','FAILED'))`, `result_json TEXT`, `error TEXT`, `created_at TEXT`, `updated_at TEXT` (UTC), ঐচ্ছিক `started_at`, `finished_at`; schema init/migration, index এবং JSON size limit। Task প্রতি DB connection, short transaction, WAL/busy timeout ও parameterized SQL।
2. `POST`-এ atomic INSERT PENDING এবং সঙ্গে সঙ্গে ID ফেরত; worker atomic claim করে PROCESSING; সাফল্যে COMPLETED + serializable result; ব্যর্থতায় FAILED + sanitized error; `finally`-তে driver.quit। ৪০৪ unknown ID, ২০০ existing ID। Repeated read-এ একই result থাকবে।
3. Restart policy স্পষ্ট করুন: single-instance worker startup-এ stranded PROCESSING-কে FAILED (interrupted) করে, PENDING-গুলো পুনরায় schedule করবে; side-effecting কাজ automatic retry নয়, যাতে duplicate submission না ঘটে। Graceful shutdown এবং bounded concurrency (শুরুতে ১) থাকবে।

### ধাপ ৩ — Selenium tool ও Deep Agent

1. প্রতি task-এর জন্য আলাদা `webdriver.Remote(command_executor=SE_REMOTE_URL, options=ChromeOptions())` session; implicit shared driver/global state নয়; page-load/script timeout, explicit waits, max task duration, bounded tool output ও screenshots-এর পৃথক retention নীতি।
2. Task-scoped typed tools: `navigate_to_page(url)` (শুধু অনুমোদিত http(s) destinations), `click_element(locator)`, `fill_element(locator, value)`, `extract_text(locator)`; CSS selector দিয়ে শুরু, প্রয়োজন হলে সীমিত locator ধরন। Tool ফলাফল structured JSON/text; invalid selector/timeout-এর নিয়ন্ত্রিত error; session `finally`-তে বন্ধ। Tool-level URL policy redirect-এর পরেও প্রয়োগ ও private/internal destinations block।
3. `deepagents.create_deep_agent(model=<configured model instance>, tools=[...], system_prompt=...)` দিয়ে agent তৈরি। `langchain_openai.ChatOpenAI`-এর `api_key`, `base_url`, `model=MODEL_NAME` runtime env থেকে; provider endpoint-এর tool-calling compatibility আগে smoke test। `agent.invoke({"messages": [{"role": "user", "content": prompt}]})` থেকে কেবল final content/সংক্ষিপ্ত structured output persist; সীমাহীন internal traces বা credentials নয়। Agent-এর tool-call ও overall step/time budget; browser-এ irreversible form submit-এর আগে অনুমোদন নীতি অথবা প্রথম release-এ read-only/demo form scope। Built-in arbitrary filesystem/shell tools agent-কে অযথা দেওয়া হবে না।

### ধাপ ৪ — API ও worker

1. `POST /run-task` body `{ "prompt": "..." }` (nonempty, max length); `202 Accepted` body `{ "task_id": "...", "status": "PENDING" }`। Request DB-তে commit হওয়ার পরে enqueue; DB write ব্যর্থ হলে 5xx, ভুয়া ID নয়।
2. `GET /task-status/{task_id}` -> `{ "task_id", "status", "result", "error", "created_at", "updated_at" }`; pending/processing-এ result null, complete-এ result, failed-এ sanitized error; UUID validation ও unknown ID-তে 404। `GET /health` readiness-এ DB/worker পরীক্ষা (browser readiness আলাদা)।
3. Lifespan-এ single worker শুরু/বন্ধ; in-memory event শুধু wake-up দেয়, SQLite-এর সীমিত active task set থেকেই worker claim করে; API process count ১; capacity পেরোলে 429, overload-এ silent loss নয়। Public deployment হলে API authentication, rate limit এবং per-user task ownership যুক্ত করা আবশ্যক; bind/access policy ছাড়া arbitrary prompts গ্রহণ করা যাবে না।

### ধাপ ৫ — যাচাই ও ডকুমেন্টেশন

1. Unit tests: schema/transition, atomic claim, 404/validation, failure persist, redaction, restart reconciliation, fake WebDriver-এ tool timeout/cleanup ও URL policy। LLM এবং Selenium mocked হলে tests নির্ভরযোগ্য থাকবে।
2. Compose smoke test: `docker compose up --build`, healthchecks green, test-controlled demo HTML page-এ navigation/extraction বা demo form, POST-এ তাৎক্ষণিক UUID/202, polling-এ PENDING → PROCESSING → COMPLETED, correct saved result; forced failure → FAILED। App restart করেও task ID দিয়ে result পাওয়া যাচ্ছে কি না পরীক্ষা। Selenium container/LLM endpoint অনুপলব্ধ হলে FAILED/error পাওয়া উচিত, hang নয়।
3. README-তে `.env.example`, `docker compose up --build`, sample curl POST/GET, volume/backup, task timeout, cleanup/retention এবং allowed destinations-এর configuration লিখুন। পরিষ্কার acceptance criterion: একই ID-এর result restart-এর পরেও পাওয়া যায়, browser task isolation আছে, app+browser আলাদা container, secrets image/log/response-এ নেই।

## সিদ্ধান্ত/ঝুঁকি (বাস্তবায়নের আগে নিশ্চিত করা দরকার)

- কোন URL/domain-এ agent কাজ করবে এবং write/submit action অনুমোদিত কি না; fallback হলো স্থানীয় demo/read-only workflow।
- বর্তমান `py/` ও `g2.spec` deletions ইচ্ছাকৃত কি না; cleanup অনুমোদন ছাড়া নয়।
- একাধিক app instance/production queue দরকার হলে architecture-কে PostgreSQL + worker/queue-তে উন্নীত করতে হবে; এই দুই-container MVP যথেষ্ট নয়।
- `OPENAI_BASE_URL`-এর সার্ভিস এবং `MODEL_NAME` টুল কল সমর্থন না করলে Deep Agent কাজ করবে না; early smoke test-এ fail-fast।

ডকুমেন্টেশন রেফারেন্স: https://docs.langchain.com/oss/python/deepagents/overview ও https://docs.langchain.com/oss/python/deepagents/quickstart ।
