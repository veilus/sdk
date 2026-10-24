#!/usr/bin/env node
// Stdio MCP launcher for the Veilus desktop app.
// If the app binary is found, runs `<binary> mcp` with stdio inherited (the app
// is the real MCP server). Otherwise answers MCP introspection itself from the
// bundled tool catalog, and every tool call explains that the app is needed.
import { spawn } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { createInterface } from 'node:readline';

const DOCS_URL = 'https://docs.veilus.io/reference/mcp/';
const pkgDir = new URL('..', import.meta.url);
const { version } = JSON.parse(readFileSync(new URL('package.json', pkgDir), 'utf8'));

function findBinary() {
  if (process.env.VEILUS_BINARY) return existsSync(process.env.VEILUS_BINARY) ? process.env.VEILUS_BINARY : null;
  // No default on Windows or Linux yet: the install path is not documented, set VEILUS_BINARY.
  if (process.platform !== 'darwin') return null;
  const bundle = 'Veilus.app/Contents/MacOS/veilus';
  return [join('/Applications', bundle), join(homedir(), 'Applications', bundle)].find((p) => existsSync(p)) ?? null;
}

function passthrough(binary) {
  const child = spawn(binary, ['mcp'], { stdio: 'inherit', env: process.env });
  const signals = ['SIGINT', 'SIGTERM', 'SIGHUP'];
  for (const sig of signals) process.on(sig, () => child.kill(sig));
  child.on('error', (err) => {
    process.stderr.write(`veilus-mcp: cannot start ${binary}: ${err.message}\n`);
    process.exit(1);
  });
  child.on('exit', (code, signal) => {
    if (signal) {
      for (const sig of signals) process.removeAllListeners(sig);
      process.kill(process.pid, signal);
    } else {
      process.exit(code ?? 1);
    }
  });
}

function fallback() {
  const tools = JSON.parse(readFileSync(new URL('tools.json', pkgDir), 'utf8'));
  process.stderr.write(`veilus-mcp: Veilus app not found (set VEILUS_BINARY); serving the tool list only. See ${DOCS_URL}\n`);
  const send = (msg) => process.stdout.write(JSON.stringify({ jsonrpc: '2.0', ...msg }) + '\n');
  const handlers = {
    initialize: (params) => ({
      protocolVersion: params?.protocolVersion ?? '2025-06-18',
      capabilities: { tools: {} },
      serverInfo: { name: 'veilus', version },
    }),
    ping: () => ({}),
    'tools/list': () => ({ tools }),
    'tools/call': () => ({
      isError: true,
      content: [{
        type: 'text',
        text: `The Veilus desktop app must be installed and running, with the local API turned on, for Veilus tools to work. Set VEILUS_BINARY to the app binary if it is not in the default location. Setup: ${DOCS_URL}`,
      }],
    }),
  };
  createInterface({ input: process.stdin }).on('line', (line) => {
    if (!line.trim()) return;
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      return send({ id: null, error: { code: -32700, message: 'Parse error' } });
    }
    if (msg.id === undefined) return; // notification (e.g. notifications/initialized): no reply
    const handler = Object.hasOwn(handlers, msg.method) ? handlers[msg.method] : null;
    if (!handler) return send({ id: msg.id, error: { code: -32601, message: `Method not found: ${msg.method}` } });
    send({ id: msg.id, result: handler(msg.params) });
  });
}

const binary = findBinary();
if (binary) passthrough(binary);
else fallback();
