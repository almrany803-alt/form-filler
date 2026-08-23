// fill_greenhouse.mjs - Greenhouse (bracketed names, autocomplete, Location combobox trap)
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "greenhouse_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const FILLED = { first_name: "Mohammed", last_name: "Al Omrani", email: "test@example.com", phone: "+44 7700 900000" };
const EMPTY = ["loc", "q_li"];
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#first_name").focus();
await sleep(5000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(4000);
let ok = true;
console.log("=== greenhouse form result ===");
for (const [id, want] of Object.entries(FILLED)) {
  const got = await page.locator("#" + id).inputValue();
  const pass = got === want; ok = ok && pass;
  console.log(`${pass ? "PASS" : "FAIL"}  #${id}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
}
for (const id of EMPTY) {
  const got = await page.locator("#" + id).inputValue();
  const pass = got === ""; ok = ok && pass;
  console.log(`${pass ? "PASS" : "FAIL"}  #${id} (declined): expected empty, got ${JSON.stringify(got)}`);
}
await browser.close();
if (!ok) { console.error("Some fields wrong."); process.exit(1); }
console.log("greenhouse: identifiable fields filled; combobox/bare fields declined.");
