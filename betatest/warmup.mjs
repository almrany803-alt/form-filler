// warmup.mjs - absorb the NVDA + Chrome cold-start cost before the real tests.
// Opens the form once and presses the fill key; asserts nothing. This stops the
// recurring "first fill after start is empty" flake from failing a real test.

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "test_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#fn").focus();
await sleep(6000);                       // let the whole stack come fully up
try {
  execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"],
               { stdio: "inherit" });
} catch { /* ignore */ }
await sleep(4000);
await browser.close();
console.log("warm-up done");
