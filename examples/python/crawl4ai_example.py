"""Crawl4AI on a Veilus profile: crawl through the profile's own browser."""

import asyncio

from crawl4ai import AsyncWebCrawler, BrowserConfig
from veilus_example import URL, cdp_url, ok, version


async def main() -> None:
    config = BrowserConfig(browser_mode="cdp", cdp_url=await cdp_url())
    async with AsyncWebCrawler(config=config) as crawler:
        result = await crawler.arun(URL)
    version("crawl4ai")
    ok(result.metadata.get("title", ""))


asyncio.run(main())
