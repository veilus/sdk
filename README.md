# Veilus SDK

Launch [Veilus](https://veilus.io) browser profiles from your own code and drive them with Playwright.

## Works with

Tested with a real Veilus profile — see [examples/TESTED.md](https://github.com/veilus/sdk/blob/main/examples/TESTED.md) for versions and date:
[Playwright](https://github.com/veilus/sdk/blob/main/examples/js/playwright.mjs) ·
[Puppeteer](https://github.com/veilus/sdk/blob/main/examples/js/puppeteer.mjs) ·
[browser-use](https://github.com/veilus/sdk/blob/main/examples/python/browser_use_example.py) ·
[Stagehand](https://github.com/veilus/sdk/blob/main/examples/js/stagehand.mjs) ·
[Crawl4AI](https://github.com/veilus/sdk/blob/main/examples/python/crawl4ai_example.py) ·
[LangChain](https://github.com/veilus/sdk/blob/main/examples/python/langchain_example.py) ·
[Scrapling](https://github.com/veilus/sdk/blob/main/examples/python/scrapling_example.py) ·
[Crawlee](https://github.com/veilus/sdk/blob/main/examples/python/crawlee_example.py) ·
[playwright-mcp](https://github.com/veilus/sdk/blob/main/examples/js/playwright-mcp.mjs) ·
[agent-browser](https://github.com/veilus/sdk/blob/main/examples/shell/agent-browser.sh)

| Language | Package | Install |
|---|---|---|
| Node.js | [`veilus`](js/) | `npm install veilus playwright-core` |
| Python | [`veilus`](python/) | `pip install "veilus[playwright]"` |
| MCP | [`veilus-mcp`](mcp/) | `npx -y veilus-mcp` (launcher for the app's MCP server) |

Both are thin clients of the Veilus desktop app's local REST API: they launch a profile, then attach Playwright to that profile's own browser over its CDP address, so your script runs with the profile's fingerprint, proxy and cookies. They need the app (0.2.9 or newer) running with the local API on, and a token in `VEILUS_API_TOKEN`.

For other tools (Puppeteer, playwright-mcp, browser-use, Crawl4AI…), see [Use a Profile from Other Tools](https://docs.veilus.io/recipes/agent-frameworks/). The full REST API is documented at [docs.veilus.io](https://docs.veilus.io/reference/rest-api/).

Also in the docs: [Web scraping recipe](https://docs.veilus.io/recipes/web-scraping/) · [Common issues](https://docs.veilus.io/troubleshooting/common-issues/) · [FAQ](https://docs.veilus.io/reference/faq/).

## License

MIT or Apache-2.0, at your option.
