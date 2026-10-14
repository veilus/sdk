"""Crawl4AI on a Veilus profile: crawl through the profile's own browser."""

import asyncio

from crawl4ai import AsyncWebCrawler, BrowserConfig
from veilus_example import URL, cdp_url, ok, version


async def main() -> None:
    # By default Crawl4AI opens a new context and sends its own User-Agent and
    # sec-ch-ua headers. These three settings keep the profile's own context and headers.
    config = BrowserConfig(
        browser_mode="cdp",
        cdp_url=await cdp_url(),
        use_managed_browser=True,
        user_agent="",
    )
    config.headers.pop("sec-ch-ua", None)
    async with AsyncWebCrawler(config=config) as crawler:
        result = await crawler.arun(URL)
    version("crawl4ai")
    ok(result.metadata.get("title", ""))


asyncio.run(main())
