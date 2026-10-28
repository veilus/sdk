"""Run every example against a real Veilus profile and report PASS / FAIL / SKIP.

PASS needs all three: exit code 0, the example's marker line (`VEILUS_EXAMPLE_OK`, or `RESULT ` for solutions),
and the profile still running afterwards (an example must disconnect, never close the browser).
A solution's marker may carry more than "RESULT " to pin the expected result (account-health pins its status).
An example (not a solution) must also open a local probe page, send the profile's own User-Agent and sec-ch-ua,
and keep the viewport its window gives — frameworks that attach over CDP like to override them, which makes the
profile contradict itself while the title check stays green.
SKIP always says why. `TESTED.md` is generated from this — never edit it by hand.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Self
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
SOLUTIONS = HERE.parent / "solutions"
PY = ["uv", "run", "--project", str(HERE / "python"), "--group"]
TIMEOUT_S = 300
PROBE_WAIT_S = 5
# Enough text that Crawl4AI's anti-bot heuristic does not reject it as an empty page.
PROBE_PAGE = b"""<!doctype html><title>Example Domain</title><h1>Example Domain</h1>
<p>This page is served by examples/check.py. It records the User-Agent and sec-ch-ua
headers it was fetched with, and the viewport and window size the page sees, so an
example that overrides them on the Veilus profile fails instead of passing.</p>
<script>navigator.sendBeacon("/probe", JSON.stringify({ua: navigator.userAgent,
  w: innerWidth, h: innerHeight, ow: outerWidth, oh: outerHeight}));</script>
"""
# Window frame: outerWidth - innerWidth is 0 on macOS; leave room for a frame elsewhere.
FRAME_PX = 16


class PreflightError(Exception):
    """The environment cannot run the examples (exit code 2, not a FAIL)."""


@dataclass(frozen=True)
class Example:
    name: str
    cmd: list[str]
    needs_env: tuple[str, ...] = ()
    needs_cmd: tuple[str, ...] = ()
    marker: str = "VEILUS_EXAMPLE_OK "
    env: dict[str, str] = field(default_factory=dict)
    probe: bool = True
    # Opened in the profile through the Veilus API before the example runs (e.g. to set a session).
    setup_url: str = ""


@dataclass
class Result:
    name: str
    status: str
    reason: str = ""
    version: str = ""


def _py(group: str, file: str, **kw) -> Example:
    return Example(
        group,
        [*PY, group, "python", str(HERE / "python" / file)],
        needs_cmd=("uv",),
        **kw,
    )


def _js(name: str, file: str, **kw) -> Example:
    return Example(name, ["node", str(HERE / "js" / file)], needs_cmd=("node",), **kw)


def dataset_rows(path: Path) -> str:
    """A solution's dataset.csv as the JSON array Veilus passes in VEILUS_VAR_ROWS."""
    with path.open(encoding="utf-8", newline="") as f:
        return json.dumps(list(csv.DictReader(f)))


def _solution(
    name: str,
    variant: str = "",
    *,
    marker: str = "RESULT ",
    env: dict[str, str] | None = None,
    setup_url: str = "",
) -> Example:
    d = SOLUTIONS / name
    base = {
        # Never the runner's real home: $HOME is the dev's live environment.
        "VEILUS_VAR_OUT_DIR": str(
            Path(tempfile.gettempdir()) / "veilus-solutions-check"
        ),
    }
    if (d / "dataset.csv").exists():
        base["VEILUS_VAR_ROWS"] = dataset_rows(d / "dataset.csv")
    return Example(
        f"solution:{name}" + (f"/{variant}" if variant else ""),
        ["node", str(d / "script.ts")],
        needs_cmd=("node",),
        marker=marker,
        probe=False,
        env={**base, **(env or {})},
        setup_url=setup_url,
    )


@dataclass(frozen=True)
class Seen:
    """One load of the probe page: request headers, then what the page's script read."""

    ua: str
    ch: str
    js_ua: str | None
    viewport: tuple[int, int, int, int] | None  # inner w, h, outer w, h


def drift(want: Seen, got: Seen) -> str | None:
    """Why `got` (an example's page load) differs from the profile's own, or None."""
    if got.js_ua is None:
        return "the probe page script never reported navigator.userAgent and viewport"
    for label, a, b in (
        ("User-Agent header", want.ua, got.ua),
        ("sec-ch-ua header", want.ch, got.ch),
        ("navigator.userAgent", want.js_ua, got.js_ua),
    ):
        if a != b:
            return f"{label} is {b!r}, the profile's is {a!r}"
    # The viewport is held to the page's own window, not to `want`: the app's tab
    # (where `want` comes from) reports outerWidth 0, so its viewport is no reference.
    w, h, ow, oh = got.viewport
    if not (ow - FRAME_PX <= w <= ow and 0 < h < oh):
        return (
            f"viewport {w}x{h} does not fit its window {ow}x{oh}: the tool overrides it"
        )
    return None


