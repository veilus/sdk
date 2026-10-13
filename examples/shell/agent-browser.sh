#!/usr/bin/env bash
# agent-browser on a Veilus profile: `connect` takes the port of the CDP address.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cd "$here/../js"
cdp="$(node -e "import('./veilus-example.mjs').then(async m => console.log(await m.cdpUrl()))")"
ab() { npx --no-install agent-browser "$@"; }
ab connect "${cdp##*:}" >/dev/null
ab open https://example.com >/dev/null
title="$(ab get title)"
echo "VEILUS_EXAMPLE_VERSION agent-browser $(ab --version | awk '{print $NF}')"
[ "$title" = "Example Domain" ] || { echo "unexpected page title: $title" >&2; exit 1; }
echo "VEILUS_EXAMPLE_OK $title"
