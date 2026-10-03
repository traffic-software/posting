"""Local synthetic viewer demo; never imported by the production application."""
import threading
import time
from contextlib import asynccontextmanager
from urllib.parse import quote

import uvicorn

from app.browser_runtime import local_browser
from app.config import Settings
from app.main import create_app
from app.task_context import TaskContext

settings = Settings(
    _env_file=None, database_path="/tmp/viewer-smoke.db", display_viewer_enabled=True,
    display_viewer_token="synthetic-viewer-token", display_viewer_origin="http://127.0.0.1:8003",
)
app = create_app(settings, runner=lambda *_: {})
release = threading.Event()
original_lifespan = app.router.lifespan_context


def show_synthetic_display():
    with local_browser(settings, TaskContext(), time.monotonic() + 300) as session:
        page = '<html><body style="font-family:system-ui;padding:40px;background:#eef5fa"><h1>Synthetic agent display</h1><p>Live browser screen — no real account data.</p><input placeholder="Synthetic input"><button>Demo button</button></body></html>'
        session.driver.get("data:text/html," + quote(page))
        release.wait(240)


@asynccontextmanager
async def lifespan(application):
    async with original_lifespan(application):
        thread = threading.Thread(target=show_synthetic_display, daemon=True)
        thread.start()
        try:
            yield
        finally:
            release.set()
            thread.join(timeout=15)


app.router.lifespan_context = lifespan


@app.post("/smoke/finish")
def finish_synthetic_display():
    release.set()
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
