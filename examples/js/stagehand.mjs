// Stagehand on a Veilus profile: LOCAL mode attached to the profile's browser over CDP.
import { Stagehand } from '@browserbasehq/stagehand';
import { z } from 'zod';
import { URL, cdpUrl, ok, version } from './veilus-example.mjs';

const model = process.env.VEILUS_EXAMPLE_MODEL ?? 'claude-sonnet-5-5';
// Stagehand wants the browser's WebSocket endpoint, not the http:// address.
const { webSocketDebuggerUrl } = await (await fetch(`${await cdpUrl()}/json/version`)).json();
const stagehand = new Stagehand({
  env: 'LOCAL',
  localBrowserLaunchOptions: { cdpUrl: webSocketDebuggerUrl },
  model: `anthropic/${model}`,
});
await stagehand.init();
const page = stagehand.context.pages()[0];
await page.goto(URL);
const { title } = await stagehand.extract('the page title', z.object({ title: z.string() }));
await stagehand.close({ force: false }); // detach; the profile keeps running
version('@browserbasehq/stagehand');
ok(title);
