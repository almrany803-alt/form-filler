// fill_repeating.mjs - a repeating Work history form (one block + "Add another
// role"). Fill all, accept the checklist of stored jobs, and confirm the add-on
// filled the existing block AND added two more, one per stored entry, newest
// first. Seed has three Work entries.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "repeating_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const nvda = (k) => execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k], { stdio: "inherit" });
const plain = (k) => execFileSync("powershell", ["-File", path.join(here, "send_plain.ps1"), "-Key", k], { stdio: "inherit" });

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator(".jt").first().focus();
await sleep(4000);

nvda("A");                 // fill all -> the checklist of Work entries appears
await sleep(4500);
// Accept the checklist. The dialog opens after the main pass, whose timing
// varies on CI, so send Enter at a few points; an early Enter lands harmlessly
// in the page (the fixture has no <form>), a late one dismisses the dialog.
plain("ENTER"); await sleep(2500);
plain("ENTER"); await sleep(2500);
plain("ENTER"); await sleep(9000);        // "Add another" clicks + fills

const jts = await page.locator(".jt").evaluateAll((els) => els.map((e) => e.value));
const emps = await page.locator(".emp").evaluateAll((els) => els.map((e) => e.value));
console.log("=== repeating work blocks ===");
console.log("job titles:", JSON.stringify(jts));
console.log("employers :", JSON.stringify(emps));

const want = [["Senior Engineer", "Acme Corp"], ["Developer", "Globex"], ["Intern", "Initech"]];
let ok = jts.length >= 3;
for (let i = 0; i < 3; i++) {
  const got = [jts[i], emps[i]];
  const p = got[0] === want[i][0] && got[1] === want[i][1];
  console.log(`${p ? "PASS" : "FAIL"}  block ${i + 1}: expected ${JSON.stringify(want[i])}, got ${JSON.stringify(got)}`);
  ok = ok && p;
}
await browser.close();
if (!ok) process.exit(1);
console.log("Three work blocks filled from the stored entries, newest first.");
