// fill_review_journey.mjs - the review journey as the methodical navigator, run
// on TWO forms: an accessible one and an inaccessible one with the same fields.
// In each, open the review list and change one field of each kind through its
// own accessible editor:
//   - name    via the text editor
//   - country via the accessible chooser (the review opens the closed dropdown
//             to read its real options, even when the page exposes none)
//   - auth    via Yes/No
// Then confirm from the DOM that each change landed, on both pages. The NVDA
// debug log (uploaded by the workflow) is read separately to confirm each
// editor announced, since -l 10 captures the speech.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const urlFor = (f) => "file:///" + path.resolve(here, "..", f).replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();

async function runPhase(file) {
  await page.goto(urlFor(file));
  await page.bringToFront();
  await page.locator("#name").focus();     // land NVDA on the form
  await sleep(5000);
  execFileSync("powershell", ["-File", path.join(here, "drive_review_journey.ps1")], { stdio: "inherit" });
  await sleep(2000);
  return {
    name: await page.locator("#name").inputValue(),
    country: await page.locator("#country").inputValue(),   // option value, "GB"
    auth: await page.locator("#auth").isChecked(),
  };
}

const acc = await runPhase("review_journey.html");
const inacc = await runPhase("review_journey_inaccessible.html");
await browser.close();

console.log("=== review journey result (accessible + inaccessible) ===");
let ok = true;
const check = (l, got, want) => {
  const p = got === want;
  ok = ok && p;
  console.log(`${p ? "PASS" : "FAIL"}  ${l}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
};
check("accessible: text editor filled name", acc.name, "Mohammed Alomrani");
check("accessible: chooser set country to United Kingdom", acc.country, "GB");
check("accessible: yes/no set auth", acc.auth, true);
check("inaccessible: text editor filled name", inacc.name, "Mohammed Alomrani");
check("inaccessible: chooser set country to United Kingdom", inacc.country, "GB");
check("inaccessible: yes/no set auth", inacc.auth, true);

if (!ok) process.exit(1);
console.log("Review journey passed on both the accessible and inaccessible forms.");
