# Prompt: let Claude build the automation

Needs Claude Code with the Veilus plugin (`/plugin marketplace add veilus/claude-plugin`)
and the Veilus app running with the local API on.

Paste this into Claude Code:

```text
Use the Veilus MCP tools.

1. List my profiles and launch the first one.
2. Open https://httpbin.org/forms/post in it and take a snapshot so you can see the form.
3. Fill the form for one test order (name "Alex Doe", phone 555-0100, email
   alex@example.com, size medium) and submit it. Read the page to check the order went through.
4. Turn what you did into a Playwright script that reads its orders from
   VEILUS_VAR_ROWS (columns NAME, PHONE, EMAIL, SIZE, COMMENTS), submits one order
   per row, throws if the site did not accept one, and prints one
   RESULT {...} line. Save it with save_script as "Form filler".
5. Create a dataset "orders" with two rows and assign it to the profile. Then stop and
   ask me to approve "Form filler" in Veilus Flow → Scripts: dataset rows reach approved
   scripts only. When I say it is approved, run it on that profile with run_script and
   show me get_run_result.
```

Claude stops before the script runs unattended: you approve it in Veilus Flow →
Scripts. Compare what Claude wrote with `script.ts` in this folder.
