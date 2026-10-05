import json
import os
import stat

import pytest

from app.browser_profiles import BrowserProfileStore, ProfileBusy, ProfileError, validate_profile_id
from app.config import Settings
from app.schemas import TaskRequest
from app.task_context import decode_context, encode_context

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Private profile filesystem tests require Linux")


def test_profiles_are_opaque_independent_private_and_metadata_only(tmp_path):
    store = BrowserProfileStore(tmp_path / "profiles")
    a = store.create('<img src=x onerror="alert(1)">')
    b = store.create("Second")
    assert a["id"] != b["id"]
    assert set(a) == {"id", "label", "created_at", "updated_at"}
    assert store.get(a["id"]) == a
    assert len(store.list()) == 2
    if os.name == "posix":
        assert stat.S_IMODE(store.root.stat().st_mode) == 0o700
        assert stat.S_IMODE((store.root / a["id"] / "metadata.json").stat().st_mode) == 0o600
    with store.lease(a["id"]) as first:
        (first / "synthetic-state").write_text("not a real session")
        with pytest.raises(ProfileBusy):
            with BrowserProfileStore(store.root).lease(a["id"]):
                pass
        with store.lease(b["id"]) as second:
            assert first != second
            assert not (second / "synthetic-state").exists()
    with store.lease(a["id"]) as again:
        assert (again / "synthetic-state").exists()
    assert (store.root / a["id"] / "lease").exists()


@pytest.mark.parametrize("value", ["", "../x", "A" * 32, "0" * 31, "/tmp/a", "0" * 33, None])
def test_invalid_ids_never_resolve_paths(value):
    with pytest.raises(ProfileError):
        validate_profile_id(value)


@pytest.mark.parametrize("label", ["", " ", "x" * 81, "line\nbreak", None])
def test_invalid_labels(tmp_path, label):
    with pytest.raises(ProfileError):
        BrowserProfileStore(tmp_path / "profiles").create(label)


def test_symlink_root_profile_metadata_and_chrome_are_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "linked"
    root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ProfileError):
        BrowserProfileStore(root).list()
    store = BrowserProfileStore(tmp_path / "real")
    profile = store.create("A")
    path = store.root / profile["id"]
    chrome = path / "chrome"
    chrome.rmdir()
    chrome.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ProfileError):
        with store.lease(profile["id"]):
            pass
    metadata = path / "metadata.json"
    metadata.unlink()
    metadata.symlink_to(tmp_path / "arbitrary")
    with pytest.raises(ProfileError):
        store.get(profile["id"])


def test_duplicate_id_is_rejected_without_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr("app.browser_profiles.secrets.token_hex", lambda _: "1" * 32)
    store = BrowserProfileStore(tmp_path / "profiles")
    first = store.create("Original")
    with pytest.raises(ProfileError, match="already exists"):
        store.create("Replacement")
    assert store.get(first["id"])["label"] == "Original"


def test_profile_only_request_round_trip_and_ephemeral_compatibility():
    settings = Settings(_env_file=None)
    request = TaskRequest(prompt="Read a heading", browser_profile_id="a" * 32)
    options, blob = encode_context(request, settings)
    assert blob is None and json.loads(options)["browser_profile_id"] == "a" * 32
    context = decode_context(options, blob, settings)
    assert context.browser_profile_id == "a" * 32
    assert not context.credentials
    assert encode_context(TaskRequest(prompt="Read a heading"), settings) == (None, None)


def test_corrupt_metadata_does_not_expose_arbitrary_fields(tmp_path):
    store = BrowserProfileStore(tmp_path / "profiles")
    profile = store.create("A")
    (store.root / profile["id"] / "metadata.json").write_text('{"path":"/private"}')
    with pytest.raises(ProfileError):
        store.list()
