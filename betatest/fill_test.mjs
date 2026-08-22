// fill_test.mjs - drive the add-on like a human beta tester.
// Open the form in real Chrome, let NVDA settle into browse mode, press the
// add-on's "fill whole form" key, then check what ACTUALLY landed in the boxes.
//
// Run with NVDA already running (started by the workflow) and a profile seeded.

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "test_form.html").replace(/\\/g, "/");

// What the workflow seeded into the profile; this is what we expect to see.
const EXPECT = {
  fn: "Mohammed",
  em: "test@example.com",
  ph: "+44 7700 900000",
  ct: "Bristol",
};

function pressFillKey() {
  execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1")],
               { stdio: "inherit" });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();

// put focus in the page so NVDA is reading this document in browse mode
await page.locator("#fn").focus();
await sleep(5000);          // let NVDA settle (cold start)

pressFillKey();
await sleep(4000);          // let the add-on walk and fill the form

const got = {};
for (const id of Object.keys(EXPECT)) {
  got[id] = await page.locator("#" + id).inputValue();
}
await browser.close();

console.log("=== beta test result ===");
let ok = true;
for (const id of Object.keys(EXPECT)) {
  const pass = got[id] === EXPECT[id];
  ok = ok && pass;
  console.log(`${pass ? "PASS" : "FAIL"}  #${id}: expected ${JSON.stringify(EXPECT[id])}, got ${JSON.stringify(got[id])}`);
}
if (!ok) {
  console.error("Some fields did not land. See the NVDA log dump for JFF lines.");
  process.exit(1);
}
console.log("All seeded fields landed in the form on real Chrome + NVDA.");
