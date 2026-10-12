// End-to-end smoke test against a running Veilus app.
// Usage: VEILUS_API_TOKEN=... node examples/smoke.mjs <profile-id>
import { Veilus } from '../src/index.js';

const profileId = process.argv[2];
const veilus = new Veilus();
const platform = (page) => page.evaluate(() => navigator.platform);

const first = await veilus.connect(profileId);
await first.page.goto('https://example.com');
console.log('profile:', await first.page.title(), '|', await platform(first.page), '| cores', await first.page.evaluate(() => navigator.hardwareConcurrency), '|', first.cdpUrl);
await first.close();

const stillRunning = (await veilus.listProfiles()).find((p) => p.id === profileId);
console.log('after close, still running:', Boolean(stillRunning?.cdpUrl));

const again = await veilus.connect(profileId);
console.log('reconnect reuses cdpUrl:', again.cdpUrl === first.cdpUrl);
await again.close();
await veilus.stop(profileId);

const diag = await veilus.connect(profileId, { diagnostic: true });
console.log('diagnostic:', await platform(diag.page), '| cores', await diag.page.evaluate(() => navigator.hardwareConcurrency));
await diag.close();
await veilus.stop(profileId);
console.log('done');
