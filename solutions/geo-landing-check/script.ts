// Geo landing check: open each landing page as a visitor from this profile's country sees it.
// Records the exit country, final URL after redirects, page language and a screenshot.
// Run it on one profile per country (each with a proxy in that country).
import { chromium, type Page } from "playwright";
import { mkdir } from "node:fs/promises";
import { homedir } from "node:os";
import { basename, join } from "node:path";

type Row = { URL: string };

// Answers with "loc=XX" for the IP that reached it. page.goto, not page.request:
// only the page goes through the profile's proxy.
const TRACE_URL = "https://www.cloudflare.com/cdn-cgi/trace";
const MAX_TITLE = 80; // keep RESULT under the app's 4096-character output limit

async function exitCountry(page: Page): Promise<string> {
  await page.goto(TRACE_URL, { waitUntil: "domcontentloaded" });
  const country = /^loc=([A-Z]{2})$/m.exec(await page.locator("body").innerText())?.[1];
  if (!country) throw new Error(`could not read the exit country from ${TRACE_URL}`);
  return country;
}

async function main() {
  const rows: Row[] = JSON.parse(process.env.VEILUS_VAR_ROWS ?? "[]");
  if (rows.length === 0) throw new Error("no rows: assign a dataset with a URL column to this profile");
  const expected = process.env.VEILUS_VAR_COUNTRY?.trim().toUpperCase();
  const runId = process.env.VEILUS_VAR_RUN_ID ?? String(Date.now());
  const outDir = join(process.env.VEILUS_VAR_OUT_DIR ?? join(homedir(), "veilus-solutions"), "geo-landing-check");

  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${process.env.VEILUS_DEBUG_PORT}`);
  const context = browser.contexts()[0];
  const page = context.pages()[0] ?? (await context.newPage());

  const country = await exitCountry(page);
  if (expected && country !== expected) {
    throw new Error(`this profile exits from ${country}, not ${expected}: check its proxy`);
  }
  await mkdir(outDir, { recursive: true });

  const pages = [];
  for (const [i, row] of rows.entries()) {
    const res = await page.goto(row.URL, { waitUntil: "domcontentloaded" });
    const screenshot = join(outDir, `${country}-${runId}-${i + 1}.png`);
    await page.screenshot({ path: screenshot }); // visible area only: fullPage would override the profile's screen metrics
    pages.push({
      url: row.URL,
      finalUrl: page.url(),
      status: res?.status() ?? null,
      lang: await page.evaluate(() => document.documentElement.lang || null),
      title: (await page.title()).slice(0, MAX_TITLE),
      screenshot: basename(screenshot),
    });
  }
  const timezone = await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone);

  console.log(`RESULT ${JSON.stringify({ country, timezone, outDir, pages })}`);
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
