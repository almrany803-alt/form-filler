// fill_intl.mjs - accessible foreign-language fields + inaccessible ATS fields.
// Accessible French/German fields must fill by their label; unlabelled fields
// with html attributes fill by those; a field with nothing to go on is declined.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "intl_form.html").replace(/\\/g, "/");

const FILLED = {                       // must be filled from the seeded profile
  fr_fn: "Mohammed", fr_ln: "Al Omrani", fr_em: "test@example.com", fr_ct: "Bristol",
  de_fn: "Mohammed", de_ct: "Bristol",
  ats_ph: "+44 7700 900000", ats_co: "United Kingdom",
};
const EMPTY = ["ats_none"];            // nothing to identify it -> must stay empty

function pressFillKey() {
  execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1")], { stdio: "inherit" });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#fr_fn").focus();
await sleep(5000);
pressFillKey();
await sleep(4000);

let ok = true;
console.log("=== international / inaccessible form result ===");
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
console.log("Accessible foreign-language fields filled; unlabelled-but-tagged filled; bare field declined.");