class Probe:
    """Local page that records the headers it was fetched with and what its script reads."""

    def __enter__(self) -> Self:
        docs: list[tuple[str, str]] = []
        reports: list[dict] = []
        self._docs, self._reports = docs, reports

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path.split("?")[0] != "/":
                    self.send_error(404)
                    return
                docs.append(
                    (
                        self.headers.get("User-Agent", ""),
                        self.headers.get("sec-ch-ua", ""),
                    )
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(PROBE_PAGE)

            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                try:
                    reports.append(json.loads(body))
                except ValueError:
                    pass
                self.send_response(204)
                self.end_headers()

            def log_message(self, *_args) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}/"
        return self

    def __exit__(self, *_exc) -> None:
        self._server.shutdown()
        self._server.server_close()

    def reset(self) -> None:
        self._docs.clear()
        self._reports.clear()

    def wait(self, timeout: float = PROBE_WAIT_S) -> Seen | None:
        """The latest page load, or None if the page was never fetched."""
        deadline = time.monotonic() + timeout
        while not self._reports and time.monotonic() < deadline:
            time.sleep(0.1)
        if not self._docs:
            return None
        ua, ch = self._docs[-1]
        if not self._reports:
            return Seen(ua, ch, None, None)
        r = self._reports[-1]
        return Seen(
            ua, ch, r.get("ua"), tuple(r.get(k, 0) for k in ("w", "h", "ow", "oh"))
        )


LLM = ("ANTHROPIC_API_KEY",)
DEMO = {"VEILUS_VAR_PLATFORM": "demo"}
EXAMPLES = [
    _js("playwright", "playwright.mjs"),
    _js("puppeteer", "puppeteer.mjs"),
    _js("playwright-mcp", "playwright-mcp.mjs"),
    Example(
        "agent-browser",
        ["bash", str(HERE / "shell" / "agent-browser.sh")],
        needs_cmd=("node",),
    ),
    _py("crawl4ai", "crawl4ai_example.py"),
    _py("langchain", "langchain_example.py"),
    _py("scrapling", "scrapling_example.py"),
    _py("crawlee", "crawlee_example.py"),
    _py("browser-use", "browser_use_example.py", needs_env=LLM),
    _js("stagehand", "stagehand.mjs", needs_env=LLM),
    _solution("price-monitor"),
    _solution("geo-landing-check"),
    _solution("ai-agent-mcp"),
    _solution(
        "account-health",
        env=DEMO,
        setup_url="https://httpbin.org/cookies/delete?veilus_demo_session",
        marker='RESULT {"platform":"demo","status":"logged_out"',
    ),
    _solution(
        "account-health",
        "session",
        env=DEMO,
        setup_url="https://httpbin.org/cookies/set?veilus_demo_session=1",
        marker='RESULT {"platform":"demo","status":"logged_in"',
    ),
]


