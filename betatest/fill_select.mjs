// fill_select.mjs - native <select> single-field fill. Focus the Country
// dropdown, run "fill this field", expect it lands on United Kingdom.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "select_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#country").focus();
await sleep(4000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "F"], { stdio: "inherit" });
await sleep(4000);
const got = await page.locator("#country").inputValue();
console.log("=== native select result ===");
const want = "United Kingdom";
const ok = got === want;
console.log(`${ok ? "PASS" : "FAIL"}  #country: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
await browser.close();
if (!ok) process.exit(1);
console.log("Native select landed on the saved country.");
