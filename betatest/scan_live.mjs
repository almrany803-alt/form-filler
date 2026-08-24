// Open a real application form and run the add-on's Scan (NVDA+J then S). The scan
// is read-only; we then read the per-field report it writes to the NVDA log.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const board = process.env.JFF_BOARD || "monzo";
const r = await fetch(`https://boards-api.greenhouse.io/v1/boards/${board}/jobs`);
const jobs = (await r.json()).jobs || [];
if (!jobs.length) { console.log("no jobs"); process.exit(2); }
const url = jobs[0].absolute_url;
console.log("URL:", url);
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.bringToFront();
await page.waitForSelector("input", { timeout: 25000 });
// put focus in the form, then run Scan
try { await page.locator('input#first_name, input').first().focus(); } catch {}
await sleep(1500);
console.log("ACTION: NVDA+J then S (Scan this form)");
try { execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "S"], { stdio: "inherit" }); } catch {}
await sleep(9000);
await browser.close();
console.log("=== done: read the JFF scan lines from the log ===");
