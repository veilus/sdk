# Account health

Checks that each profile is still signed in to its own account and reads a few numbers
from it (followers, notifications, orders). Run it on a schedule to find a signed-out
account before you need it.

It only reads. It never signs in for you, never sees a password, and never posts,
likes, follows or sends messages. You sign in once yourself, in the profile's window;
the profile keeps that session.

## Try it in 1 minute (no account needed)

1. Paste `script.ts` into **Veilus Flow → Scripts** and approve it.
2. On a profile, add the profile variable `PLATFORM` = `demo`.
3. Run it: `RESULT {"platform":"demo","status":"logged_out","metrics":{}}`.
4. Open `https://httpbin.org/cookies/set?veilus_demo_session=1` in that profile ("sign in"),
   run again: `"status":"logged_in"` with a `session` metric.
   `https://httpbin.org/cookies/delete?veilus_demo_session` signs out again.

That is the same thing it does on a real site: the session lives in the profile, the
script only reads it.

## Use it on your accounts

1. Sign in to your account in the profile's window, once.
2. Profile variable `PLATFORM`: a key of `PLATFORMS` in `script.ts`. `URL` if the page
   differs (your store's admin, your own profile page).
3. Approve the script and put it on a [schedule](https://docs.veilus.io/automation/schedules/)
   across all your profiles.

Selectors for real platforms do not run in CI. A run that exits 1 with
`metric … not found` means the site changed its page: update that entry in `PLATFORMS`.
The `demo` entry runs daily on a real Veilus profile.

## What a run prints

    RESULT {"platform":"demo","status":"logged_in","metrics":{"session":{"value":1,"raw":"{\n  \"cookies\": {\n    \"veilus_demo_sessio"}}}

`value` is the first number in the element's text; `raw` keeps up to 40 characters of
the text as it was (so `1.2K` is still readable). Exit code 0 means the page was read,
signed in or not, and any alert was delivered. Exit code 1 means the page did not load, `PLATFORM` is wrong, or a
signed-in page did not show a metric. Exit code 1 also means the webhook did not accept the
alert (the RESULT line is still printed).

## Make it yours

| Change | How |
|---|---|
| Get told when an account is signed out | Profile variable `WEBHOOK_URL`: a webhook URL that accepts JSON (the body carries `text` for Slack and `content` for Discord). |
| Another site | Add an entry to `PLATFORMS`: the page, a selector that only exists when signed in, and a selector per number. Or let Claude do it with `prompt.md`. |
| Other numbers | Add a key to that platform's `metrics`. |

## Legal considerations

Read each platform's Terms of Service. This script reads your own account only; how you
use Veilus is your responsibility.
