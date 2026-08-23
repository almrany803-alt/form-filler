// fill_date.mjs - dates: native input, UK-format text, US-format text.
// Seed date_of_birth="1990-05-20", country="United Kingdom".
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "date_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const key = (k) => execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k], { stdio: "inherit" });
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
let ok = true;
async function fillCheck(id, want, note) {
  await page.locator("#" + id).focus();
  await sleep(2500);
  key("F");
  await sleep(3500);
  const got = await page.locator("#" + id).inputValue();
  const p = got === want; ok = ok && p;
  console.log(`${p ? "PASS" : "FAIL"}  #${id} (${note}): expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
}
console.log("=== dates: native, UK, US ===");
await fillCheck("dob1", "1990-05-20", "native input type=date (ISO)");
await fillCheck("dob2", "20/05/1990", "UK text DD/MM/YYYY");
await fillCheck("dob3", "05/20/1990", "US text MM/DD/YYYY");
await browser.close();
if (!ok) process.exit(1);
console.log("Dates filled in the right format for each field.");
