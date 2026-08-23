// fill_async.mjs - async search-box combobox. Seed city="Bristol".
// Checks the addon's real contribution: it types the value, which fires the
// async search so options are ready. (Reading/selecting the async options is
// unreliable via NVDA's cached tree, so the user makes the final pick.)
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "async_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#loc").focus();
await sleep(3000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "F"], { stdio: "inherit" });
await sleep(5000);
const val = await page.locator("#loc").inputValue();
const optCount = await page.locator("#loclist li").count();
const optTexts = await page.locator("#loclist li").allTextContents();
console.log("=== async search-box combobox ===");
console.log(`INFO  input value: ${JSON.stringify(val)}`);
console.log(`INFO  suggestions loaded: ${optCount} -> ${JSON.stringify(optTexts)}`);
const typed = val.includes("Bristol");
const searchFired = optCount > 0;
console.log(`${typed ? "PASS" : "FAIL"}  addon typed the value into the box`);
console.log(`${searchFired ? "PASS" : "FAIL"}  the search fired and options are ready to pick`);
await browser.close();
if (!(typed && searchFired)) process.exit(1);
console.log("Async combobox: value typed, search fired, options ready for the user to pick.");
