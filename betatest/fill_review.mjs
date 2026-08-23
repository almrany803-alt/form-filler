// fill_review.mjs - open the review list on a form and fill the first field
// (First name) from the profile, then check it landed.
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
await page.locator("#fn").focus();
await sleep(5000);
execFileSync("powershell", ["-File", path.join(here, "drive_review.ps1")], { stdio: "inherit" });
await sleep(2000);
const fn = await page.locator("#fn").inputValue();
await browser.close();
console.log("=== review list result ===");
const pass = fn === "Mohammed";
console.log(`${pass ? "PASS" : "FAIL"}  review filled #fn from profile: expected "Mohammed", got ${JSON.stringify(fn)}`);
if (!pass) process.exit(1);
console.log("Review list opened, listed fields, and filled one from the profile.");
