# Solutions

Ready-to-run Veilus Flow scripts for real jobs. Each folder has:

- `script.ts`: paste it into **Veilus Flow → Scripts → New Script**, or let an AI assistant save it over MCP. Then approve it: dataset rows reach approved scripts only.
- `dataset.csv` (most solutions): example rows. Import it as a dataset and assign it to your profiles.
- `README.md`: what it does, how to run it, what to change for your own sites.

| Solution | What it does |
|---|---|
| [price-monitor](price-monitor/) | Track prices on product pages and get told when one changes. |
| [geo-landing-check](geo-landing-check/) | See your landing pages as visitors in each country do. |
| [ai-agent-mcp](ai-agent-mcp/) | Let Claude drive a profile over MCP, then keep what it did as a script. |
| [account-health](account-health/) | Check that each profile is still signed in to its own account, and read a few numbers. |

Every script here runs daily on a real Veilus profile (`examples/check.py`). account-health runs its `demo` entry there; its real-platform selectors were measured by hand (see its README).

## Run one from the command line

Needs Node 22.18 or newer, and a running profile's debug port (the port in `cdpUrl` from `GET /v1/profiles`, or from `launch_profile`):

```bash
cd solutions && npm ci
VEILUS_DEBUG_PORT=<port> VEILUS_VAR_ROWS="$(python3 -c 'import csv,json,sys; print(json.dumps(list(csv.DictReader(open(sys.argv[1])))))' price-monitor/dataset.csv)" node price-monitor/script.ts
```

Or run all of them with `python examples/check.py` (see `examples/README.md`).
