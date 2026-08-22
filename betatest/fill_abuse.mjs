// fill_abuse.mjs - be a chaotic user. Fire the add-on's keys where they make no
// sense, hammer them, press random combos, and then prove a normal fill STILL
// works. If the add-on had crashed or wedged NVDA, the survival fill would fail.

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "test_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const key = (k) => {
  try {
    execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k],
                 { stdio: "inherit" });
  } catch { /* even a failed inject must not stop the abuse run */ }
};

let ok = true;
const check = (label, got, want) => {
  const pass = got === want; ok = ok && pass;
  console.log(`${pass ? "PASS" : "FAIL"}  ${label}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
};

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();

console.log("\n=== abuse 1: single-field fill with focus on non-editable body ===");
await page.locator("body").click();
await sleep(2000);
key("F");                       // no editable field -> should decline, not crash
await sleep(1200);

console.log("=== abuse 2: hammer whole-form fill five times fast ===");
await page.locator("#fn").focus();
await sleep(1500);
for (let i = 0; i < 5; i++) { key("A"); await sleep(500); }
await sleep(1500);

console.log("=== abuse 3: random unbound NVDA+Shift combos ===");
for (const k of ["Z", "Q", "X", "J", "K"]) { key(k); await sleep(350); }
await sleep(1000);

console.log("=== survival: after all that, a normal fill must still work ===");
await page.goto(formUrl);       // fresh, empty form
await page.bringToFront();
await page.locator("#fn").focus();
await sleep(3000);
key("A");
await sleep(3500);
check("survived: #fn fills", await page.locator("#fn").inputValue(), "Mohammed");
check("survived: #em fills", await page.locator("#em").inputValue(), "test@example.com");
check("survived: #ct fills", await page.locator("#ct").inputValue(), "Bristol");

await browser.close();

if (!ok) { console.error("\nAdd-on did NOT survive the abuse (survival fill failed)."); process.exit(1); }
console.log("\nAdd-on survived the abuse: normal fill still works afterwards.");
