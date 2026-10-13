// playwright-mcp on a Veilus profile: start the MCP server with --cdp-endpoint and call it.
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { URL, cdpUrl, ok, version } from './veilus-example.mjs';

const transport = new StdioClientTransport({
  command: 'npx',
  cwd: import.meta.dirname, // so npx finds the locally installed @playwright/mcp
  args: ['--no-install', '@playwright/mcp', '--cdp-endpoint', await cdpUrl()],
});
const client = new Client({ name: 'veilus-example', version: '0' });
await client.connect(transport);
const res = await client.callTool({ name: 'browser_navigate', arguments: { url: URL } });
const text = res.content.map((c) => c.text ?? '').join('\n');
await client.close();
version('@playwright/mcp');
ok(/Page Title: (.+)/.exec(text)?.[1] ?? '');
