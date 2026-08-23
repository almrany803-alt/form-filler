import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "select_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const key = (k) => execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k], { stdio: "inherit" });
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
let ok = true;
async function fillAndCheck(id, want, note) {
  await page.locator("#" + id).focus();
  await sleep(2500);
  key("F");
  await sleep(3500);
  const got = await page.locator("#" + id).inputValue();
  const pass = got === want; ok = ok && pass;
  console.log(`${pass ? "PASS" : "FAIL"}  #${id} (${note}): expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
}
console.log("=== native select: exact, locale alias, and decline ===");
await fillAndCheck("country", "United Kingdom", "same-language exact");
await fillAndCheck("pays", "Royaume-Uni", "locale alias FR");
await fillAndCheck("country3", "France", "no match -> declined, default kept");
await browser.close();
if (!ok) process.exit(1);
console.log("Native selects: exact and locale filled; unmatched declined.");
