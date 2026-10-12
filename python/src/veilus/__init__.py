"""Veilus SDK for Python: launch Veilus profiles through the app's local REST
API and drive them with Playwright over the profile's own CDP endpoint.

Discovery follows the same contract as the app's own MCP server:

- the port comes from ``<app dir>/api-endpoint.json``, a file the app writes
  when its local API starts and deletes when it stops (it holds no secret);
- the token comes ONLY from the caller (``token=``) or the ``VEILUS_API_TOKEN``
  environment variable. This package never reads the app's token store: being
  able to run this package must not mean being able to drive every profile on
  the machine.
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

__all__ = ["APP_DIR_ENV", "TOKEN_ENV", "Connected", "Veilus", "VeilusError"]

TOKEN_ENV = "VEILUS_API_TOKEN"
APP_DIR_ENV = "VEILUS_APP_DIR"
ENDPOINT_FILE = "api-endpoint.json"


class VeilusError(Exception):
    """An error whose message says what to do next."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class Connected:
    """Playwright attached to a running profile. ``close()`` only disconnects."""

    browser: Any
    context: Any
    page: Any
    cdp_url: str
    _playwright: Any

    async def close(self) -> None:
        await self.browser.close()
        await self._playwright.stop()


class Veilus:
    def __init__(
        self,
        token: str | None = None,
        port: int | None = None,
        app_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        self.token = token or os.environ.get(TOKEN_ENV)
        if not self.token:
            raise VeilusError(
                f"missing {TOKEN_ENV}. Create a token on the API & MCP page in Veilus "
                "(sidebar) and pass it as token= or put it in the environment."
            )
        self.port = port
        self.app_dir = Path(
            app_dir or os.environ.get(APP_DIR_ENV) or Path.home() / ".veilus"
        )

    def _resolve_port(self) -> int:
        """Given, or read from the endpoint file on every call (it changes when
        the app restarts)."""
        if self.port:
            return self.port
        path = self.app_dir / ENDPOINT_FILE
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as e:
            raise VeilusError(
                f"{path} not found. Open the Veilus app and turn on the local API "
                "(API & MCP page in Veilus, sidebar)."
            ) from e
        port = json.loads(raw).get("rest_port")
        if not isinstance(port, int) or not 0 < port <= 65535:
            raise VeilusError(f"{path}: missing or invalid `rest_port`")
        return port

    def _request_sync(self, method: str, path: str, body: Any = None) -> Any:
        port = self._resolve_port()
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}", data=data, method=method
        )
        req.add_header("Authorization", f"Bearer {self.token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                text = res.read().decode()
        except urllib.error.HTTPError as e:
            hint = (
                " (token rejected: create a new one on the API & MCP page)"
                if e.code == 401
                else ""
            )
            raise VeilusError(
                f"{method} {path} -> {e.code}{hint}: {e.read().decode()}",
                status=e.code,
            ) from e
        except urllib.error.URLError as e:
            raise VeilusError(
                f"cannot reach the Veilus API on 127.0.0.1:{port}. "
                "Is the app running with the local API on?"
            ) from e
        return json.loads(text) if text else None

    async def _request(self, method: str, path: str, body: Any = None) -> Any:
        return await asyncio.to_thread(self._request_sync, method, path, body)

    async def list_profiles(self) -> list[dict[str, Any]]:
        """All profiles. A running one carries ``cdpUrl``."""
        return await self._request("GET", "/v1/profiles")

    async def launch(self, profile_id: str, diagnostic: bool = False) -> dict[str, Any]:
        """Launch a profile and wait for its browser to start.

        ``diagnostic`` (Veilus >= 0.2.10): the profile's proxy without its
        fingerprint, in a temporary directory.
        """
        body = {"diagnostic": True} if diagnostic else {}
        out = await self._request(
            "POST", f"/v1/profiles/{quote(profile_id, safe='')}/launch", body
        )
        if not out or not out.get("cdpUrl"):
            raise VeilusError(
                "the launch reply has no `cdpUrl`: this SDK needs Veilus 0.2.9 or newer."
            )
        return out

    async def stop(self, profile_id: str) -> None:
        """Stop a running profile."""
        await self._request(
            "POST", f"/v1/profiles/{quote(profile_id, safe='')}/stop", {}
        )

    async def connect(self, profile_id: str, diagnostic: bool = False) -> Connected:
        """Playwright connected to the profile: launched if it is not running
        yet (or always, with ``diagnostic``). Uses the profile's own context and
        first page, so its fingerprint, proxy and cookies apply."""
        cdp_url = None
        if not diagnostic:
            running = next(
                (p for p in await self.list_profiles() if p.get("id") == profile_id),
                None,
            )
            cdp_url = (running or {}).get("cdpUrl")
        if not cdp_url:
            cdp_url = (await self.launch(profile_id, diagnostic=diagnostic))["cdpUrl"]

        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise VeilusError(
                'connect() needs Playwright: pip install "veilus[playwright]"'
            ) from e
        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        return Connected(browser, context, page, cdp_url, pw)
