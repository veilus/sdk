"""End-to-end smoke test against a running Veilus app.

Usage: VEILUS_API_TOKEN=... python examples/smoke.py <profile-id>
"""

import asyncio
import sys

from veilus import Veilus


async def main(profile_id: str) -> None:
    veilus = Veilus()
    first = await veilus.connect(profile_id)
    await first.page.goto("https://example.com")
    platform = await first.page.evaluate("navigator.platform")
    cores = await first.page.evaluate("navigator.hardwareConcurrency")
    print("profile:", await first.page.title(), "|", platform, "| cores", cores)
    await first.close()

    running = [p for p in await veilus.list_profiles() if p["id"] == profile_id]
    print("after close, still running:", bool(running and running[0].get("cdpUrl")))

    again = await veilus.connect(profile_id)
    print("reconnect reuses cdpUrl:", again.cdp_url == first.cdp_url)
    await again.close()
    await veilus.stop(profile_id)

    diag = await veilus.connect(profile_id, diagnostic=True)
    platform = await diag.page.evaluate("navigator.platform")
    cores = await diag.page.evaluate("navigator.hardwareConcurrency")
    print("diagnostic:", platform, "| cores", cores)
    await diag.close()
    await veilus.stop(profile_id)
    print("done")


asyncio.run(main(sys.argv[1]))
