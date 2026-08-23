// fill_combobox.mjs - fill a REAL custom single-select combobox (APG select-only
// pattern: role=combobox + hidden listbox popup) from the saved profile. Focus
// it, press NVDA+J then F (fill this field), and read data-value to see whether
// the addon opened it, read the options, and chose United Kingdom. If it could
// not, data-value stays empty and the addon should have handed back.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "combobox_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#country").focus();
await sleep(5000);

execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "F"], { stdio: "inherit" });
await sleep(4000);

const val = await page.locator("#country").getAttribute("data-value");
await browser.close();

console.log("=== custom combobox fill result ===");
let ok = true;
const check = (l, got, want) => {
  const p = got === want;
  ok = ok && p;
  console.log(`${p ? "PASS" : "FAIL"}  ${l}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
};
check("custom combobox set to United Kingdom (GB)", val, "GB");

if (!ok) process.exit(1);
console.log("Custom combobox filled from the profile.");
