// Fill a web form once per dataset row and check the site accepted it.
// Written by Claude Code through the Veilus MCP server from prompt.md, then reviewed.
import { chromium } from "playwright";

type Row = { NAME: string; PHONE: string; EMAIL: string; SIZE: string; COMMENTS?: string };

const FORM_URL = process.env.VEILUS_VAR_FORM_URL ?? "https://httpbin.org/forms/post";

async function main() {
  const rows: Row[] = JSON.parse(process.env.VEILUS_VAR_ROWS ?? "[]");
  if (rows.length === 0) throw new Error("no rows: assign a dataset to this profile, and approve the script (datasets reach approved scripts only)");

  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${process.env.VEILUS_DEBUG_PORT}`);
  const context = browser.contexts()[0];
  const page = context.pages()[0] ?? (await context.newPage());

  const orders: { name: string; size: string; accepted: boolean }[] = [];
  for (const row of rows) {
    await page.goto(FORM_URL, { waitUntil: "domcontentloaded" });
    await page.fill('input[name="custname"]', row.NAME);
    await page.fill('input[name="custtel"]', row.PHONE);
    await page.fill('input[name="custemail"]', row.EMAIL);
    await page.check(`input[name="size"][value="${row.SIZE}"]`);
    await page.fill('textarea[name="comments"]', row.COMMENTS ?? "");
    await Promise.all([page.waitForURL("**/post"), page.click('button:has-text("Submit order")')]);
    // httpbin echoes what it received; a real site would show a confirmation instead.
    const echo = JSON.parse(await page.locator("body").innerText());
    const accepted = echo.form?.custname === row.NAME && echo.form?.size === row.SIZE;
    if (!accepted) throw new Error(`the form did not take ${row.NAME}: ${JSON.stringify(echo.form)}`);
    orders.push({ name: row.NAME, size: row.SIZE, accepted });
  }

  console.log(`RESULT ${JSON.stringify({ submitted: orders.length, orders })}`);
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
