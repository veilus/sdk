// Veilus SDK for Node: launch Veilus profiles through the app's local REST API
// and drive them with Playwright over the profile's own CDP endpoint.
//
// Discovery follows the same contract as the app's own MCP server:
// - the port comes from `<app dir>/api-endpoint.json`, a file the app writes
//   when its local API starts and deletes when it stops (it holds no secret);
// - the token comes ONLY from the caller (`token` option) or the
//   `VEILUS_API_TOKEN` environment variable. This package never reads the
//   app's token store: being able to run this package must not mean being able
//   to drive every profile on the machine.

import { readFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';

export const TOKEN_ENV = 'VEILUS_API_TOKEN';
export const APP_DIR_ENV = 'VEILUS_APP_DIR';
const ENDPOINT_FILE = 'api-endpoint.json';

/** An error with a message that says what to do next. */
export class VeilusError extends Error {
  constructor(message, { status, cause } = {}) {
    super(message, cause ? { cause } : undefined);
    this.name = 'VeilusError';
    this.status = status;
  }
}

export class Veilus {
  /**
   * @param {object} [options]
   * @param {string} [options.token]  API token; defaults to $VEILUS_API_TOKEN.
   * @param {number} [options.port]   REST port; defaults to the app's endpoint file.
   * @param {string} [options.appDir] Veilus app directory; defaults to $VEILUS_APP_DIR or ~/.veilus.
   */
  constructor({ token, port, appDir } = {}) {
    this.token = token ?? process.env[TOKEN_ENV];
    if (!this.token) {
      throw new VeilusError(
        `missing ${TOKEN_ENV}. Create a token on the API & MCP page in Veilus (sidebar) ` +
          'and pass it as `token` or put it in the environment.',
      );
    }
    this.port = port;
    this.appDir = appDir ?? process.env[APP_DIR_ENV] ?? join(homedir(), '.veilus');
  }

  /** The REST port: given, or read from the endpoint file on every call (it changes when the app restarts). */
  async #resolvePort() {
    if (this.port) return this.port;
    const path = join(this.appDir, ENDPOINT_FILE);
    let raw;
    try {
      raw = await readFile(path, 'utf8');
    } catch (cause) {
      throw new VeilusError(
        `${path} not found. Open the Veilus app and turn on the local API ` +
          '(API & MCP page in Veilus, sidebar).',
        { cause },
      );
    }
    const port = JSON.parse(raw).rest_port;
    if (!Number.isInteger(port) || port <= 0 || port > 65535) {
      throw new VeilusError(`${path}: missing or invalid \`rest_port\``);
    }
    return port;
  }

  async #request(method, path, body) {
    const port = await this.#resolvePort();
    let res;
    try {
      res = await fetch(`http://127.0.0.1:${port}${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${this.token}`,
          ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (cause) {
      throw new VeilusError(
        `cannot reach the Veilus API on 127.0.0.1:${port}. Is the app running with the local API on?`,
        { cause },
      );
    }
    if (res.status === 204) return null;
    const text = await res.text();
    if (!res.ok) {
      const hint = res.status === 401 ? ' (token rejected: create a new one on the API & MCP page)' : '';
      throw new VeilusError(`${method} ${path} -> ${res.status}${hint}: ${text}`, { status: res.status });
    }
    return text ? JSON.parse(text) : null;
  }

  /** All profiles. A running one carries `cdpUrl`. */
  listProfiles() {
    return this.#request('GET', '/v1/profiles');
  }

  /**
   * Launch a profile and wait for its browser to start.
   * @param {string} profileId
   * @param {{diagnostic?: boolean, headless?: boolean}} [options] `diagnostic` (Veilus >= 0.2.10): the
   *   profile's proxy without its fingerprint, in a temporary directory. `headless`
   *   (Veilus >= 0.2.13): no browser window; the profile's fingerprint is unchanged.
   * @returns {Promise<{pid: number, cdpUrl: string, diagnostic?: boolean, headless?: boolean}>}
   */
  async launch(profileId, { diagnostic = false, headless = false } = {}) {
    const body = {};
    if (diagnostic) body.diagnostic = true;
    if (headless) body.headless = true;
    const out = await this.#request('POST', `/v1/profiles/${encodeURIComponent(profileId)}/launch`, body);
    if (!out?.cdpUrl) {
      throw new VeilusError('the launch reply has no `cdpUrl`: this SDK needs Veilus 0.2.9 or newer.');
    }
    return out;
  }

  /** Stop a running profile. */
  async stop(profileId) {
    await this.#request('POST', `/v1/profiles/${encodeURIComponent(profileId)}/stop`, {});
  }

  /**
   * Playwright connected to the profile: launched if it is not running yet
   * (or always, with `diagnostic`). Uses the profile's own context and first
   * page, so its fingerprint, proxy and cookies apply. `close()` only
   * disconnects — the profile keeps running until `stop()`. `headless` applies
   * only when this call launches the profile; a running one is reused as it is.
   * @param {string} profileId
   * @param {{diagnostic?: boolean, headless?: boolean}} [options]
   */
  async connect(profileId, { diagnostic = false, headless = false } = {}) {
    let cdpUrl;
    if (!diagnostic) {
      const running = (await this.listProfiles()).find((p) => p.id === profileId && p.cdpUrl);
      cdpUrl = running?.cdpUrl;
    }
    cdpUrl ??= (await this.launch(profileId, { diagnostic, headless })).cdpUrl;

    let chromium;
    try {
      ({ chromium } = await import('playwright-core'));
    } catch (cause) {
      throw new VeilusError('connect() needs Playwright: npm install playwright-core', { cause });
    }
    const browser = await chromium.connectOverCDP(cdpUrl);
    const context = browser.contexts()[0];
    const page = context.pages()[0] ?? (await context.newPage());
    return { browser, context, page, cdpUrl, close: () => browser.close() };
  }
}
