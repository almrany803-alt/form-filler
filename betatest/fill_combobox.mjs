// fill_combobox.mjs - fill a real custom single-select combobox from the saved
// profile, on TWO layouts: the listbox next to the combobox, and the listbox in
// a portal at the end of the body (linked only by aria-controls). Focus it,
// press NVDA+J then F, and read data-value. The portal case proves the
// aria-controls fast-path, since walking the parent tree may not reach the list.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const urlFor = (f) => "file:///" + path.resolve(here, "..", f).replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();

async function fillCombo(file) {
  await page.goto(urlFor(file));
  await page.bringToFront();
  await page.locator("#country").focus();
  await sleep(5000);
  execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "F"], { stdio: "inherit" });
  await sleep(4000);
  return await page.locator("#country").getAttribute("data-value");
}

const plain = await fillCombo("combobox_form.html");
const portal = await fillCombo("combobox_portal_form.html");
await browser.close();

console.log("=== custom combobox fill result ===");
let ok = true;
const check = (l, got, want) => { const p = got === want; ok = ok && p; console.log(`${p ? "PASS" : "FAIL"}  ${l}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`); };
check("plain custom combobox set to GB", plain, "GB");
check("portal custom combobox set to GB (aria-controls)", portal, "GB");
if (!ok) process.exit(1);
console.log("Custom combobox filled from the profile, plain and portal.");
