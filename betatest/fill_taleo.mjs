// fill_taleo.mjs - Taleo (camelCase names, bare field)
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "taleo_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const FILLED = { firstName: "Mohammed", lastName: "Al Omrani", emailAddress: "test@example.com", phoneNumber: "+44 7700 900000" };
const EMPTY = ["mystery"];
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#firstName").focus();
await sleep(5000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(4000);
let ok = true;
console.log("=== taleo form result ===");
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
console.log("taleo: identifiable fields filled; combobox/bare fields declined.");
