# Price monitor

Checks the price on a list of product pages, compares it with the last run, and
tells you what changed. Each page is opened in a real Veilus profile, with that
profile's fingerprint, proxy and cookies.

## Run it in 3 steps

1. **Script:** in Veilus Flow → Scripts, create a script and paste `script.ts`. Save it.
2. **Data:** import `dataset.csv` as a dataset (one row per product page) and assign it
   to the profile. See [Datasets](https://docs.veilus.io/profiles/datasets/).
3. **Schedule:** run it once to check, then add a schedule, for example every 6 hours.
   See [Schedules](https://docs.veilus.io/automation/schedules/).

Each run prints one line, for example:

    RESULT {"checked":2,"changed":[{"url":"https://…","from":51.77,"to":49.99}]}

The first run only records prices, so `changed` is empty.

## Make it yours

| Change | How |
|---|---|
| Your own product pages | Put them in the `URL` column. |
| Where the price is | Put a CSS selector in `SELECTOR` (right-click the price → Inspect). Empty means `.price`. |
| Get a message when a price changes | Add a profile variable `WEBHOOK_URL` with a Slack or Discord webhook URL. |
| Where the last prices are kept | Profile variable `OUT_DIR` (default `~/veilus-solutions`). |

Check each site's terms of service and robots.txt before you monitor it. The example
rows use books.toscrape.com, a site built for scraping practice.
