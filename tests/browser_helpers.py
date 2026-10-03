from contextlib import contextmanager
from types import SimpleNamespace

from app import agent


def mock_local_browser(monkeypatch, factory):
    @contextmanager
    def local(settings, context, deadline):
        driver = factory()
        context.bind_browser(driver.quit)
        try:
            yield SimpleNamespace(driver=driver, desktop=None)
        finally:
            try:
                context.close_browser()
            except Exception:
                pass

    monkeypatch.setattr(agent, "local_browser", local)
