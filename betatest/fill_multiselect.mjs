// fill_multiselect.mjs - native <select multiple>. Seed has nationality="Saudi".
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "multiselect_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#nat").focus();
await sleep(4000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "F"], { stdio: "inherit" });
await sleep(4000);
const chosen = await page.locator("#nat").evaluate(
  (el) => Array.from(el.selectedOptions).map((o) => o.text));
console.log("=== multi-select result ===");
const ok = chosen.includes("Saudi");
console.log(`${ok ? "PASS" : "FAIL"}  #nat: expected Saudi selected, got ${JSON.stringify(chosen)}`);
await browser.close();
if (!ok) process.exit(1);
console.log("Multi-select: the saved nationality was selected.");
