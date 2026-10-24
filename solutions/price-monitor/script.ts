// Price monitor: read the price on each product page, compare it with the last run,
// and report what changed. Rows come from the profile's dataset (columns URL, SELECTOR).
import { chromium } from "playwright";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

type Row = { URL: string; SELECTOR?: string };
type Prices = Record<string, number>;
type Change = { url: string; from: number; to: number };
type Failure = { url: string; error: string };

const DEFAULT_SELECTOR = ".price";
const PAUSE_MS = 1_000; // go easy on the site
const MAX_ERROR = 120; // keep RESULT under the app's 4096-character output limit

// Takes the last "." or "," as the decimal point: "£51.77" -> 51.77, "1.299,00 €" -> 1299.
// Limitation: a lone "," or "." before exactly three digits ("1,299", "1.299") reads as a decimal point; add a DECIMAL column if a site needs it.
function parsePrice(text: string): number | null {
  const digits = text.replace(/[^\d.,]/g, "");
  const last = Math.max(digits.lastIndexOf("."), digits.lastIndexOf(","));
  const normalized =
    last === -1 ? digits : `${digits.slice(0, last).replace(/[.,]/g, "")}.${digits.slice(last + 1)}`;
  const n = Number.parseFloat(normalized);
  return Number.isFinite(n) ? n : null;
}

async function notify(webhook: string, changed: Change[]) {
  const text = changed.map((c) => `${c.url}: ${c.from} -> ${c.to}`).join("\n");
  const res = await fetch(webhook, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text, content: text, changed }),
  });
  if (!res.ok) throw new Error(`webhook answered ${res.status}`);
}

async function main() {
  const rows: Row[] = JSON.parse(process.env.VEILUS_VAR_ROWS ?? "[]");
  if (rows.length === 0) throw new Error("no rows: assign a dataset with a URL column to this profile, and approve the script (datasets reach approved scripts only)");
  const outDir = process.env.VEILUS_VAR_OUT_DIR || join(homedir(), "veilus-solutions");
  const stateFile = join(outDir, `price-monitor-${process.env.VEILUS_VAR_PROFILE_ID ?? "default"}.json`);
  const previous: Prices = await readFile(stateFile, "utf8").then(JSON.parse, () => ({}));

  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${process.env.VEILUS_DEBUG_PORT}`);
  const context = browser.contexts()[0];
  const page = context.pages()[0] ?? (await context.newPage());

  const current: Prices = {};
  const changed: Change[] = [];
  const failed: Failure[] = [];
  for (const row of rows) {
    // One bad row must not silence the alerts for the others.
    try {
      const selector = row.SELECTOR || DEFAULT_SELECTOR;
      await page.goto(row.URL, { waitUntil: "domcontentloaded" });
      const text = await page.locator(selector).first().textContent({ timeout: 15_000 });
      const price = parsePrice(text ?? "");
      if (price === null) throw new Error(`no price at selector ${selector}: ${JSON.stringify(text)}`);
      current[row.URL] = price;
      const before = previous[row.URL];
      if (before !== undefined && before !== price) changed.push({ url: row.URL, from: before, to: price });
    } catch (e) {
      const error = (e instanceof Error ? e.message : String(e)).split("\n")[0].slice(0, MAX_ERROR);
      console.error(`${row.URL}: ${error}`);
      failed.push({ url: row.URL, error });
    }
    await page.waitForTimeout(PAUSE_MS);
  }

  const webhook = process.env.VEILUS_VAR_WEBHOOK_URL;
  // Notify before saving: if the webhook fails, the next run still sees the change.
  if (webhook && changed.length > 0) await notify(webhook, changed);

  await mkdir(outDir, { recursive: true });
  await writeFile(stateFile, JSON.stringify({ ...previous, ...current }, null, 2));

  console.log(`RESULT ${JSON.stringify({ checked: rows.length, changed, ...(failed.length > 0 && { failed }) })}`);
  await browser.close();
  if (failed.length > 0) process.exitCode = 1; // keep CI red
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
