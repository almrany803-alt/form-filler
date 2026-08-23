// fill_mangled.mjs - the incorrectly-parsed-CV case. An ATS often auto-parses
// the CV and drops a WRONG value into a field. Our fill must NOT clobber it
// (we cannot know it is wrong), must still fill the empty fields, and the
// review list is how the user then sees and fixes the wrong one.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "test_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
// Simulate the ATS auto-parse having put a WRONG email in the field already.
await page.locator("#em").fill("parsed-wrong@ats.example");
await page.locator("#fn").focus();
await sleep(5000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(4000);

const em = await page.locator("#em").inputValue();
const fn = await page.locator("#fn").inputValue();
const ph = await page.locator("#ph").inputValue();
await browser.close();
console.log("=== mangled-parse (do not clobber) result ===");
let ok = true;
const check = (label, got, want) => {
  const pass = got === want; ok = ok && pass;
  console.log(`${pass ? "PASS" : "FAIL"}  ${label}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
};
check("#em pre-filled value left untouched", em, "parsed-wrong@ats.example");
check("#fn empty field still filled", fn, "Mohammed");
check("#ph empty field still filled", ph, "+44 7700 900000");
if (!ok) process.exit(1);
console.log("Wrong pre-filled value was not clobbered; empties filled. Review list fixes the wrong one.");
