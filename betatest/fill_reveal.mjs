// fill_reveal.mjs - a form where choosing "Yes" on work authorization reveals a
// City field that was display:none during the first scan. Confirms the add-on
// re-reads the form after an answer and fills the newly-revealed field.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "reveal_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const nvda = (k) => execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k], { stdio: "inherit" });
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#first_name").focus();
await sleep(4000);
nvda("A");                 // fill all: sets Yes, which reveals City, then fills it
await sleep(10000);
const cityVisible = await page.locator("#extra").isVisible();
const city = (await page.locator("#city").inputValue()).trim();
const waYes = await page.locator("#wa_yes").isChecked();
console.log("=== conditional reveal ===");
console.log("work-auth Yes checked:", waYes, "| City revealed:", cityVisible, "| City value:", JSON.stringify(city));
let ok = waYes && cityVisible && city === "Bristol";
console.log(`${ok ? "PASS" : "FAIL"}  revealed City field filled after answering`);
await browser.close();
if (!ok) process.exit(1);
console.log("The add-on re-read the form after the answer and filled the revealed field.");
