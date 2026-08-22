# Live NVDA tests

This is the test the sandbox and Wine could not do. It runs a real browser and
real NVDA together, fills a field with the add-on, and checks two things:
what NVDA says, and that the value actually landed in the page. It uses the
current NVDA that guidepup installs, so it also answers the newer-version
question.

## Two ways to run it

### A. On GitHub Actions (real Windows runner, no Windows machine of your own needed)
1. Put this whole project in a GitHub repo.
2. The workflow is already at `.github/workflows/nvda-live.yml`.
3. On GitHub, open Actions, choose "NVDA live fill test", and Run workflow.
4. Read the run log. Send it to me and we fix whatever the first run surfaces.

### B. Locally on your own Windows machine (fastest, since you have Windows)
```
cd live-tests
npx @guidepup/setup     # installs the NVDA and speech-capture pieces
npm install
npx playwright install chromium
pwsh -File install-addon.ps1
npx playwright test
```

## What passing looks like

- "fills the email field ..." goes green: NVDA said "email filled" and the
  field holds test@example.com.
- "declines a bespoke field ..." goes green: NVDA said it could not identify
  the field, and nothing was typed.

## Two things to confirm on the first run (I flagged them in the code)

1. The exact key-send call in `fill.spec.ts` (`nvda.press("NVDA+Shift+f")`),
   against guidepup's NVDA API reference. If that method name differs, it is a
   one-line change.
2. The add-on-into-NVDA path in `install-addon.ps1`. It uses the scratchpad
   approach that worked under Wine; the only unknown is the guidepup NVDA's
   config directory, which the first run will reveal.

## Honest note

I wrote this to guidepup's documented API but could not run it here, because
this sandbox has no Windows and no cloud runner. So the first green is yours.
Once it runs, the fill path is proven on real hardware, which is the last big
unknown in the whole project.
