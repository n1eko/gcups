import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from gcups_exporter.client import GcupsApiError, GcupsClient

PASSWORD = "Test12345"


class FakeGcupsApi(BaseHTTPRequestHandler):
    """Issues numbered tokens; only the latest token is accepted."""
    logins = 0

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path != "/api/login" or body.get("password") != PASSWORD:
            return self._reply(403, {})
        type(self).logins += 1
        self._reply(201, {"access_token": f"token-{self.logins}"})

    def do_GET(self):
        if self.headers.get("Authorization") != f"Bearer token-{self.logins}":
            return self._reply(401, {})
        if self.path == "/api/empty":
            return self._reply(200, None)
        self._reply(200, {"path": self.path})

    def _reply(self, status, payload):
        body = json.dumps(payload).encode() if payload is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def api_url():
    FakeGcupsApi.logins = 0
    server = HTTPServer(("127.0.0.1", 0), FakeGcupsApi)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_logs_in_once_and_reuses_token(api_url):
    client = GcupsClient(api_url, PASSWORD, timeout_seconds=2)

    assert client.get("/status") == {"path": "/api/status"}
    assert client.get("/data") == {"path": "/api/data"}
    assert FakeGcupsApi.logins == 1


def test_logs_in_again_when_token_is_rejected(api_url):
    client = GcupsClient(api_url, PASSWORD, timeout_seconds=2)
    client.get("/status")
    FakeGcupsApi.logins += 1  # server-side rotation invalidates the current token

    assert client.get("/status") == {"path": "/api/status"}
    assert FakeGcupsApi.logins == 3


def test_wrong_password_raises_api_error(api_url):
    client = GcupsClient(api_url, "wrong", timeout_seconds=2)

    with pytest.raises(GcupsApiError, match="403"):
        client.get("/status")


def test_unreachable_api_raises_api_error():
    client = GcupsClient("http://127.0.0.1:1", PASSWORD, timeout_seconds=2)

    with pytest.raises(GcupsApiError):
        client.get("/status")


def test_empty_body_is_returned_as_none(api_url):
    client = GcupsClient(api_url, PASSWORD, timeout_seconds=2)

    assert client.get("/empty") is None
