import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

import veilus
from veilus import Veilus, VeilusError


class FakeApi:
    """A fake Veilus REST API: records requests, answers with ``handler``."""

    def __init__(self, tmp_path: Path, handler):
        self.requests = []
        api = self

        class Handler(BaseHTTPRequestHandler):
            def _serve(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(n).decode()
                api.requests.append(
                    (self.command, self.path, self.headers.get("Authorization"), body)
                )
                status, reply = handler(self.path)
                self.send_response(status)
                self.end_headers()
                if reply is not None:
                    self.wfile.write(json.dumps(reply).encode())

            do_GET = do_POST = _serve

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.app_dir = tmp_path
        (tmp_path / "api-endpoint.json").write_text(
            json.dumps({"rest_port": self.server.server_port}), encoding="utf-8"
        )

    def close(self):
        self.server.shutdown()


def test_finds_port_in_endpoint_file_and_sends_bearer(tmp_path):
    api = FakeApi(
        tmp_path, lambda p: (200, [{"id": "p1", "cdpUrl": "http://127.0.0.1:9"}])
    )
    v = Veilus(token="t0k", app_dir=api.app_dir)
    profiles = asyncio.run(v.list_profiles())
    assert profiles[0]["cdpUrl"] == "http://127.0.0.1:9"
    assert [(r[0], r[1], r[2]) for r in api.requests] == [
        ("GET", "/v1/profiles", "Bearer t0k")
    ]
    api.close()


def test_launch_sends_diagnostic_only_when_asked_and_stop_posts(tmp_path):
    api = FakeApi(
        tmp_path,
        lambda p: (
            (204, None)
            if p.endswith("/stop")
            else (200, {"pid": 7, "cdpUrl": "http://x"})
        ),
    )
    v = Veilus(token="t", app_dir=api.app_dir)

    async def run():
        await v.launch("p1")
        await v.launch("p1", diagnostic=True)
        await v.stop("p1")

    asyncio.run(run())
    assert [(r[1], r[3]) for r in api.requests] == [
        ("/v1/profiles/p1/launch", "{}"),
        ("/v1/profiles/p1/launch", '{"diagnostic": true}'),
        ("/v1/profiles/p1/stop", "{}"),
    ]
    api.close()


def test_launch_sends_headless_only_when_asked(tmp_path):
    api = FakeApi(tmp_path, lambda p: (200, {"pid": 7, "cdpUrl": "http://x"}))
    v = Veilus(token="t", app_dir=api.app_dir)

    async def run():
        await v.launch("p1", headless=True)
        await v.launch("p1", diagnostic=True, headless=True)
        await v.launch("p1", headless=False)

    asyncio.run(run())
    assert [r[3] for r in api.requests] == [
        '{"headless": true}',
        '{"diagnostic": true, "headless": true}',
        "{}",
    ]
    api.close()


def test_launch_reply_without_cdp_url_names_minimum_version(tmp_path):
    api = FakeApi(tmp_path, lambda p: (200, {"pid": 7}))
    v = Veilus(token="t", app_dir=api.app_dir)
    with pytest.raises(VeilusError, match=r"Veilus 0\.2\.9 or newer"):
        asyncio.run(v.launch("p1"))
    api.close()


def test_rejected_token_says_what_to_do(tmp_path):
    api = FakeApi(tmp_path, lambda p: (401, {"error": "unauthorized"}))
    v = Veilus(token="old", app_dir=api.app_dir)
    with pytest.raises(VeilusError, match="API & MCP") as e:
        asyncio.run(v.list_profiles())
    assert e.value.status == 401
    api.close()


def test_no_endpoint_file_says_turn_on_local_api(tmp_path):
    v = Veilus(token="t", app_dir=tmp_path)
    with pytest.raises(VeilusError, match="turn on the local API"):
        asyncio.run(v.list_profiles())


def test_never_falls_back_to_the_token_store(tmp_path, monkeypatch):
    """Decision 0124 / 0016: with the app's token store right there and no
    token given, the SDK still refuses — and does not point at the store."""
    (tmp_path / "api-tokens.json").write_text('[{"token": "secret"}]', encoding="utf-8")
    monkeypatch.delenv("VEILUS_API_TOKEN", raising=False)
    with pytest.raises(VeilusError) as e:
        Veilus(app_dir=tmp_path)
    assert "VEILUS_API_TOKEN" in str(e.value)
    assert "api-tokens" not in str(e.value)
    source = Path(veilus.__file__).read_text(encoding="utf-8")
    assert "api-tokens" not in source, "the SDK source names the token store"
