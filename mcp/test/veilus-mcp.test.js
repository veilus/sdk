import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { chmod, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const BIN = fileURLToPath(new URL('../bin/veilus-mcp.js', import.meta.url));
const TOOLS = JSON.parse(await readFile(new URL('../tools.json', import.meta.url), 'utf8'));
const PKG = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));

/** Runs the launcher with `env`, writes `input`, closes stdin; resolves on exit. */
function run(env, input) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [BIN], { env: { ...process.env, ...env } });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (d) => (stdout += d));
    child.stderr.on('data', (d) => (stderr += d));
    child.on('error', reject);
    child.on('close', (code) => resolve({ code, stdout, stderr }));
    child.stdin.end(input);
  });
}

const rpc = (msgs) => msgs.map((m) => JSON.stringify({ jsonrpc: '2.0', ...m })).join('\n') + '\n';

/** A fake app binary: records argv, echoes stdin lines prefixed, exits with $FAKE_EXIT. */
async function fakeApp() {
  const dir = await mkdtemp(join(tmpdir(), 'veilus-mcp-test-'));
  const bin = join(dir, 'fake-veilus');
  const argvFile = join(dir, 'argv.json');
  await writeFile(
    bin,
    `#!${process.execPath}
const fs = require('node:fs');
fs.writeFileSync(${JSON.stringify(argvFile)}, JSON.stringify(process.argv.slice(2)));
let buf = '';
process.stdin.on('data', (d) => (buf += d));
process.stdin.on('end', () => {
  for (const line of buf.split('\\n').filter(Boolean)) process.stdout.write('fake:' + line + '\\n');
  process.exit(Number(process.env.FAKE_EXIT || 0));
});
`,
  );
  await chmod(bin, 0o755);
  return { dir, bin, argvFile, close: () => rm(dir, { recursive: true, force: true }) };
}

test('tools.json is a non-empty catalog', () => {
  assert.ok(TOOLS.length > 0);
  for (const t of TOOLS) assert.ok(t.name && t.description && t.inputSchema, t.name);
});

test('fallback answers initialize, tools/list, tools/call, ping and unknown methods', async () => {
  const { code, stdout } = await run(
    { VEILUS_BINARY: join(tmpdir(), 'veilus-does-not-exist', 'veilus') },
    rpc([
      { id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '0' } } },
      { method: 'notifications/initialized' },
      { id: 2, method: 'tools/list' },
      { id: 3, method: 'tools/call', params: { name: TOOLS[0].name, arguments: {} } },
      { id: 4, method: 'ping' },
      { id: 5, method: 'resources/list' },
    ]),
  );
  assert.equal(code, 0);
  const replies = stdout.trim().split('\n').map((l) => JSON.parse(l));
  assert.deepEqual(replies.map((r) => r.id), [1, 2, 3, 4, 5]); // notification got no reply
  assert.deepEqual(replies[0].result.serverInfo, { name: 'veilus', version: PKG.version });
  assert.deepEqual(replies[0].result.capabilities, { tools: {} });
  assert.deepEqual(replies[1].result.tools, TOOLS);
  assert.equal(replies[2].result.isError, true);
  assert.match(replies[2].result.content[0].text, /docs\.veilus\.io\/reference\/mcp/);
  assert.deepEqual(replies[3].result, {});
  assert.equal(replies[4].error.code, -32601);
});

test('passthrough runs `<binary> mcp` and forwards bytes both ways', async () => {
  const app = await fakeApp();
  try {
    const input = rpc([{ id: 1, method: 'tools/list' }]);
    const { code, stdout } = await run({ VEILUS_BINARY: app.bin }, input);
    assert.equal(code, 0);
    assert.deepEqual(JSON.parse(await readFile(app.argvFile, 'utf8')), ['mcp']);
    // Control: the fallback would answer with a JSON-RPC result, not the fake's echo.
    assert.equal(stdout, `fake:${input.trim()}\n`);
  } finally {
    await app.close();
  }
});

test('passthrough propagates the app exit code', async () => {
  const app = await fakeApp();
  try {
    const { code } = await run({ VEILUS_BINARY: app.bin, FAKE_EXIT: '7' }, '');
    assert.equal(code, 7);
  } finally {
    await app.close();
  }
});