def run_example(
    ex: Example,
    env: dict[str, str],
    profile_running,
    timeout: int = TIMEOUT_S,
    probe: tuple[Seen, object] | None = None,
    navigate=None,
) -> Result:
    full_env = {**os.environ, **env, **ex.env}
    for var in ex.needs_env:
        if not full_env.get(var):
            return Result(ex.name, "SKIP", f"no {var}")
    for cmd in ex.needs_cmd:
        if shutil.which(cmd) is None:
            return Result(ex.name, "SKIP", f"{cmd} not installed")
    if ex.setup_url:
        if navigate is None:
            return Result(ex.name, "FAIL", "setup_url needs the Veilus API to open it")
        try:
            navigate(ex.setup_url)
        except Exception as e:  # noqa: BLE001 - any failure is a FAIL row, not a crash
            return Result(ex.name, "FAIL", f"setup_url {ex.setup_url}: {e}")
    proc = subprocess.Popen(
        ex.cmd,
        env=full_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return Result(ex.name, "FAIL", f"timeout after {timeout}s")
    version = ""
    marker = False
    for line in stdout.splitlines():
        if line.startswith("VEILUS_EXAMPLE_VERSION "):
            version = line.split(" ", 1)[1].strip()
        if line.startswith(ex.marker):
            marker = True
    tail = (stderr or stdout).strip().splitlines()[-3:]
    if proc.returncode != 0:
        return Result(
            ex.name, "FAIL", f"exit {proc.returncode}: {' | '.join(tail)}", version
        )
    if not marker:
        return Result(ex.name, "FAIL", f"no {ex.marker.strip()} line", version)
    if not profile_running(env.get("VEILUS_PROFILE_ID", "")):
        return Result(ex.name, "FAIL", "example closed the profile", version)
    if ex.probe and probe:
        want, read = probe
        got = read()
        if got is None:
            return Result(ex.name, "FAIL", "never loaded the probe page", version)
        reason = drift(want, got)
        if reason:
            return Result(ex.name, "FAIL", reason, version)
    return Result(ex.name, "PASS", "", version)


def render_table(results: list[Result], date: str) -> str:
    lines = [
        f"Tested {date} with a real Veilus profile — generated by `check.py`.",
        "",
        "| Example | Version | Result | Note |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {r.name} | {r.version or '—'} | {r.status} | {r.reason.replace('|', chr(92) + '|')} |"
        for r in results
    ]
    return "\n".join(lines) + "\n"


class Api:
    def __init__(self) -> None:
        app_dir = Path(os.environ.get("VEILUS_APP_DIR", Path.home() / ".veilus"))
        endpoint = app_dir / "api-endpoint.json"
        if not endpoint.exists():
            raise PreflightError(
                f"{endpoint} not found — open Veilus and turn on the local API "
                "(API & MCP page)."
            )
        try:
            self.base = (
                f"http://127.0.0.1:{json.loads(endpoint.read_text())['rest_port']}"
            )
        except (ValueError, KeyError, TypeError) as e:
            raise PreflightError(f"{endpoint} is malformed: {e!r}") from e
        self.token = os.environ.get("VEILUS_API_TOKEN")
        if not self.token:
            raise PreflightError(
                "VEILUS_API_TOKEN is not set — create a token on the API & MCP page."
            )

    def _call(self, method: str, path: str, body: dict | None = None):
        headers = {"Authorization": f"Bearer {self.token}"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.base + path,
            method=method,
            headers=headers,
            data=None if body is None else json.dumps(body).encode(),
        )
        with urllib.request.urlopen(req, timeout=120) as res:
            body = res.read()
        return json.loads(body) if body else None

    def profiles(self) -> list[dict]:
        data = self._call("GET", "/v1/profiles")
        return data.get("profiles", data) if isinstance(data, dict) else data

    def ensure_running(self, profile_id: str) -> None:
        if not any(p["id"] == profile_id for p in self.profiles()):
            raise PreflightError(f"profile {profile_id} not found in Veilus.")
        if not self.is_running(profile_id):
            self._call("POST", f"/v1/profiles/{profile_id}/launch")

    def navigate(self, profile_id: str, url: str) -> None:
        self._call("POST", f"/v1/profiles/{profile_id}/navigate", {"url": url})

    def is_running(self, profile_id: str) -> bool:
        return any(p["id"] == profile_id and p.get("cdpUrl") for p in self.profiles())

    def debug_port(self, profile_id: str) -> int:
        url = next(
            (p.get("cdpUrl") for p in self.profiles() if p["id"] == profile_id), None
        )
        port = urlparse(url).port if url else None
        if not port:
            raise PreflightError(f"profile {profile_id} has no CDP address: {url!r}")
        return port


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--write-tested", action="store_true")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    names = [e.name for e in EXAMPLES]
    unknown = [n for n in args.only if n not in names]
    if unknown:
        print(
            f"Unknown --only name(s) {unknown}; valid: {', '.join(names)}",
            file=sys.stderr,
        )
        return 2
    if args.write_tested and args.only:
        print("--write-tested needs a full run; drop --only.", file=sys.stderr)
        return 2
    with Probe() as probe:
        return _run(args, probe)


def _run(args, probe: Probe) -> int:
    try:
        api = Api()
        profiles = api.profiles()
        if not profiles:
            raise PreflightError("No profile in Veilus — create one first.")
        pid = os.environ.get("VEILUS_PROFILE_ID") or profiles[0]["id"]
        api.ensure_running(pid)
        port = api.debug_port(pid)
        # The profile's own values: the app navigates its tab, no framework involved.
        probe.reset()
        api.navigate(pid, probe.url)
        want = probe.wait(15)
        if want is None or want.js_ua is None:
            raise PreflightError(
                f"the profile did not load the probe page {probe.url}: {want!r}"
            )
    except PreflightError as e:
        print(e, file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError) as e:  # URLError/HTTPError are OSError
        print(f"Veilus local API preflight failed: {e!r}", file=sys.stderr)
        return 2
    env = {
        "VEILUS_PROFILE_ID": pid,
        "VEILUS_VAR_PROFILE_ID": pid,
        "VEILUS_DEBUG_PORT": str(port),
        "VEILUS_EXAMPLE_URL": probe.url,
    }
    todo = [e for e in EXAMPLES if not args.only or e.name in args.only]
    results = []
    for e in todo:
        probe.reset()
        results.append(
            run_example(
                e,
                env,
                api.is_running,
                probe=(want, probe.wait),
                navigate=lambda url: api.navigate(pid, url),
            )
        )
    table = render_table(results, dt.datetime.now().astimezone().date().isoformat())
    print(table)
    if args.write_tested:
        (HERE / "TESTED.md").write_text(table, encoding="utf-8")
    if args.json:
        args.json.write_text(
            json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8"
        )
    return 1 if any(r.status == "FAIL" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
