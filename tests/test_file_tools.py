import json
import socket
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.artifacts import ArtifactManager
from app.browser_dom import DISCOVER_PAGE
from app.config import Settings
from app.element_readiness import READINESS
from app.file_tools import _DOWNLOAD_TARGET, _FILE_INPUTS, _FILE_INPUT_STATE
from app.schemas import UploadSource
from app.selenium_tools import BrowserPolicyStop, browser_tools
from app.storage import TaskStore
from app.task_context import TaskContext


ORIGIN = "https://upload.example"
SOURCE = "https://source.example/video.mp4?signature=source-private-value"


class FileInput:
    tag_name = "input"
    text = ""
    selected = 0
    enabled = True
    multiple = False

    def __init__(self):
        self.assignments = []

    def get_attribute(self, name):
        assert name != "value"
        return "file" if name == "type" else None

    def is_displayed(self):
        return False  # Hidden file inputs are deliberately supported only by the dedicated tool.

    def is_enabled(self):
        return self.enabled

    def send_keys(self, paths):
        self.assignments.append(paths)
        self.selected = len(paths.split("\n"))


class Link:
    tag_name = "a"
    text = "Download"

    def get_attribute(self, name):
        return "https://cdn.example/installer.exe" if name == "href" else None

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def click(self):
        pass


class Driver:
    current_url = ORIGIN + "/workspace"
    top = True

    def __init__(self):
        self.input = FileInput()
        self.link = Link()
        self.body = SimpleNamespace(text="Authorized fixture files")

    def find_element(self, by, selector):
        return self.body if selector == "body" else self.input if selector == "input:nth-child(1)" else self.link

    def execute_script(self, code, *args):
        if code == READINESS:
            return "ready"
        if code == _FILE_INPUTS:
            return [{"element": self.input, "selector": "input:nth-child(1)"}]
        if code == _FILE_INPUT_STATE:
            element = args[0]
            return {"top": self.top, "origin": self.current_url.split("/workspace")[0], "connected": True,
                    "file": element is self.input, "enabled": element.enabled, "multiple": element.multiple,
                    "selected": element.selected, "accept": ".mp4,.exe"}
        if code == _DOWNLOAD_TARGET:
            return True
        if code == DISCOVER_PAGE:
            return [{"element": self.link, "selector": "a:nth-child(2)"}]
        return {"origin": self.current_url.split("/workspace")[0], "top": self.top}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("8.8.8.8", 443))])
    settings = Settings(_env_file=None, enable_file_transfers=True, enable_write_actions=True,
                        artifact_root=tmp_path / "files", artifact_public_base_url="https://files.example",
                        artifact_link_signing_key="k" * 32, task_api_token="fixture-token")
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    manager = ArtifactManager(settings, store)
    manager.initialize()
    task = store.create("Transfer fixtures", 5)
    store.claim_next()
    ctx = TaskContext(task_id=task, allow_write_actions=True, allow_file_downloads=True,
                      upload_sources=[UploadSource(id="reference", url=SOURCE, filename="reference.mp4")], upload_origins=[ORIGIN])
    ctx._artifact_session = manager.task_session(task, ctx.check_alive)
    driver = Driver()
    calls = []

    def fetch(url, write, guard, deadline, **kwargs):
        calls.append(url)
        guard()
        write(b"verified bytes")
        return {"name": "installer.exe", "media_type": "application/octet-stream", "size_bytes": 14}

    monkeypatch.setattr("app.file_tools.fetch_file", fetch)
    yield driver, settings, ctx, manager, store, calls
    ctx.clear_sensitive_state()
    manager.close()


def tools(setup):
    driver, settings, ctx, *_ = setup
    return {item.name: item for item in browser_tools(driver, settings, time.monotonic() + 60, ctx)}


def fetched(bound):
    return json.loads(bound["fetch_upload_source"].invoke({"source_id": "reference"}))["id"]


def input_id(bound):
    return json.loads(bound["inspect_file_inputs"].invoke({}))["controls"][0]["input_id"]


def test_url_source_is_cached_and_no_secret_or_path_reaches_model(setup):
    bound = tools(setup)
    first = fetched(bound)
    assert fetched(bound) == first
    assert setup[-1] == [SOURCE]
    result = bound["list_upload_sources"].invoke({}) + bound["list_task_files"].invoke({}) + str(setup[2].observations())
    assert SOURCE not in result and "source-private-value" not in result
    assert str(setup[3].root) not in result
    assert setup[3].links(setup[2].task_id) == []


def test_aws_source_security_token_is_redacted_decoded_and_encoded():
    from urllib.parse import quote, quote_plus

    token = "AWS/session+secret=with space"
    encoded = quote(token, safe="")
    raw = encoded.replace("%2F", "%2f")
    context = TaskContext(upload_sources=[UploadSource(
        id="aws", url="https://source.example/file?X-Amz-Security-Token=" + raw,
    )])
    for value in (token, raw, encoded, quote_plus(token, safe="")):
        assert context.redact("Source token: " + value) == "Source token: [REDACTED]"
        assert context.redacted_result({"output": value}) == {"output": "[REDACTED]"}
    context.record_observation("fetch_upload_source", "ok", token + " " + raw)
    assert token not in str(context.observations())
    assert raw not in str(context.observations())


