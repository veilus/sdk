# Veilus SDK

Launch [Veilus](https://veilus.io) browser profiles from your own code and drive them with Playwright.

| Language | Package | Install |
|---|---|---|
| Node.js | [`veilus`](js/) | `npm install veilus playwright-core` |
| Python | [`veilus`](python/) | `pip install "veilus[playwright]"` |

Both are thin clients of the Veilus desktop app's local REST API: they launch a profile, then attach Playwright to that profile's own browser over its CDP address, so your script runs with the profile's fingerprint, proxy and cookies. They need the app (0.2.9 or newer) running with the local API on, and a token in `VEILUS_API_TOKEN`.

For other tools (Puppeteer, playwright-mcp, browser-use, Crawl4AI…), see [Use a Profile from Other Tools](https://docs.veilus.io/recipes/agent-frameworks/). The full REST API is documented at [docs.veilus.io](https://docs.veilus.io/reference/rest-api/).

## License

MIT or Apache-2.0, at your option.
