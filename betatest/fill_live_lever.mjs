// fill_live_lever.mjs - drive NVDA fill + review on a REAL, LIVE, PUBLIC Lever
// application (no account). Finds a live posting via the Lever public API,
// navigates to the apply page, presses NVDA+J then A (fill all), reads back the
// real inputs, then NVDA+J then R (review) and Escape. NEVER submits. Dummy id.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const candidates = (process.env.JFF_LEVER_CO || "metabase,voltus,supermove,thinkahead,h1,corbalt").split(",");

// 1. find a live Lever posting (robust to postings expiring)
let job = null;
for (const co of candidates) {
  try {
    const res = await fetch(`https://api.lever.co/v0/postings/${co.trim()}?mode=json`);
    if (!res.ok) continue;
    const posts = await res.json();
    if (Array.isArray(posts) && posts.length) {
      const p = posts[0];
      job = { co: co.trim(), title: p.text, url: p.applyUrl || (p.hostedUrl + "/apply") };
      break;
    }
  } catch { /* try next company */ }
}
if (!job) { console.error("No live Lever posting found"); process.exit(2); }
console.log(`Live target: ${job.co} / ${job.title}`);
console.log(`URL: ${job.url}`);

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(job.url, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.bringToFront();

const NAME = 'input[name="name"]';
const EMAIL = 'input[name="email"]';
const PHONE = 'input[name="phone"]';
try {
  await page.waitForSelector(NAME, { timeout: 30000 });
} catch {
  console.error("FAIL  the live Lever form did not render (bot wall or layout change).");
  console.error(`  page title: ${JSON.stringify(await page.title())}`);
  await browser.close(); process.exit(3);
}
await page.locator(NAME).first().focus();
await sleep(4000);

// 2. NVDA+J then A = fill all. Never submit.
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(18000);

// 3. read back the live inputs
const val = async (sel) => { try { return await page.locator(sel).first().inputValue(); } catch { return "(missing)"; } };
const name = await val(NAME);
const email = await val(EMAIL);
const phone = await val(PHONE);
const stillOnForm = (await page.locator(NAME).count()) >= 1;

// 4. exercise the REVIEW feature on the same live form (NVDA+J then R), Escape
try {
  await page.locator(NAME).first().focus();
  await sleep(1500);
  execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "R"], { stdio: "inherit" });
  await sleep(9000);
  execFileSync("powershell", ["-File", path.join(here, "send_esc.ps1")], { stdio: "inherit" });
  await sleep(1500);
  console.log("  review feature exercised (see NVDA log for what it collected)");
} catch (e) { console.log(`  review phase error (non-fatal): ${e}`); }
await browser.close();

console.log("=== live Lever fill result ===");
console.log(`  full name: ${JSON.stringify(name)}   (Lever uses one Full name field)`);
console.log(`  email    : ${JSON.stringify(email)}`);
console.log(`  phone    : ${JSON.stringify(phone)}  (informational)`);
console.log(`  still on form (NOT submitted): ${stillOnForm}`);

let ok = stillOnForm;
const check = (l, got) => { const p = !!got && got.trim() && got !== "(missing)"; ok = ok && p; console.log(`${p ? "PASS" : "FAIL"}  ${l}: ${JSON.stringify(got)}`); };
check("email filled", email);
// name is informational: a single Full name field is a known open question
console.log(`  (full name is informational: does the add-on fill a single Full name field?)`);
if (!ok) process.exit(1);
console.log(`Filled the LIVE ${job.co} Lever application, no submit.`);
