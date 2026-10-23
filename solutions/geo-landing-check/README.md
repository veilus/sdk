# Geo landing check

Opens your landing pages the way visitors in each country see them: which country the
visit really came from, where redirects end up, the page language, and a screenshot.
Use it to check ads, affiliate links and localized stores before you spend on traffic.

## Run it in 3 steps

1. **Profiles:** one profile per country, each with a proxy in that country.
   See [Proxy setup](https://docs.veilus.io/profiles/proxy/). On each profile, add a
   profile variable `COUNTRY` with the two-letter code (`DE`, `JP`, …).
2. **Script and data:** paste `script.ts` into Veilus Flow → Scripts, import
   `dataset.csv` with your landing pages and assign it to all the profiles.
   See [Datasets](https://docs.veilus.io/profiles/datasets/).
3. **Run:** run the script on all the profiles at once and read each profile's
   `RESULT` line in Run History.

If a profile's proxy exits from the wrong country, that profile fails with
`this profile exits from US, not DE: check its proxy`, so you never compare pages
from the wrong place.

Screenshots are saved in `OUT_DIR/geo-landing-check/`; the `RESULT` line gives that folder once as `outDir` and each page's file name. Veilus keeps the last 4096 characters of a run's output, so keep each profile's list to about 20 pages.

## Make it yours

| Change | How |
|---|---|
| Your landing pages | Put them in the `URL` column. |
| Where screenshots go | Profile variable `OUT_DIR` (default `~/veilus-solutions`). |
| Skip the country check | Leave `COUNTRY` unset; the exit country is still recorded. |
