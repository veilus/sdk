# veilus

Launch [Veilus](https://veilus.io) browser profiles from Python and drive them with Playwright.

Each Veilus profile is a browser with its own fingerprint, proxy and cookies. This package talks to the Veilus app's local API, launches a profile, and connects Playwright to that profile's own browser — so your script runs with the profile's identity.

```bash
pip install "veilus[playwright]"
```

Requires the Veilus desktop app **0.2.9 or newer**, running, with the local API turned on (**API & MCP** page in the app sidebar, Pro plan or higher). Create a token on that page and put it in the environment:

```bash
export VEILUS_API_TOKEN=...
```

```python
import asyncio
from veilus import Veilus

async def main():
    veilus = Veilus()
    profiles = await veilus.list_profiles()

    session = await veilus.connect(profiles[0]["id"])
    await session.page.goto("https://example.com")
    print(await session.page.title())
    await session.close()  # disconnects Playwright; the profile keeps running

    await veilus.stop(profiles[0]["id"])

asyncio.run(main())
```

`connect()` reuses the profile if it is already running, otherwise launches it. It returns the profile's own context and page — don't create a new context with your own user agent, viewport or locale, as those would override the profile's values for that context.

## API

| | |
|---|---|
| `Veilus(token=None, port=None, app_dir=None)` | `token` defaults to `$VEILUS_API_TOKEN`; the port is read from the app's `api-endpoint.json` in `app_dir` (`$VEILUS_APP_DIR` or `~/.veilus`) |
| `await list_profiles()` | all profiles; a running one carries `cdpUrl` |
| `await launch(id, diagnostic=False)` | starts the profile, returns `{"pid", "cdpUrl"}` |
| `await stop(id)` | stops the profile |
| `await connect(id, diagnostic=False)` | Playwright `browser`, `context`, `page`, `cdp_url`, `close()` |

`diagnostic=True` (Veilus 0.2.10 or newer) opens the profile through its proxy but **without** its fingerprint, in a temporary browser directory deleted on stop: the page sees this machine's real values. Use it to tell whether a site blocks the fingerprint or the IP — never on an account you care about.

## Security

The token is read only from your code or `VEILUS_API_TOKEN`. This package never reads the app's token store. The profile's CDP address (`cdpUrl`) has no password: any local program can use it while the profile runs, and it listens on `127.0.0.1` only.

## License

MIT or Apache-2.0, at your option.
