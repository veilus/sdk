# Examples

Each file connects one tool to a running Veilus profile over its CDP address and
prints `VEILUS_EXAMPLE_VERSION <package> <version>` and then
`VEILUS_EXAMPLE_OK <page title>`. They disconnect when done — the profile
keeps running.

Requirements: Veilus 0.2.9 or newer, the local API turned on (**API & MCP** page),
and a token:

```bash
export VEILUS_API_TOKEN=...
export VEILUS_PROFILE_ID=...   # optional; defaults to your first profile
export VEILUS_APP_DIR=...      # optional; where Veilus keeps api-endpoint.json (default ~/.veilus)
```

Run one example:

```bash
uv run --project examples/python --group crawl4ai python examples/python/crawl4ai_example.py
cd examples/js && npm ci && node playwright.mjs
```

Run all and see which pass:

```bash
python examples/check.py            # table on stdout
python examples/check.py --write-tested   # also updates TESTED.md
```

Tools that attach over CDP often set their own User-Agent, `sec-ch-ua` header or
viewport, so the page sees values that contradict the profile. The examples turn
that off (Crawl4AI: `use_managed_browser=True`, `user_agent=""` and no `sec-ch-ua`;
browser-use: `no_viewport=True`; Puppeteer: `defaultViewport: null`). `check.py`
holds them to it: it serves a local page (`VEILUS_EXAMPLE_URL`), loads it once
through the app for the profile's own User-Agent and `sec-ch-ua`, and fails an
example whose load sent different ones, or whose viewport does not fit its window.

`check.py` exits 0 when nothing failed (SKIP is fine), 1 when any example failed, and
2 when it cannot start (API off, no token, no profile, unknown `--only` name).
`--write-tested` needs a full run and cannot be combined with `--only`.

`check.py` also runs every script in `../solutions/` (names start with `solution:`).
It turns the folder's `dataset.csv` into `VEILUS_VAR_ROWS` and passes the profile's
`VEILUS_DEBUG_PORT`, as the app does. A solution passes on exit code 0, a
`RESULT {...}` line and the profile still running. A solution can set `setup_url` (opened in the profile first) and a longer marker that pins the expected result. Run `npm ci` in `solutions/` first; it needs Node 22.18 or newer.

The two examples that drive an LLM (browser-use, Stagehand) need
`ANTHROPIC_API_KEY`; set `VEILUS_EXAMPLE_MODEL` to use another Claude model.
Without the key they are reported as `SKIP`, not run.
