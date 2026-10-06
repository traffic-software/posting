"""Opt-in synthetic HTTPS uploads and native/Blob downloads; no external accounts."""
import base64
import datetime
import ipaddress
import os
import ssl
import threading
import time
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from app.artifacts import ArtifactManager
from app.browser_runtime import local_browser
from app.config import Settings
from app.selenium_tools import browser_tools
from app.storage import TaskStore
from app.task_context import TaskContext

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LOCAL_BROWSER_INTEGRATION") != "1",
                                reason="Requires opt-in configured Linux Chrome/Xvfb")


def tls_server(tmp_path, handler):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "local-fixture")])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
                   .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(minutes=1))
                   .not_valid_after(now + datetime.timedelta(days=1))
                   .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
                   .sign(key, hashes.SHA256()))
    cert_path, key_path = tmp_path / "fixture.pem", tmp_path / "fixture-key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    spki = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    digest = hashes.Hash(hashes.SHA256())
    digest.update(spki)
    return server, thread, base64.b64encode(digest.finalize()).decode("ascii")


def test_hidden_upload_authenticated_native_and_blob_downloads(tmp_path, monkeypatch):
    import json
    from urllib.parse import urlsplit
    from app import selenium_tools

    upload_bytes, download_bytes = b"authorized-upload\x00", b"authenticated-download\x00"
    received_uploads, download_cookies = [], []
    html = b"""<html><body>
<input type="file" id="file" style="display:none" onchange="const f=new FormData();f.append('file',this.files[0]);fetch('/upload',{method:'POST',body:f}).then(r=>r.text()).then(t=>document.getElementById('status').textContent=t)">
<p id="status"></p><a id="protected" href="/protected-download" download>Download protected file</a>
<button id="blob" onclick="const a=document.createElement('a');a.href=window.URL.createObjectURL(new window.Blob(['blob bytes'],{type:'application/octet-stream'}));a.download='blob-result.bin';a.click()">Download Blob</button>
</body></html>"""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/protected-download":
                cookie = self.headers.get("Cookie", "")
                download_cookies.append(cookie)
                if "fixture_session=allowed" not in cookie:
                    self.send_error(403)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", 'attachment; filename="protected-video.mp4"')
                self.send_header("Content-Length", str(len(download_bytes)))
                self.end_headers()
                self.wfile.write(download_bytes)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Set-Cookie", "fixture_session=allowed; Secure; HttpOnly; Path=/; SameSite=Strict")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            message = BytesParser(policy=default).parsebytes(("Content-Type: " + self.headers["Content-Type"] + "\r\n\r\n").encode() + body)
            part = next(message.iter_parts())
            received_uploads.append((part.get_filename(), part.get_payload(decode=True)))
            result = b"Upload received"
            self.send_response(200)
            self.send_header("Content-Length", str(len(result)))
            self.end_headers()
            self.wfile.write(result)

        def log_message(self, *_args):
            pass

    server, thread, fixture_spki = tls_server(tmp_path, Handler)

    # Browser-owned native downloads do not inherit page-scoped CDP Security
    # overrides. Trust only this ephemeral fixture key at browser startup.
    import seleniumbase
    driver_factory = seleniumbase.Driver

    def fixture_driver(**kwargs):
        kwargs["chromium_arg"] += ",ignore-certificate-errors-spki-list=" + fixture_spki
        return driver_factory(**kwargs)

    monkeypatch.setattr(seleniumbase, "Driver", fixture_driver)
    origin = f"https://127.0.0.1:{server.server_port}"
    check = selenium_tools.check_url

    def fixture_url(value):
        parsed = urlsplit(value)
        if parsed.scheme == "https" and parsed.netloc == f"127.0.0.1:{server.server_port}":
            return
        check(value)

    monkeypatch.setattr(selenium_tools, "check_url", fixture_url)
    settings = Settings(_env_file=None, enable_file_transfers=True, enable_write_actions=True,
                        artifact_root=tmp_path / "files", artifact_public_base_url="https://files.example",
                        artifact_link_signing_key="k" * 32, task_api_token="fixture-token",
                        artifact_max_file_bytes=65536, artifact_max_task_bytes=1024 * 1024)
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    manager = ArtifactManager(settings, store)
    manager.initialize()
    task_id = store.create("Upload and download authorized fixtures", 1)
    store.claim_next()
    ctx = TaskContext(task_id=task_id, allow_write_actions=True, allow_file_downloads=True, upload_origins=[origin])
    ctx._artifact_session = manager.task_session(task_id, ctx.check_alive)
    writer = ctx._artifact_session.reserve(purpose="input", name="reference.bin")
    writer.write(upload_bytes)
    input_file = writer.finish()["id"]
    try:
        with local_browser(settings, ctx, time.monotonic() + 90) as session:
            assert ctx._browser_downloads is not None and ctx._browser_downloads.available
            events = []
            ctx._browser_downloads._connection.add_callback(ctx._browser_downloads._devtools.browser.DownloadProgress,
                lambda event: events.append((event.state, event.received_bytes, event.total_bytes)))
            session.driver.get(origin + "/")
            observed = session.driver.execute_script("return {origin:location.origin,top:window===window.top};")
            assert observed == {"origin": origin, "top": True}, (observed, session.driver.current_url, session.driver.title)
            bound = {item.name: item for item in browser_tools(session.driver, settings, time.monotonic() + 70, ctx, session.desktop)}
            control = json.loads(bound["inspect_file_inputs"].invoke({}))["controls"][0]
            assert "assigned once" in bound["upload_file"].invoke({"input_id": control["input_id"], "file_ids": [input_file]})
            WebDriverWait(session.driver, 10).until(lambda d: d.find_element(By.ID, "status").text == "Upload received")
            assert received_uploads == [("reference.bin", upload_bytes)]
            for identifier in ("protected", "blob"):
                page = json.loads(bound["inspect_page"].invoke({}))
                element = session.driver.find_element(By.ID, identifier)
                # Use the actual structural selector discovered by inspection.
                selector = next(row["selector"] for row in session.driver.execute_script(selenium_tools.DISCOVER_PAGE) if row["element"] == element)
                assert any(control["selector"] == selector for control in page["controls"])
                started = json.loads(bound["download_from_element"].invoke({"selector": selector}))
                result = started
                end = time.monotonic() + 15
                while result["status"] == "pending" and time.monotonic() < end:
                    result = json.loads(bound["wait_for_download"].invoke({"download_id": started["download_id"]}))
                assert result["status"] == "ready", (identifier, result, events, download_cookies)
                path, _ = ctx._artifact_session.resolve(result["artifact"]["id"])
                assert path.read_bytes() == (download_bytes if identifier == "protected" else b"blob bytes")
            assert download_cookies and "fixture_session=allowed" in download_cookies[0]
            assert "fixture_session" not in str(ctx.observations())
        links = manager.links(task_id)
        assert {item["name"] for item in links} == {"protected-video.mp4", "blob-result.bin"}
        assert all(manager._path(item["id"]).exists() for item in links)
    finally:
        ctx.clear_sensitive_state()
        manager.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
