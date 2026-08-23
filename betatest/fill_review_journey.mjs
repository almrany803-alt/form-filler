// fill_review_journey.mjs - the review journey as the methodical navigator.
// Accessible form: drive ALL FIVE editors (text, chooser, yes/no, date via three
// dropdowns, multi-check). Inaccessible form (no labels, bare select): drive the
// three reliable editors and confirm the chooser still reads a closed dropdown's
// options. Confirm every change from the DOM. The NVDA debug log (uploaded by
// the workflow, -l 10) is read separately to confirm each editor announced.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const urlFor = (f) => "file:///" + path.resolve(here, "..", f).replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();

async function runPhase(file, driver, full) {
  await page.goto(urlFor(file));
  await page.bringToFront();
  await page.locator("#name").focus();
  await sleep(5000);
  execFileSync("powershell", ["-File", path.join(here, driver)], { stdio: "inherit" });
  await sleep(2000);
  const out = {
    name: await page.locator("#name").inputValue(),
    country: await page.locator("#country").inputValue(),
    auth: await page.locator("#auth").isChecked(),
  };
  if (full) {
    out.dob = await page.locator("#dob").inputValue();
    out.skills = await page.locator("#skills").evaluate(
      (el) => Array.from(el.selectedOptions).map((o) => o.value));
  }
  return out;
}

const acc = await runPhase("review_journey.html", "drive_review_journey_full.ps1", true);
const inacc = await runPhase("review_journey_inaccessible.html", "drive_review_journey.ps1", false);
await browser.close();

console.log("=== review journey result (accessible: all 5; inaccessible: 3) ===");
let ok = true;
const check = (l, got, want) => {
  const p = JSON.stringify(got) === JSON.stringify(want);
  ok = ok && p;
  console.log(`${p ? "PASS" : "FAIL"}  ${l}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
};
check("accessible: text editor filled name", acc.name, "Mohammed Alomrani");
check("accessible: chooser set country", acc.country, "GB");
check("accessible: yes/no set auth", acc.auth, true);
check("accessible: date dropdowns set dob", acc.dob, "15/06/2000");
check("accessible: multi-check set skills", acc.skills, ["py", "sql"]);
check("inaccessible: text editor filled name", inacc.name, "Mohammed Alomrani");
check("inaccessible: chooser set country", inacc.country, "GB");
check("inaccessible: yes/no set auth", inacc.auth, true);

if (!ok) process.exit(1);
console.log("Review journey: all five editors on the accessible form, three on the inaccessible.");
