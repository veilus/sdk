"""Crawlee on a Veilus profile: a browser plugin that connects instead of launching."""

import asyncio

from crawlee.browsers import (
    BrowserPool,
    PlaywrightBrowserController,
    PlaywrightBrowserPlugin,
)
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from veilus_example import URL, cdp_url, ok, version


class VeilusPlugin(PlaywrightBrowserPlugin):
    def __init__(self, cdp: str) -> None:
        super().__init__()
        self._cdp = cdp

    async def new_browser(self) -> PlaywrightBrowserController:
        browser = await self._playwright.chromium.connect_over_cdp(self._cdp)
        return PlaywrightBrowserController(
            browser, max_open_pages_per_browser=1, header_generator=None
        )


async def main() -> None:
    titles: list[str] = []
    crawler = PlaywrightCrawler(
        browser_pool=BrowserPool(plugins=[VeilusPlugin(await cdp_url())])
    )

    @crawler.router.default_handler
    async def handle(context: PlaywrightCrawlingContext) -> None:
        titles.append(await context.page.title())

    await crawler.run([URL])
    version("crawlee")
    ok(titles[0] if titles else "")


asyncio.run(main())
