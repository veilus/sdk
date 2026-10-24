# AI agent over MCP

Let Claude drive a Veilus profile: look at a page, fill a form, check the result, then
save what it did as a script you approve and schedule. The example fills an order form
once per row of a dataset.

## Two ways to use it

- **With Claude:** follow `prompt.md`. Claude works in the profile through the Veilus
  MCP server and saves a script. Nothing runs unattended until you approve it.
- **Without Claude:** paste `script.ts` into Veilus Flow → Scripts and approve it, import
  `dataset.csv` and assign it to a profile.

## Make it yours

| Change | How |
|---|---|
| Your own form | Profile variable `FORM_URL`, then change the `page.fill` selectors and the check after the submit: the example reads httpbin's JSON echo, while a real site shows a confirmation page. Or ask Claude to redo step 4 of the prompt on your page. |
| Your data | One row per submission in `dataset.csv`. |

`script.ts` runs daily on a real Veilus profile. The prompt is not tested
automatically: an LLM writes different code on each run, so read the script before you approve it.