def test_hidden_file_assignment_preserves_filename_without_exposing_path(setup):
    bound = tools(setup)
    artifact = fetched(bound)
    token = input_id(bound)
    result = bound["upload_file"].invoke({"input_id": token, "file_ids": [artifact]})
    assert "assigned once" in result
    assert Path(setup[0].input.assignments[0]).name == "reference.mp4"
    assert Path(setup[0].input.assignments[0]).read_bytes() == b"verified bytes"
    assert str(setup[3].root) not in result + str(setup[2].observations())
    assert "stale or consumed" in bound["upload_file"].invoke({"input_id": token, "file_ids": [artifact]})
    token = input_id(bound)
    assert "already contains" in bound["upload_file"].invoke({"input_id": token, "file_ids": [artifact]})
    assert len(setup[0].input.assignments) == 1


@pytest.mark.parametrize("change", ["origin", "frame", "disabled", "replaced", "handoff"])
def test_upload_revalidates_origin_frame_input_and_manual_epoch(setup, change):
    bound = tools(setup)
    artifact, token = fetched(bound), input_id(bound)
    original = setup[0].input
    if change == "origin":
        setup[0].current_url = "https://other.example/workspace"
    elif change == "frame":
        setup[0].top = False
    elif change == "disabled":
        original.enabled = False
    elif change == "replaced":
        setup[0].input = FileInput()
    else:
        setup[2].control.epoch += 1
    if change in {"origin", "frame"}:
        with pytest.raises(BrowserPolicyStop):
            bound["upload_file"].invoke({"input_id": token, "file_ids": [artifact]})
    else:
        assert "input" in bound["upload_file"].invoke({"input_id": token, "file_ids": [artifact]}).lower()
    assert not original.assignments and not setup[0].input.assignments


def test_other_task_files_and_server_paths_cannot_be_uploaded(setup):
    bound = tools(setup)
    _, _, _, manager, store, _ = setup
    task = store.create("another task", 5)
    store.claim_next()
    other = manager.task_session(task, lambda: None)
    writer = other.reserve(purpose="input")
    writer.write(b"other bytes")
    artifact = writer.finish()["id"]
    for identifier in (artifact, "/etc/passwd"):
        result = bound["upload_file"].invoke({"input_id": input_id(bound), "file_ids": [identifier]})
        assert "unavailable to this task" in result
    assert not setup[0].input.assignments


def test_public_output_gets_a_real_link_but_does_not_process_software(setup):
    bound = tools(setup)
    result = json.loads(bound["download_file"].invoke({"url": "https://cdn.example/installer.exe"}))
    links = setup[3].links(setup[2].task_id)
    assert links[0]["id"] == result["id"] and links[0]["name"] == "installer.exe"
    assert "download_url" not in result and "signature=" not in str(setup[2].observations())


def test_permission_gates_do_not_expose_click_upload_bypasses(setup):
    setup[2].allow_write_actions = False
    bound = tools(setup)
    assert "upload_file" not in bound and "download_from_element" not in bound
    assert "prepare_browser_download" not in bound
    assert "download_file" in bound
    setup[2].allow_file_downloads = False
    assert "download_file" not in tools(setup)


def test_prepared_browser_download_agent_click_then_collect(setup):
    driver, _, context, *_ = setup
    clicks = []
    driver.link.click = lambda: clicks.append(True)

    class Collector:
        available = True
        active = False
        def arm(self, origin):
            assert origin == ORIGIN
            if self.active:
                raise RuntimeError('already armed')
            self.active = True
            return 'synthetic-download'
        def wait(self, identifier, timeout):
            assert identifier == 'synthetic-download'
            if not clicks:
                return {'status': 'pending'}
            writer = context._artifact_session.reserve(purpose='output', name='video.mp4', media_type='video/mp4')
            writer.write(b'verified fixture video bytes')
            self.active = False
            return {'status': 'ready', 'artifact': writer.finish()}
        def close(self):
            pass

    context._browser_downloads = Collector()
    bound = tools(setup)
    assert 'Inspect the current page' in bound['prepare_browser_download'].invoke({'selector': 'a:nth-child(2)'})
    bound['inspect_page'].invoke({})
    receipt = json.loads(bound['prepare_browser_download'].invoke({'selector': 'a:nth-child(2)'}))
    assert receipt['status'] == 'armed' and receipt['click_performed'] is False
    assert not clicks
    assert 'Could not arm' in bound['prepare_browser_download'].invoke({'selector': 'a:nth-child(2)'})
    assert not clicks
    pending = json.loads(bound['wait_for_download'].invoke({'download_id': receipt['download_id']}))
    assert pending['status'] == 'pending'
    assert bound['click_element'].invoke({'selector': 'a:nth-child(2)'}) == 'Element clicked'
    ready = json.loads(bound['wait_for_download'].invoke({'download_id': receipt['download_id']}))
    assert ready['status'] == 'ready' and clicks == [True]
    files = json.loads(bound['list_task_files'].invoke({}))['files']
    assert files[0]['id'] == ready['artifact']['id'] and files[0]['purpose'] == 'output'
    assert setup[3].links(context.task_id)[0]['id'] == files[0]['id']
    assert 'https://' not in json.dumps(receipt) and 'download_url' not in ready['artifact']


def test_challenge_stop_applies_to_direct_downloads(setup):
    setup[0].body.text = "CAPTCHA"
    with pytest.raises(BrowserPolicyStop):
        tools(setup)["download_file"].invoke({"url": "https://cdn.example/installer.exe"})
    assert not setup[-1]
