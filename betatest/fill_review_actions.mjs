// fill_review_actions.mjs - the review list's Edit and Clear (untested before).
// Edit types a value into the first field; Clear empties the second (which we
// pre-fill as an ATS auto-parse would). Changes apply on close.
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
await page.locator("#em").fill("old-wrong@ats.example");   // as an ATS parse would
await page.locator("#fn").focus();
await sleep(5000);
execFileSync("powershell", ["-File", path.join(here, "drive_review_actions.ps1")], { stdio: "inherit" });
await sleep(2000);
const fn = await page.locator("#fn").inputValue();
const em = await page.locator("#em").inputValue();
await browser.close();
console.log("=== review Edit + Clear result ===");
let ok = true;
const check = (l, got, want) => { const p = got === want; ok = ok && p; console.log(`${p?"PASS":"FAIL"}  ${l}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`); };
check("Edit wrote #fn", fn, "Edited Name");
check("Clear emptied #em", em, "");
if (!ok) process.exit(1);
console.log("Review list Edit typed a value in; Clear emptied a field.");
