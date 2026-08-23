// fill_radio_form.mjs - whole-form fill over text, select, radio, checkbox.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "radio_whole_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#fn").focus();
await sleep(4000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(7000);
let ok = true;
console.log("=== whole-form: text + select + radio + checkbox ===");
const fn = await page.locator("#fn").inputValue();
const country = await page.locator("#country").inputValue();
const yes = await page.locator("#wa_yes").isChecked();
const consent = await page.locator("#consent").isChecked();
for (const [name, got, want] of [
  ["#fn", fn, "Mohammed"], ["#country", country, "United Kingdom"],
  ["#wa_yes checked", yes, true], ["#consent checked", consent, true],
]) {
  const p = got === want; ok = ok && p;
  console.log(`${p ? "PASS" : "FAIL"}  ${name}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
}
await browser.close();
if (!ok) process.exit(1);
console.log("Whole-form fill set text, dropdown, radio, and checkbox together.");
