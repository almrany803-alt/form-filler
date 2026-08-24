// Test across real forms, behaving like a human applicant, and judge by speech.
// Focus: (1) the "JFF platform" detection line per board, (2) a real date field
// (press Fill, expect our day/month/year picker), (3) pick values, never escape.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ps = (f, ...a) => { try { execFileSync("powershell", ["-File", path.join(here, f), ...a], { stdio: "inherit" }); } catch (e) {} };
// Greenhouse boards + direct URLs that expose a date field where possible.
const targets = (process.env.JFF_TARGETS ||
  "gh:monzo,gh:gitlab,gh:brex,gh:figma").split(",");

async function urlFor(t) {
  if (t.startsWith("gh:")) {
    const b = t.slice(3);
    try { const r = await fetch(`https://boards-api.greenhouse.io/v1/boards/${b}/jobs`); const j = (await r.json()).jobs || []; return j.length ? j[0].absolute_url : null; }
    catch { return null; }
  }
  return t; // a raw URL
}

const browser = await chromium.launch({ channel: "chrome", headless: false });
for (const t of targets) {
  const url = await urlFor(t);
  console.log(`\n######## TARGET: ${t} ########`);
  if (!url) { console.log("  [skip] no live url"); continue; }
  console.log("  URL:", url);
  const page = await browser.newPage();
  try { await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 }); await page.bringToFront(); await page.waitForSelector("input", { timeout: 25000 }); }
  catch { console.log("  [skip] did not render"); await page.close(); continue; }

  // source: any date-ish field on this form?
  const dateSel = await page.evaluate(() => {
    const cands = [...document.querySelectorAll('input,[role=combobox]')];
    const hit = cands.find(el => {
      const s = ((el.getAttribute("aria-label")||"") + " " + (el.placeholder||"") + " " + (el.className||"") + " " + (el.getAttribute("aria-haspopup")||"")).toLowerCase();
      return /date|birth|mm\/dd|dd\/mm|calendar/.test(s);
    });
    return hit ? (hit.id ? "#"+CSS.escape(hit.id) : null) : null;
  });
  console.log("  date field on page:", JSON.stringify(dateSel));

  // like a human: text, then a select (pick), then a date if present
  for (const [name, sel, pick] of [
    ["TEXT", 'input#first_name, input[autocomplete="given-name"], input[name="first_name"]', false],
    ["DROPDOWN", 'input.select__input, [role=combobox], select', true],
  ]) {
    const loc = page.locator(sel).first();
    if ((await loc.count()) === 0) { console.log(`  [none] ${name}`); continue; }
    try { await loc.focus(); } catch { continue; }
    await sleep(1200);
    console.log(`  ACTION ${t}: Fill on ${name}`);
    ps("send_nvda_key.ps1", "-Key", "F"); await sleep(6000);
    if (pick) { ps("send_pick.ps1"); await sleep(3500); }
    ps("send_esc.ps1"); await sleep(1000);
  }
  if (dateSel) {
    try {
      await page.locator(dateSel).first().focus(); await sleep(1200);
      console.log(`  ACTION ${t}: Fill on DATE field`);
      ps("send_nvda_key.ps1", "-Key", "F"); await sleep(6000);
      ps("send_pick.ps1"); await sleep(3500);
      ps("send_esc.ps1"); await sleep(1000);
    } catch {}
  }
  await page.close();
}
await browser.close();
console.log("\n######## done: read the SPEECH + JFF platform lines ########");
