// fill_live_review_actions.mjs - prove the REVIEW editor's per-field actions
// (edit, clear) work on a REAL, LIVE Lever form. Fill all, open the review,
// EDIT row 1 (Full name) to "Edited Name", CLEAR row 2 (Email), close to apply,
// then read the live DOM to confirm both actually took. Never submits.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const candidates = (process.env.JFF_LEVER_CO || "metabase,voltus,supermove,thinkahead,h1").split(",");

let job = null;
for (const co of candidates) {
  try {
    const res = await fetch(`https://api.lever.co/v0/postings/${co.trim()}?mode=json`);
    if (!res.ok) continue;
    const posts = await res.json();
    if (Array.isArray(posts) && posts.length) { const p = posts[0]; job = { co: co.trim(), title: p.text, url: p.applyUrl || (p.hostedUrl + "/apply") }; break; }
  } catch {}
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
try { await page.waitForSelector(NAME, { timeout: 30000 }); }
catch { console.error("FAIL  Lever form did not render"); await browser.close(); process.exit(3); }
const val = async (sel) => { try { return await page.locator(sel).first().inputValue(); } catch { return "(missing)"; } };

await page.locator(NAME).first().focus();
await sleep(4000);

// 1. fill all (Full name -> "Alex Sample", email, phone)
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(18000);
const nameBefore = await val(NAME);
const emailBefore = await val(EMAIL);
console.log(`  before review: name=${JSON.stringify(nameBefore)} email=${JSON.stringify(emailBefore)}`);

// 2. open review, EDIT row 1 to "Edited Name", CLEAR row 2 (email), close-apply
await page.locator(NAME).first().focus();
await sleep(1500);
execFileSync("powershell", ["-File", path.join(here, "drive_review_actions.ps1")], { stdio: "inherit" });
await sleep(5000);

const nameAfter = await val(NAME);
const emailAfter = await val(EMAIL);
const stillOnForm = (await page.locator(NAME).count()) >= 1;
await browser.close();

console.log("=== live review actions result ===");
console.log(`  after: name=${JSON.stringify(nameAfter)} email=${JSON.stringify(emailAfter)}`);
console.log(`  still on form (NOT submitted): ${stillOnForm}`);

let ok = stillOnForm;
const check = (l, cond, detail) => { ok = ok && cond; console.log(`${cond ? "PASS" : "FAIL"}  ${l}${detail ? ": " + detail : ""}`); };
check("EDIT applied on the live form (row 1 Full name now 'Edited Name')", nameAfter === "Edited Name", JSON.stringify(nameAfter));
check("CLEAR applied on the live form (row 2 Email now empty)", emailAfter === "", JSON.stringify(emailAfter));
if (!ok) process.exit(1);
console.log("Review edit + clear both took on the LIVE form, no submit.");
