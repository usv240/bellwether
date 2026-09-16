# Accessibility and quality audit

Measured, not asserted. Lighthouse 13.4.1 against the deployed site, headless Chrome, default mobile throttling.

## Results

| Page | Accessibility | Best practices | SEO | Performance |
|---|---|---|---|---|
| Landing (`/`) | 100 | 100 | 100 | 86 |
| Dashboard (`/app`) | 100 | 100 | 100 | 83 |
| Doctor report (`/report`) | 100 | 100 | 100 | 93 |

Reproduce:

```
npx lighthouse https://d1xfuyog8wiuvf.cloudfront.net/ \
  --only-categories=accessibility,performance,best-practices,seo \
  --chrome-flags="--headless=new"
```

## What the first run found

Accessibility was 100 on all three pages on the first run. Best practices was 96, and the reason was worth more than the score.

**Every API call from the browser was failing with a CORS error, and only a browser could see it.** The Lambda function URL's CORS configuration reflects the request origin, and the FastAPI app also carried CORS middleware, so the response arrived with two `Access-Control-Allow-Origin` headers: `*` and the origin. A browser refuses that outright. `curl` never notices, because `curl` does not enforce CORS, so every command-line check passed and the eighteen server tests passed, while the live dashboard would have shown nothing to a judge.

CORS is now handled by exactly one layer: the function URL in Lambda, the app middleware locally, selected on `AWS_LAMBDA_FUNCTION_NAME`. Verified live: one header, and the dashboard loads.

The remaining item was a missing favicon, which 404'd on every page load and left a blank browser tab. Added.

## Design decisions the audit does not measure

- **Colour is never the only carrier of meaning.** Every tier is a word (`Stable`, `Watch`, `Discuss`, `Quiet day`) as well as a colour, in the badge, the chart tooltip and the report's tier bar.
- **The chart has a text alternative.** The trend is `role="img"` with a label, the underlying numbers are in the Recent days table beneath it, and the report states every notable change in words with dates.
- **Quiet days are hollow, not zero.** A day with too little speech is drawn as an open circle on the axis and breaks the line, so it cannot be misread as a measured value of zero.
- **Progressive disclosure throughout.** Twenty-two info buttons carry plain-language explanations with an optional technical layer and a source link, so no visitor has to leave the page to understand a term, and no paragraph mixes audiences.
- **Both themes are real themes.** Light and dark are defined independently with a three-state toggle (system, light, dark), applied before first paint so there is no flash.
- **The whole landing page is prerendered.** The what, why and how, and every citation, exist in the HTML before any JavaScript runs, so a judge on a slow connection or a failed fetch still sees the entire case. Only the live baseline strip depends on the API.
- **The report prints.** A print stylesheet hides navigation and chrome so the one page a patient carries into an appointment is the one that comes out of the printer.

## Known limit

Lighthouse checks the automatable minority of WCAG. It does not tell us whether the tier language is clear to a worried person, whether the report is readable across a desk in twelve minutes, or whether the spoken check is comfortable to perform. No assistive-technology user, no older adult, and no clinician has tested this build. Those are the claims we are not making.
