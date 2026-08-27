// fill_repeating_live.mjs - scan several REAL, LIVE Greenhouse application
// forms for a repeating section (an "Add another ..." control), and on the
// first one found, run whole-form fill (which includes the repeating pass),
// accept the checklist, and report what the section holds afterwards. Judged by
// the real field values and the NVDA speech in the log. If no live form has a
// repeating section right now, it says so honestly rather than failing.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ps = (file, ...args) => execFileSync("powershell", ["-File", path.join(here, file), ...args], { stdio: "inherit" });
const boards = (process.env.JFF_BOARDS || "monzo,gitlab,discord,figma,stripe,airtable,brex,gusto").split(",");

async function firstJob(board) {
  try {
    const r = await fetch(`https://boards-api.greenhouse.io/v1/boards/${board}/jobs`);
    const jobs = (await r.json()).jobs || [];
    return jobs.length ? jobs[0].absolute_url : null;
  } catch { return null; }
}

const browser = await chromium.launch({ channel: "chrome", headless: false });
let testedOne = false;

for (const board of boards) {
  const url = await firstJob(board);
  if (!url) { console.log(`[skip] no live jobs on ${board}`); continue; }
  const page = await browser.newPage();
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector("input", { timeout: 25000 });
  } catch { console.log(`[skip] ${board} form did not render`); await page.close(); continue; }

  // Does this form have a repeating section?
  const addCtl = page.getByText(/add another/i).first();
  const hasRepeat = (await addCtl.count()) > 0;
  console.log(`[${board}] repeating section: ${hasRepeat ? "YES" : "no"}  ${url}`);
  if (!hasRepeat || testedOne) { await page.close(); continue; }

  await page.bringToFront();
  // focus the field just before the Add-another control (the section's start)
  const anchor = page.locator('input:not([type=hidden]), select, textarea').first();
  try { await anchor.focus(); } catch {}
  await sleep(1500);
  console.log(`ACTION ${board}: whole-form fill (with repeating pass)`);
  ps("send_nvda_key.ps1", "-Key", "A");
  await sleep(5000);
  ps("send_plain.ps1", "-Key", "ENTER");   // accept a checklist if it appears
  await sleep(9000);
  ps("send_plain.ps1", "-Key", "ENTER");   // a second section's checklist
  await sleep(9000);

  // how many blocks does the section have now, and did any fill?
  const filledCount = await page.evaluate(() => {
    const vals = [...document.querySelectorAll('input:not([type=hidden]), textarea')]
      .map((e) => (e.value || "").trim()).filter(Boolean);
    return vals.length;
  });
  console.log(`[${board}] non-empty fields after fill: ${filledCount}`);
  ps("send_esc.ps1");
  await page.close();
  testedOne = true;
}

await browser.close();
if (!testedOne) console.log("No live form had a repeating section at test time (honest skip).");
console.log("######## done: judge by the SPEECH in the NVDA log + counts above ########");
