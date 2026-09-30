# Browser Task API

এই repository-র পুরোনো `GCW.py` / `ps_lib/` worker অপরিবর্তিত রেখে নতুন FastAPI + Deep Agents + Selenium Standalone Chrome task API যোগ করা হয়েছে। আর্কিটেকচার ও DFD: [plan/implementation-plan.md](plan/implementation-plan.md), [plan/dfd.md](plan/dfd.md)।

## চালু করা

1. `.env.example` অনুসরণ করে **নিজের** `.env` তৈরি করুন। আপনার বিদ্যমান `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME` রেখে `ALLOWED_HOSTS`-এ অনুমোদিত সাইটগুলোর সঠিক hostname (কমা দিয়ে) লিখুন, যেমন `example.com`। Base URL-র model-কে tool calling সমর্থন করতে হবে। `.env` Git বা Docker image-এ যায় না।
2. `docker compose up --build -d` চালান। App `127.0.0.1:8000`-তে, Selenium শুধু Compose-এর private network-এ। `docker compose ps`-এ দুই service healthy হওয়া পর্যন্ত অপেক্ষা করুন।
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

`TASK_API_TOKEN` ফাঁকা থাকলে উদাহরণের Authorization header বাদ দিতে পারেন, তবে তখন শুধু trusted local environment ব্যবহার করুন। `GET /health` API ও task DB/worker-এর readiness জানায়; Selenium-এর health Compose-এ আলাদা। ভুল UUID-তে 422, অজানা UUID-তে 404, capacity পূর্ণ হলে 429। API-তে কোনো ফল সফলভাবে সেভ হলে app restart-এর পরেও একই ID-তে পাওয়া যায়।

## Browser policy ও সীমা

- `ALLOWED_HOSTS` খালি থাকলে POST গ্রহণ করে না; অনুমোদন ছাড়া কোনো default destination নেই। Hostname exact-match; HTTP(S) ছাড়া অন্য scheme, embedded credentials, localhost/private IP নিষিদ্ধ। Redirect-এর পরে host যাচাই করা হয়; **redirect request আগেই পাঠানো হতে পারে**, তাই allowlist-এ শুধু trusted সাইট দিন এবং browser container-কে network-level access restriction ছাড়া hostile content-এ ব্যবহার করবেন না।
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

Tests fake model/browser ব্যবহার করে, তাই credentials, live site বা network লাগে না। Live smoke test করার আগে একটি অনুমোদিত domain এবং tool-calling endpoint configure করুন; তারপর POST ও GET দিয়ে result যাচাই করুন। Deploy/cleanup-এর আগে [plan/unnecessary-files.md](plan/unnecessary-files.md)-এ তালিকাভুক্ত পুরোনো ফাইল ও বর্তমান tracked deletion যাচাই করুন—এই feature কোনো legacy file মুছে দেয়নি।
