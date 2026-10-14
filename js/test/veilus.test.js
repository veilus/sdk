import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { Veilus, VeilusError } from '../src/index.js';

/** A fake Veilus REST API: records requests, answers with `handler`. */
async function fakeApi(handler) {
  const requests = [];
  const server = createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    requests.push({ method: req.method, url: req.url, auth: req.headers.authorization, body });
    const [status, reply] = handler(req, body);
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(reply === undefined ? '' : JSON.stringify(reply));
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const appDir = await mkdtemp(join(tmpdir(), 'veilus-sdk-test-'));
  await writeFile(join(appDir, 'api-endpoint.json'), JSON.stringify({ rest_port: server.address().port }));
  return {
    appDir,
    requests,
    async close() {
      server.close();
      await rm(appDir, { recursive: true, force: true });
    },
  };
}

test('finds the port in the endpoint file and sends the bearer token', async () => {
  const api = await fakeApi(() => [200, [{ id: 'p1', name: 'one', cdpUrl: 'http://127.0.0.1:9' }]]);
  const veilus = new Veilus({ token: 't0k', appDir: api.appDir });
  const profiles = await veilus.listProfiles();
  assert.equal(profiles[0].cdpUrl, 'http://127.0.0.1:9');
  assert.deepEqual(api.requests.map((r) => [r.method, r.url, r.auth]), [['GET', '/v1/profiles', 'Bearer t0k']]);
  await api.close();
});

test('launch sends diagnostic only when asked, and stop posts to the profile', async () => {
  const api = await fakeApi((req) =>
    req.url.endsWith('/stop') ? [204] : [200, { pid: 7, cdpUrl: 'http://127.0.0.1:9' }],
  );
  const veilus = new Veilus({ token: 't', appDir: api.appDir });
  await veilus.launch('p1');
  await veilus.launch('p1', { diagnostic: true });
  await veilus.stop('p1');
  assert.deepEqual(
    api.requests.map((r) => [r.url, r.body]),
    [
      ['/v1/profiles/p1/launch', '{}'],
      ['/v1/profiles/p1/launch', '{"diagnostic":true}'],
      ['/v1/profiles/p1/stop', '{}'],
    ],
  );
  await api.close();
});

test('launch sends headless only when asked, alone or with diagnostic', async () => {
  const api = await fakeApi(() => [200, { pid: 7, cdpUrl: 'http://127.0.0.1:9' }]);
  const veilus = new Veilus({ token: 't', appDir: api.appDir });
  await veilus.launch('p1', { headless: true });
  await veilus.launch('p1', { headless: true, diagnostic: true });
  await veilus.launch('p1', { headless: false });
  assert.deepEqual(
    api.requests.map((r) => r.body),
    ['{"headless":true}', '{"diagnostic":true,"headless":true}', '{}'],
  );
  await api.close();
});

test('a launch reply without cdpUrl names the minimum app version', async () => {
  const api = await fakeApi(() => [200, { pid: 7 }]);
  const veilus = new Veilus({ token: 't', appDir: api.appDir });
  await assert.rejects(veilus.launch('p1'), /Veilus 0\.2\.9 or newer/);
  await api.close();
});

test('a rejected token says what to do', async () => {
  const api = await fakeApi(() => [401, { error: 'unauthorized' }]);
  const veilus = new Veilus({ token: 'old', appDir: api.appDir });
  await assert.rejects(veilus.listProfiles(), (e) => e instanceof VeilusError && e.status === 401 && /API & MCP/.test(e.message));
  await api.close();
});

test('no endpoint file: the error says to turn the local API on', async () => {
  const appDir = await mkdtemp(join(tmpdir(), 'veilus-sdk-test-'));
  const veilus = new Veilus({ token: 't', appDir });
  await assert.rejects(veilus.listProfiles(), /turn on the local API/);
  await rm(appDir, { recursive: true, force: true });
});

// Decision 0124 / 0016: the SDK must never read the app's token store. With
// the store right there and no token given, it still refuses — and the error
// does not point at the store either.
test('never falls back to the token store', async () => {
  const appDir = await mkdtemp(join(tmpdir(), 'veilus-sdk-test-'));
  await writeFile(join(appDir, 'api-tokens.json'), JSON.stringify([{ token: 'secret' }]));
  const saved = process.env.VEILUS_API_TOKEN;
  delete process.env.VEILUS_API_TOKEN;
  try {
    assert.throws(
      () => new Veilus({ appDir }),
      (e) => /VEILUS_API_TOKEN/.test(e.message) && !e.message.includes('api-tokens'),
    );
  } finally {
    if (saved !== undefined) process.env.VEILUS_API_TOKEN = saved;
    await rm(appDir, { recursive: true, force: true });
  }
  const source = await readFile(new URL('../src/index.js', import.meta.url), 'utf8');
  assert.ok(!source.includes('api-tokens'), 'the SDK source names the token store');
});
