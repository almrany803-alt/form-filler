// fill_live_apply.mjs - drive NVDA "fill all" on a REAL, LIVE, PUBLIC job
// application (Greenhouse public board, no account). Finds a currently-open job
// at runtime so it is always live, navigates to the real apply page, presses
// NVDA+J then A, reads what the add-on put into the real inputs, and NEVER
// submits. Dummy identity only.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const board = process.env.JFF_BOARD || "monzo";

// 1. find a live job on this public board (robust to postings expiring)
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

// the real application form must render (guard against a bot wall). Greenhouse
// markup varies (classic #first_name vs newer autocomplete-based inputs), so
// accept any of the known first-name shapes.
const FIRST = 'input#first_name, input[autocomplete="given-name"], input[name="first_name"], input[name="job_application[first_name]"]';
const LAST  = 'input#last_name, input[autocomplete="family-name"], input[name="last_name"], input[name="job_application[last_name]"]';
const EMAIL = 'input#email, input[autocomplete="email"], input[type="email"], input[name="email"], input[name="job_application[email]"]';
const PHONE = 'input#phone, input[autocomplete="tel"], input[type="tel"], input[name="phone"], input[name="job_application[phone]"]';
try {
  await page.waitForSelector(FIRST, { timeout: 30000 });
} catch {
  const title = await page.title();
  const bodyLen = (await page.content()).length;
  console.error("FAIL  the live form did not render (bot wall or layout change).");
  console.error(`  page title: ${JSON.stringify(title)}  body chars: ${bodyLen}`);
  await browser.close();
  process.exit(3);
}
await page.locator(FIRST).first().focus();
await sleep(4000);

// 2. NVDA+J then A = fill all. We never click Apply/Submit.
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(18000);

// 3. read what actually landed in the LIVE inputs
const val = async (sel) => { try { return await page.locator(sel).first().inputValue(); } catch { return "(missing)"; } };
const first = await val(FIRST);
const last  = await val(LAST);
const email = await val(EMAIL);
const phone = await val(PHONE);
const stillOnForm = (await page.locator(FIRST).count()) >= 1;

// --- also exercise the REVIEW feature on the same live form (NVDA+J then R) ---
// Opens the add-on's review dialog over the live page; the log records what it
// collected ("JFF review: collected ..."). We open, wait, Escape, never submit.
try {
  await page.locator(FIRST).first().focus();
  await sleep(1500);
  execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "R"], { stdio: "inherit" });
  await sleep(9000);
  execFileSync("powershell", ["-File", path.join(here, "send_esc.ps1")], { stdio: "inherit" });
  await sleep(1500);
  console.log("  review feature exercised (see NVDA log for what it collected)");
} catch (e) {
  console.log(`  review phase error (non-fatal): ${e}`);
}
await browser.close();

console.log("=== live apply fill result ===");
console.log(`  first_name: ${JSON.stringify(first)}`);
console.log(`  last_name : ${JSON.stringify(last)}`);
console.log(`  email     : ${JSON.stringify(email)}`);
console.log(`  phone     : ${JSON.stringify(phone)}  (informational)`);
console.log(`  still on form (NOT submitted): ${stillOnForm}`);

let ok = stillOnForm;
const check = (l, got) => { const p = !!got && got.trim() && got !== "(missing)"; ok = ok && p; console.log(`${p ? "PASS" : "FAIL"}  ${l}: ${JSON.stringify(got)}`); };
check("first_name filled", first);
check("last_name filled", last);
check("email filled", email);
if (!ok) process.exit(1);
console.log(`Filled the LIVE ${board} application from the profile, no submit.`);
