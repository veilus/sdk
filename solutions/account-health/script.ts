// Account health: check that this profile is still signed in to its own account, and read a few numbers.
// Read-only: it never signs in, never sees a password, and never posts, likes, follows or sends messages.
import { chromium, errors } from "playwright";

type Platform = {
  url: string; // page to open
  loggedIn: string; // Playwright selector that only matches when signed in
  metrics: Record<string, string>; // metric name -> selector of the element holding the number
};
type Metric = { value: number | null; raw: string };

// Add a real platform only after measuring its selectors by hand; note the date in README.md. CI runs only "demo".
const PLATFORMS: Record<string, Platform> = {
  // Signed in = the profile holds the cookie veilus_demo_session (open the sign-in link in README.md).
  demo: {
    url: "https://httpbin.org/cookies",
    loggedIn: 'pre:has-text("veilus_demo_session")',
    metrics: { session: "pre" },
  },
};
const WAIT_MS = 10_000;
const MAX_RAW = 40; // keep RESULT short: the app keeps the last 4096 characters

// First number in the text. "1,234" and "1.234" read as 1234; "1.2K" reads as 1.2 (raw keeps "1.2K").
function firstNumber(text: string): number | null {
  const m = text.match(/\d[\d.,]*/);
  if (!m) return null;
  const s = m[0].replace(/[.,]$/, "");
  const n = /^\d{1,3}([.,]\d{3})+$/.test(s) ? Number(s.replace(/[.,]/g, "")) : Number(s.replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

async function notify(webhook: string, platform: string, url: string) {
  const text = `${platform}: profile ${process.env.VEILUS_VAR_PROFILE_ID ?? "?"} is signed out (${url})`;
  const res = await fetch(webhook, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text, content: text, platform, status: "logged_out" }),
  });
  if (!res.ok) throw new Error(`webhook answered ${res.status}`);
}

async function main() {
  const name = process.env.VEILUS_VAR_PLATFORM ?? "";
  const platform = PLATFORMS[name];
  if (!platform) throw new Error(`profile variable PLATFORM must be one of ${Object.keys(PLATFORMS).join(", ")}; got "${name}"`);
  const url = process.env.VEILUS_VAR_URL || platform.url;

  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${process.env.VEILUS_DEBUG_PORT}`);
  const context = browser.contexts()[0];
  const page = context.pages()[0] ?? (await context.newPage());
  await page.goto(url, { waitUntil: "load" });

  const signedIn = await page
    .locator(platform.loggedIn)
    .first()
    .waitFor({ timeout: WAIT_MS })
    .then(
      () => true,
      (e) => {
        if (e instanceof errors.TimeoutError) return false; // only a timeout means signed out
        throw e;
      },
    );

  const metrics: Record<string, Metric> = {};
  if (signedIn) {
    for (const [key, selector] of Object.entries(platform.metrics)) {
      let raw: string;
      try {
        raw = (await page.locator(selector).first().innerText({ timeout: WAIT_MS })).trim();
      } catch {
        throw new Error(`metric ${key} not found at ${selector}: the site may have changed its page; update PLATFORMS.${name}`);
      }
      metrics[key] = { value: firstNumber(raw), raw: raw.slice(0, MAX_RAW) };
    }
  }

  const status = signedIn ? "logged_in" : "logged_out";
  const webhook = process.env.VEILUS_VAR_WEBHOOK_URL;

  console.log(`RESULT ${JSON.stringify({ platform: name, status, metrics })}`);
  if (!signedIn && webhook) {
    try {
      await notify(webhook, name, url);
    } catch (e) {
      console.error(`webhook failed: ${e instanceof Error ? e.message : e}`);
      process.exitCode = 1; // an alert that was not delivered must not look green
    }
  }
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
