#!/usr/bin/env node
// Regenerates tools.json from the docs catalog (`mcpTools` in api-catalog.json).
// Usage: npm run sync-tools [-- <path or URL>]   (default: docs repo main on GitHub)
// Never hand-edit tools.json; the catalog is exported by the Veilus app.
import { readFile, writeFile } from 'node:fs/promises';

const DEFAULT_SOURCE = 'https://raw.githubusercontent.com/veilus/docs/main/src/data/api-catalog.json';
const source = process.argv[2] ?? DEFAULT_SOURCE;

async function load(src) {
  if (!/^https?:\/\//.test(src)) return readFile(src, 'utf8');
  const res = await fetch(src);
  if (!res.ok) throw new Error(`GET ${src}: HTTP ${res.status}`);
  return res.text();
}

const { mcpTools } = JSON.parse(await load(source));
if (!Array.isArray(mcpTools) || mcpTools.length === 0) throw new Error(`${source}: no mcpTools array`);
for (const t of mcpTools) {
  if (typeof t.name !== 'string' || typeof t.description !== 'string' || typeof t.inputSchema !== 'object') {
    throw new Error(`${source}: malformed tool ${JSON.stringify(t.name)}`);
  }
}
await writeFile(new URL('../tools.json', import.meta.url), JSON.stringify(mcpTools, null, 2) + '\n');
console.log(`tools.json: ${mcpTools.length} tools from ${source}`);
