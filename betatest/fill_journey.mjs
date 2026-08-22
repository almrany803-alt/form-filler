// fill_journey.mjs - behave like a real user, not a script that jumps straight
// to "fill everything". Two journeys:
//   A) Tab from field to field and fill each one individually (NVDA+Shift+F).
//   B) A two-step application: fill step 1, press Next, fill step 2.

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const url = (f, dir) => "file:///" + path.resolve(dir || here, f).replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const key = (k) => execFileSync("powershell",
  ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k], { stdio: "inherit" });

let ok = true;
const check = (label, got, want) => {
  const pass = got === want;
  ok = ok && pass;
  console.log(`${pass ? "PASS" : "FAIL"}  ${label}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
};

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();

// ---- Journey A: tab through the clean form, filling one field at a time ----
console.log("\n=== Journey A: tab + single-field fill ===");
await page.goto(url("test_form.html", path.resolve(here, "..")));
await page.bringToFront();
await page.locator("body").click();
await sleep(3000);

for (const id of ["fn", "em"]) {
  await page.keyboard.press("Tab");                       // move like a user
  await sleep(700);
  const active = await page.evaluate(() => document.activeElement && document.activeElement.id);
  console.log(`  tabbed to #${active}`);
  key("F");                                               // fill just this field
  await sleep(1500);
}
check("A #fn (tabbed, single-fill)", await page.locator("#fn").inputValue(), "Mohammed");
check("A #em (tabbed, single-fill)", await page.locator("#em").inputValue(), "test@example.com");
// fields we never tabbed to must stay empty
check("A #ph (untouched)", await page.locator("#ph").inputValue(), "");

// ---- Journey B: a two-step application with a Next button ----
console.log("\n=== Journey B: multi-section, press Next between steps ===");
await page.goto(url("multi_form.html"));
await page.bringToFront();
await page.locator("#fn").focus();
await sleep(2500);

key("A");                                                 // fill step 1
await sleep(3500);
check("B step1 #fn", await page.locator("#fn").inputValue(), "Mohammed");
check("B step1 #em", await page.locator("#em").inputValue(), "test@example.com");

await page.locator("#next").click();                      // press Next
await sleep(1500);
key("A");                                                 // fill step 2
await sleep(3500);
check("B step2 #ph", await page.locator("#ph").inputValue(), "+44 7700 900000");
check("B step2 #ct", await page.locator("#ct").inputValue(), "Bristol");

await browser.close();

if (!ok) { console.error("\nJourney test found mismatches."); process.exit(1); }
console.log("\nUser journeys passed: tabbing + single-fill, and multi-section with Next.");
