// fill_radio.mjs - radios (native fieldset + ARIA radiogroup) and a checkbox,
// single-field fill. Seed has work_authorisation="Yes".
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "radio_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const key = (k) => execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k], { stdio: "inherit" });
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
let ok = true;
async function fillField(selector) {
  await page.locator(selector).first().focus();
  await sleep(2500);
  key("F");
  await sleep(3500);
}
console.log("=== radios + checkbox ===");
// 1. native fieldset radio -> Yes
await fillField("#wa_yes");
let yes = await page.locator("#wa_yes").isChecked();
console.log(`${yes ? "PASS" : "FAIL"}  native radio: expected Yes checked, got ${yes}`);
ok = ok && yes;
// 2. native checkbox -> checked
await fillField("#consent");
let chk = await page.locator("#consent").isChecked();
console.log(`${chk ? "PASS" : "FAIL"}  checkbox: expected checked, got ${chk}`);
ok = ok && chk;
// 3. ARIA radiogroup -> Yes (aria-checked=true)
await fillField("#ar_yes");
let arc = (await page.locator("#ar_yes").getAttribute("aria-checked")) === "true";
console.log(`${arc ? "PASS" : "FAIL"}  ARIA radio: expected aria-checked true, got ${arc}`);
ok = ok && arc;
await browser.close();
if (!ok) process.exit(1);
console.log("Radios and checkbox set from the saved detail.");
