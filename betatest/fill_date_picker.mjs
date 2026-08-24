// Drive the add-on on a REAL date field and a date-picker combobox, judged by the
// field's actual committed value (its input/change event), not the add-on's word.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ps = (f, ...a) => { try { execFileSync("powershell", ["-File", path.join(here, f), ...a], { stdio: "inherit" }); } catch (e) {} };
const url = "file:///" + path.resolve(here, "..", "date_picker_form.html").replace(/\\/g, "/");

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(url);
await page.waitForSelector("#dob", { timeout: 20000 });

// 1) date of birth: Fill should type the formatted date from the profile.
await page.locator("#dob").focus(); await sleep(1500);
console.log("ACTION: Fill on Date of birth (should auto-fill from profile)");
ps("send_nvda_key.ps1", "-Key", "F"); await sleep(6000);
const dob = await page.locator("#committed").getAttribute("data-dob");

// 2) date-picker combobox: Fill should open our day/month/year picker.
await page.locator("#startdate").focus(); await sleep(1500);
console.log("ACTION: Fill on Start date (date-picker combobox, should open our picker)");
ps("send_nvda_key.ps1", "-Key", "F"); await sleep(6000);
ps("send_esc.ps1"); await sleep(1200);

await browser.close();
console.log("=== date field result ===");
console.log(`  DOB committed (field's real value): ${JSON.stringify(dob)}`);
const ok = !!dob && /\d/.test(dob);
console.log(ok ? "PASS  the date typed back into the field" : "FAIL  nothing landed in the date field");
if (!ok) process.exit(1);
