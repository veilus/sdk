// Playwright on a Veilus profile: use the profile's own context, then disconnect.
import { chromium } from 'playwright-core';
import { URL, cdpUrl, ok, version } from './veilus-example.mjs';

const browser = await chromium.connectOverCDP(await cdpUrl());
const context = browser.contexts()[0];
const page = context.pages()[0] ?? (await context.newPage());
await page.goto(URL);
const title = await page.title();
await browser.close(); // over CDP this disconnects; the profile keeps running
version('playwright-core');
ok(title);
