// Test a VARIETY of real live application forms, behaving like a human applicant:
// on each form, inspect the source, then land on fields and press Fill, and when
// a chooser opens, actually pick a value and confirm, never just escape. Judge by
// what NVDA speaks (read from the log afterwards). Never submit.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const boards = (process.env.JFF_BOARDS || "monzo,gitlab,discord,figma").split(",");
const ps = (f, ...a) => { try { execFileSync("powershell", ["-File", path.join(here, f), ...a], { stdio: "inherit" }); } catch (e) {} };

async function firstJob(board) {
  try {
    const r = await fetch(`https://boards-api.greenhouse.io/v1/boards/${board}/jobs`);
    const jobs = (await r.json()).jobs || [];
    return jobs.length ? jobs[0].absolute_url : null;
  } catch { return null; }
}

const browser = await chromium.launch({ channel: "chrome", headless: false });
for (const board of boards) {
  const url = await firstJob(board);
  console.log(`\n######## BOARD: ${board} ########`);
  if (!url) { console.log(`  [skip] no live jobs on ${board}`); continue; }
  console.log(`  URL: ${url}`);
  const page = await browser.newPage();
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.bringToFront();
    await page.waitForSelector("input", { timeout: 25000 });
  } catch { console.log("  [skip] form did not render"); await page.close(); continue; }

  // inspect the source: what field types will a human meet here?
  const kinds = await page.evaluate(() => {
    const q = 'input:not([type=hidden]), select, textarea, [role="combobox"], [role="checkbox"]';
    const c = {};
    for (const el of document.querySelectorAll(q)) {
      const k = el.tagName.toLowerCase() + (el.getAttribute("type") ? ":" + el.getAttribute("type") : "") + (el.getAttribute("role") ? "/" + el.getAttribute("role") : "");
      c[k] = (c[k] || 0) + 1;
    }
    return c;
  });
  console.log("  source field types:", JSON.stringify(kinds));

  // like a human: fill a text field, then Fill + PICK on a select and a checkbox
  const acts = [
    ["TEXT (first name)", 'input#first_name, input[autocomplete="given-name"], input[name="first_name"]', false],
    ["SELECT/dropdown", "select, [role=combobox]", true],
    ["CHECKBOX", 'input[type="checkbox"]', true],
  ];
  for (const [name, sel, pick] of acts) {
    const loc = page.locator(sel).first();
    if ((await loc.count()) === 0) { console.log(`  [none] ${name}`); continue; }
    try { await loc.focus(); } catch { console.log(`  [nofocus] ${name}`); continue; }
    await sleep(1200);
    console.log(`  ACTION ${board}: Fill on ${name}`);
    ps("send_nvda_key.ps1", "-Key", "F");
    await sleep(6000);
    if (pick) { ps("send_pick.ps1"); await sleep(3500); }
    ps("send_esc.ps1");
    await sleep(1200);
  }
  await page.close();
}
await browser.close();
console.log("\n######## done: judge by the SPEECH in the NVDA log ########");
