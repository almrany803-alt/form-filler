// fill_repeating_ats.mjs - repeating employment section with real-world ATS
// labels (Company, Job Title, From, To; "Add another position"). Proves the
// field matching holds on realistic wording. Seed has three Work entries.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "repeating_ats_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const nvda = (k) => execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k], { stdio: "inherit" });
const plain = (k) => execFileSync("powershell", ["-File", path.join(here, "send_plain.ps1"), "-Key", k], { stdio: "inherit" });
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator(".company").first().focus();
await sleep(4000);
nvda("A");
await sleep(4500);
plain("ENTER");
await sleep(11000);
const comp = await page.locator(".company").evaluateAll((els) => els.map((e) => e.value));
const jts = await page.locator(".jt").evaluateAll((els) => els.map((e) => e.value));
console.log("=== ATS-labelled employment blocks ===");
console.log("companies:", JSON.stringify(comp));
console.log("titles   :", JSON.stringify(jts));
const want = [["Acme Corp", "Senior Engineer"], ["Globex", "Developer"], ["Initech", "Intern"]];
let ok = comp.length >= 3;
for (let i = 0; i < 3; i++) {
  const p = comp[i] === want[i][0] && jts[i] === want[i][1];
  console.log(`${p ? "PASS" : "FAIL"}  block ${i + 1}: expected ${JSON.stringify(want[i])}, got ${JSON.stringify([comp[i], jts[i]])}`);
  ok = ok && p;
}
await browser.close();
if (!ok) process.exit(1);
console.log("Realistic ATS-labelled employment blocks filled from stored entries.");
