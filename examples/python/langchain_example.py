"""LangChain on a Veilus profile: PlayWrightBrowserToolkit tools, no LLM needed."""

import asyncio

from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from playwright.async_api import async_playwright
from veilus_example import URL, cdp_url, ok, version


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(await cdp_url())
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
        tools = {t.name: t for t in toolkit.get_tools()}
        await tools["navigate_browser"].arun({"url": URL})
        title = await browser.contexts[0].pages[-1].title()
        # Leaving the `async with` disconnects Playwright; the profile keeps running.
    version("langchain-community")
    ok(title)


asyncio.run(main())
