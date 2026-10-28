# Prompt: add a platform with Claude

Needs Claude Code with the Veilus plugin (`/plugin marketplace add veilus/claude-plugin`, then `/plugin install veilus@veilus`)
and the Veilus app running with the local API on.

Sign in to your account in a profile's window first. Then paste this into Claude Code:

```text
Use the Veilus MCP tools. Only read pages: never sign in, type a password, post, like,
follow or send messages.

1. List my profiles and ask me which one is signed in to the account to check, and which
   page shows the numbers I want. Launch that profile and open that page.
2. Take a snapshot. Find a selector that only exists when I am signed in, and a selector
   for each number I asked for. Check them with evaluate_js.
3. Add an entry for this site to PLATFORMS in solutions/account-health/script.ts and save
   the script with save_script as "Account health".
4. Set the profile variable PLATFORM to the new key. Then stop and ask me to approve
   "Account health" in Veilus Flow → Scripts. When I say it is approved, run it on that
   profile with run_script and show me get_run_result.
```
