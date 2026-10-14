"""Scrapling on a Veilus profile: Playwright drives the profile's own browser
over CDP, Scrapling parses the page (its fetchers would open a new context)."""

import asyncio

from playwright.async_api import async_playwright
from scrapling.parser import Selector
from veilus_example import URL, cdp_url, ok, version


async def main() -> None:
    cdp = await cdp_url()
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(cdp)
        context = browser.contexts[0]
        page = await context.new_page()
        try:
            await page.goto(URL)
            html = await page.content()
        finally:
            await page.close()
        # leaving the block disconnects; the profile's browser keeps running
    version("scrapling")
    ok(Selector(html).css("title::text").get() or "")


asyncio.run(main())
