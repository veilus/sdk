import type { Browser, BrowserContext, Page } from 'playwright-core';

export declare const TOKEN_ENV: 'VEILUS_API_TOKEN';
export declare const APP_DIR_ENV: 'VEILUS_APP_DIR';

export declare class VeilusError extends Error {
  /** HTTP status of the failed request, when there was one. */
  status?: number;
}

export interface VeilusOptions {
  /** API token; defaults to `$VEILUS_API_TOKEN`. */
  token?: string;
  /** REST port; defaults to the app's `api-endpoint.json`. */
  port?: number;
  /** Veilus app directory; defaults to `$VEILUS_APP_DIR` or `~/.veilus`. */
  appDir?: string;
}

export interface Profile {
  id: string;
  name: string;
  slug: string;
  status: string;
  os: string;
  /** Present while the profile is running. */
  cdpUrl?: string;
  [field: string]: unknown;
}

export interface LaunchOptions {
  /** Veilus >= 0.2.10: the profile's proxy without its fingerprint, in a temporary directory. */
  diagnostic?: boolean;
  /** Veilus >= 0.2.13: no browser window; the profile's fingerprint is unchanged. `connect()` reuses a running profile as it is. */
  headless?: boolean;
}

export interface Launched {
  pid: number;
  cdpUrl: string;
  diagnostic?: boolean;
  headless?: boolean;
}

export interface Connected {
  browser: Browser;
  context: BrowserContext;
  page: Page;
  cdpUrl: string;
  /** Disconnects Playwright; the profile keeps running. */
  close(): Promise<void>;
}

export declare class Veilus {
  constructor(options?: VeilusOptions);
  listProfiles(): Promise<Profile[]>;
  launch(profileId: string, options?: LaunchOptions): Promise<Launched>;
  stop(profileId: string): Promise<void>;
  connect(profileId: string, options?: LaunchOptions): Promise<Connected>;
}
