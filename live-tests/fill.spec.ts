import { nvdaTest as test } from "@guidepup/playwright";
import { expect } from "@playwright/test";

// Capture everything NVDA speaks, so we can assert on it.
test.use({ nvdaStartOptions: { capture: true } });

// This test proves the whole chain the sandbox could not:
//   1. NVDA reads a live field in a real browser,
//   2. our add-on's command fills it,
//   3. the value actually lands in the real DOM,
//   4. NVDA announces the right words.
// It runs on the NVDA guidepup installed (a current release), so it also
// answers the newer-NVDA-version question.

test("fills the email field and announces it, on real NVDA", async ({ page, nvda }) => {
  await page.goto("/test_form.html");

  // Put keyboard focus in the email field (NVDA follows focus).
  await page.locator("#em").focus();

  // Trigger our add-on's command. NVDA+Shift+F is the gesture we registered.
  // VERIFY ON FIRST RUN: the exact key-send call against the guidepup NVDA API
  // (class-nvda reference). If `press` is not the method name, the likely
  // alternative is sending the keys via nvda's keyboard helper.
  await nvda.press("NVDA+Shift+f");

  // What did NVDA actually say?
  const spoken = (await nvda.spokenPhraseLog()).join(" ").toLowerCase();
  expect(spoken).toContain("email filled");

  // Did the value truly land in the DOM? This is the real fill, not just speech.
  await expect(page.locator("#em")).toHaveValue("test@example.com");
});

test("declines a bespoke field instead of guessing", async ({ page, nvda }) => {
  await page.goto("/test_form.html");
  await page.locator("#msg").focus();
  await nvda.press("NVDA+Shift+f");
  const spoken = (await nvda.spokenPhraseLog()).join(" ").toLowerCase();
  expect(spoken).toContain("could not identify");
  await expect(page.locator("#msg")).toHaveValue("");   // nothing typed
});
