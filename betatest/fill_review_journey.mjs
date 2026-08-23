// fill_review_journey.mjs - the single end-to-end review journey, as the
// methodical navigator. Open the review list on a form that has every control
// kind, and change one field of each kind through its OWN accessible editor:
//   - name    via the text editor
//   - country via the accessible chooser (a dropdown becomes a real chooser)
//   - auth    via Yes/No
// Then confirm from the DOM that each change actually landed. The NVDA debug
// log (uploaded by the workflow) is read separately to confirm each editor
// announced, since -l 10 captures the speech.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "review_journey.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#name").focus();     // land NVDA on the form
await sleep(5000);

execFileSync("powershell", ["-File", path.join(here, "drive_review_journey.ps1")], { stdio: "inherit" });
await sleep(2000);

const name = await page.locator("#name").inputValue();
const country = await page.locator("#country").inputValue();   // option value, "GB"
const auth = await page.locator("#auth").isChecked();
await browser.close();

console.log("=== review journey result ===");
let ok = true;
const check = (l, got, want) => {
  const p = got === want;
  ok = ok && p;
  console.log(`${p ? "PASS" : "FAIL"}  ${l}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
};
check("text editor filled name", name, "Mohammed Alomrani");
check("accessible chooser set country to United Kingdom", country, "GB");
check("yes/no editor set auth", auth, true);

if (!ok) process.exit(1);
console.log("Review journey: text, chooser and yes/no editors all wrote back.");
