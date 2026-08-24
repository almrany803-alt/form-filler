// applicant_live.mjs — test the add-on the way a blind applicant actually uses
// it, on a REAL live form. The rules that make it applicant-like:
//   1. INSPECT THE SOURCE first, so we know which field types are present.
//   2. NAVIGATE to specific fields the way a user tabs onto them.
//   3. PRESS the add-on's command on each (NVDA+J then F = fill this field).
//   4. JUDGE ONLY BY WHAT NVDA SPEAKS (read from the NVDA log after the run),
//      because that is all the applicant can perceive. The DOM is never proof.
//      Never submit.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const board = process.env.JFF_BOARD || "monzo";

const res = await fetch(`https://boards-api.greenhouse.io/v1/boards/${board}/jobs`);
const jobs = (await res.json()).jobs || [];
if (!jobs.length) { console.error(`No live jobs on ${board}`); process.exit(2); }
const job = jobs[0];
console.log(`Live target: ${board} / ${job.title}`);
console.log(`URL: ${job.absolute_url}`);

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(job.absolute_url, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.bringToFront();
try { await page.waitForSelector("input", { timeout: 30000 }); }
catch { console.error("FAIL form did not render"); await browser.close(); process.exit(3); }

// 1) INSPECT THE SOURCE — enumerate the fields an applicant will meet.
const fields = await page.evaluate(() => {
  const q = 'input:not([type=hidden]), select, textarea, [role="combobox"], [role="checkbox"]';
  return [...document.querySelectorAll(q)].slice(0, 40).map((el) => ({
    tag: el.tagName.toLowerCase(),
    type: el.getAttribute("type") || "",
    role: el.getAttribute("role") || "",
    cls: (el.className || "").toString().slice(0, 28),
    label: (el.getAttribute("aria-label") || el.placeholder || el.name || "").slice(0, 38),
    roledesc: el.getAttribute("aria-roledescription") || "",
  }));
});
console.log("=== SOURCE INSPECTION: fields on the page ===");
for (const f of fields) console.log("  " + JSON.stringify(f));

// focus a field like a user landing on it, then run one add-on command on it.
async function applicantActsOn(name, selector, key) {
  const loc = page.locator(selector).first();
  if ((await loc.count()) === 0) { console.log(`\n[skip] no ${name} on this form`); return; }
  await loc.focus();
  await sleep(1500);
  console.log(`\n=== APPLICANT ACTION: on ${name}, press NVDA+J then ${key} ===`);
  execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", key], { stdio: "inherit" });
  await sleep(6000);
  try { execFileSync("powershell", ["-File", path.join(here, "send_esc.ps1")], { stdio: "inherit" }); } catch {}
  await sleep(1500);
}

// 2+3) DRIVE the add-on on representative field types, one at a time.
await applicantActsOn("a TEXT field (First name)",
  'input#first_name, input[autocomplete="given-name"], input[name="first_name"]', "F");
await applicantActsOn("a CHECKBOX (consent)", 'input[type="checkbox"]', "F");
await applicantActsOn("a DROPDOWN (Country, react-select)",
  'input.select__input, [class*="select__input"], [role="combobox"]', "F");

await browser.close();
console.log("\n=== done: judge by the SPEECH in the NVDA log, not this console ===");
