"""Crawlee on a Veilus profile: a browser plugin that connects instead of launching."""

import asyncio
import os
import tempfile

# Keep Crawlee's storage out of the cwd; must be set before Crawlee is configured.
os.environ["CRAWLEE_STORAGE_DIR"] = tempfile.mkdtemp(prefix="veilus-crawlee-")

from crawlee.browsers import (
    BrowserPool,
    PlaywrightBrowserController,
    PlaywrightBrowserPlugin,
)
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from playwright.async_api import Page
from veilus_example import URL, cdp_url, ok, version


class ProfileController(PlaywrightBrowserController):
    """Pages live in the profile's default context; closing only disconnects."""

    async def new_page(self, *args, **kwargs) -> Page:
        context = self._browser.contexts[0]
        page = await context.new_page()
        page.on("close", self._on_page_close)
        self._pages.append(page)
        self._total_opened_pages += 1
        return page

    async def close(self, *, force: bool = False) -> None:
        # Never close the profile's context or browser; playwright.stop() disconnects.
        return None


class VeilusPlugin(PlaywrightBrowserPlugin):
    def __init__(self, cdp: str) -> None:
        super().__init__()
        self._cdp = cdp

    async def new_browser(self) -> PlaywrightBrowserController:
        browser = await self._playwright.chromium.connect_over_cdp(self._cdp)
        return ProfileController(
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
