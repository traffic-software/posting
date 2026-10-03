from contextlib import contextmanager
from types import SimpleNamespace

from app import agent


def mock_local_browser(monkeypatch, factory):
    @contextmanager
    def local(settings, context, deadline):
        driver = factory()
        context.bind_browser(driver.quit)
        try:
            yield SimpleNamespace(driver=driver, desktop=None, network_idle=FakeIdleTracker())
        finally:
            try:
                context.close_browser()
            except Exception:
                pass

    monkeypatch.setattr(agent, "local_browser", local)


class FakeIdleTracker:
    """Explicit deterministic readiness fixture, never a production fallback."""
    def __init__(self, action=None):
        self.action = action
        self.calls = 0

    def wait(self, deadline, guard, cancelled=None):
        self.calls += 1
        guard()
        if self.action:
            self.action()
        guard()
