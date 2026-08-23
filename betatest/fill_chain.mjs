// fill_chain.mjs - the import-to-fill chain. The profile is IMPORTED from a CV
// by the workflow (drive_cv.ps1), NOT seeded. We then open a real form, press
// the add-on's fill key, and check the imported values actually landed.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "test_form.html").replace(/\\/g, "/");

// What cv_en.docx holds; this is what should appear in the form after import+fill.
const EXPECT = {
  fn: "Jane",
  em: "jane.doe@example.co.uk",
  ph: "+44 7911 123456",
};

function pressFillKey() {
  execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1")], { stdio: "inherit" });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#fn").focus();
await sleep(5000);
pressFillKey();
await sleep(4000);

const got = {};
for (const id of Object.keys(EXPECT)) got[id] = await page.locator("#" + id).inputValue();
await browser.close();

console.log("=== import-to-fill chain result ===");
let ok = true;
for (const id of Object.keys(EXPECT)) {
  const pass = got[id] === EXPECT[id];
  ok = ok && pass;
  console.log(`${pass ? "PASS" : "FAIL"}  #${id}: expected ${JSON.stringify(EXPECT[id])}, got ${JSON.stringify(got[id])}`);
}
if (!ok) { console.error("Imported values did not fill the form."); process.exit(1); }
console.log("Imported a CV, then filled a real form from it, end to end.");
