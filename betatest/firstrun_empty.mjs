// firstrun_empty.mjs - NO profile saved. Trigger a fill; the add-on must put up
// a critical dialog telling the user to import or enter details, and that must
// be SPOKEN (the bug: it was spoken then cancelled). We trigger and dismiss;
// the workflow asserts the message is in the NVDA log's spoken output.
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
await sleep(5000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(3000);                          // the critical dialog should be up now
execFileSync("powershell", ["-File", path.join(here, "send_escape.ps1")], { stdio: "inherit" }); // dismiss it
await sleep(1000);
await browser.close();
console.log("empty-state: triggered fill with no profile (dialog expected).");
