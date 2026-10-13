"""Scrapling on a Veilus profile: fetch through the profile's browser over CDP."""

import asyncio
import json
import urllib.request

from scrapling.fetchers import DynamicFetcher
from veilus_example import URL, cdp_url, ok, version


async def main() -> None:
    cdp = await cdp_url()
    with await asyncio.to_thread(urllib.request.urlopen, f"{cdp}/json/version") as resp:
        ws = json.load(resp)["webSocketDebuggerUrl"]
    page = await DynamicFetcher.async_fetch(URL, cdp_url=ws)
    version("scrapling")
    ok(page.css("title::text").get() or "")


asyncio.run(main())
