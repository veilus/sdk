"""Shared helpers: find the profile's CDP address and print the agreed marker."""

import os
import sys
from importlib.metadata import version as _dist_version

from veilus import Veilus

# check.py points this at a local page that records the UA and viewport the example used.
URL = os.environ.get("VEILUS_EXAMPLE_URL", "https://example.com")
EXPECTED_TITLE = "Example Domain"


async def cdp_url() -> str:
    """CDP address of VEILUS_PROFILE_ID (or the first profile), launching it if needed."""
    veilus = Veilus()
    profiles = await veilus.list_profiles()
    if not profiles:
        sys.exit("No profile in Veilus - create one first.")
    wanted = os.environ.get("VEILUS_PROFILE_ID") or profiles[0]["id"]
    profile = next((p for p in profiles if p["id"] == wanted), None)
    if profile is None:
        sys.exit(f"VEILUS_PROFILE_ID {wanted!r} not found in Veilus.")
    return profile.get("cdpUrl") or (await veilus.launch(wanted))["cdpUrl"]


def version(pkg: str) -> None:
    print(f"VEILUS_EXAMPLE_VERSION {pkg} {_dist_version(pkg)}")


def ok(title: str) -> None:
    if title.strip() != EXPECTED_TITLE:
        sys.exit(f"unexpected page title: {title!r}")
    print(f"VEILUS_EXAMPLE_OK {title.strip()}")
