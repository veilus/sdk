# veilus-mcp

MCP server launcher for [Veilus](https://veilus.io), a desktop app for running browser profiles. It lets Claude Code, Cursor, Claude Desktop or any stdio MCP client list and launch profiles, drive a running profile's page, save and run scripts, and create schedules.

The MCP server itself is the Veilus app (its binary has an `mcp` subcommand). This package finds the installed app and runs `<app binary> mcp`, passing stdin, stdout, stderr and the environment through unchanged, so you can configure it with `npx` instead of a machine-specific path.

## Requirements

- The Veilus desktop app, installed and running, with the local API turned on from the **API & MCP** page in the app sidebar. That page also creates the token.
- A Pro plan or higher: the MCP server and local API are not on the Free plan. The app includes a 7-day Pro trial.
- Node.js 18 or newer.

## Setup

Claude Code:

```bash
claude mcp add --scope user veilus -e VEILUS_API_TOKEN=<token> -- npx -y veilus-mcp
```

Other clients (Cursor, Claude Desktop, …):

```json
{
  "mcpServers": {
    "veilus": {
      "command": "npx",
      "args": ["-y", "veilus-mcp"],
      "env": { "VEILUS_API_TOKEN": "<token>" }
    }
  }
}
```

## Finding the app

1. `VEILUS_BINARY`, if set: the full path to the app binary. The **API & MCP** page shows this path.
2. On macOS: `/Applications/Veilus.app/Contents/MacOS/veilus`, then the same under `~/Applications`.

On other systems, set `VEILUS_BINARY`.

If the app is not found, `veilus-mcp` still starts and lists the Veilus tools, but every tool call returns an error asking you to install the app. This is how MCP directories can inspect the server without the app.

The tool list in `tools.json` is generated from the [Veilus docs](https://docs.veilus.io/reference/mcp/) catalog with `npm run sync-tools`; don't edit it by hand.

## License

MIT or Apache-2.0, at your option.
