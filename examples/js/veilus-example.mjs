// Shared helpers: find the profile's CDP address and print the agreed marker.
import { createRequire } from 'node:module';
import { Veilus } from 'veilus';

// check.py points this at a local page that records the UA and viewport the example used.
export const URL = process.env.VEILUS_EXAMPLE_URL || 'https://example.com';
const EXPECTED_TITLE = 'Example Domain';
const require = createRequire(import.meta.url);

function fail(message) {
  console.error(message);
  process.exit(1);
}

export async function cdpUrl() {
  const veilus = new Veilus();
  const profiles = await veilus.listProfiles();
  if (profiles.length === 0) fail('no Veilus profiles found: create one in the app first');
  const wanted = process.env.VEILUS_PROFILE_ID || profiles[0].id;
  const profile = profiles.find((p) => p.id === wanted);
  if (!profile) fail(`VEILUS_PROFILE_ID ${wanted} is not one of the ${profiles.length} profiles`);
  return profile.cdpUrl ?? (await veilus.launch(wanted)).cdpUrl;
}

export function version(pkg) {
  console.log(`VEILUS_EXAMPLE_VERSION ${pkg} ${require(`${pkg}/package.json`).version}`);
}

export function ok(title) {
  if (title.trim() !== EXPECTED_TITLE) fail(`unexpected page title: ${JSON.stringify(title)}`);
  console.log(`VEILUS_EXAMPLE_OK ${title.trim()}`);
}
