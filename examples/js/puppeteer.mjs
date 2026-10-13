// Puppeteer on a Veilus profile: keep defaultViewport null so the page keeps the window size.
import puppeteer from 'puppeteer-core';
import { URL, cdpUrl, ok, version } from './veilus-example.mjs';

const browser = await puppeteer.connect({ browserURL: await cdpUrl(), defaultViewport: null });
const [page = await browser.newPage()] = await browser.pages();
await page.goto(URL);
const title = await page.title();
await browser.disconnect();
version('puppeteer-core');
ok(title);
