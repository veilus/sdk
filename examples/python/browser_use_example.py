"""browser-use on a Veilus profile: a Claude agent drives the profile's browser."""

import asyncio
import os

from browser_use import Agent, Browser
from browser_use.llm import ChatAnthropic
from veilus_example import URL, cdp_url, ok, version


async def main() -> None:
    browser = Browser(cdp_url=await cdp_url(), keep_alive=True)
    llm = ChatAnthropic(
        model=os.environ.get("VEILUS_EXAMPLE_MODEL", "claude-sonnet-5-5")
    )
    agent = Agent(
        task=f"Open {URL} and reply with the page title only.", llm=llm, browser=browser
    )
    history = await agent.run(max_steps=5)
    version("browser-use")
    ok((history.final_result() or "").strip().strip('"'))


asyncio.run(main())
