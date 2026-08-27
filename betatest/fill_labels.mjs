// fill_labels.mjs - one form, five ways of labelling a field. Confirms the
// add-on can identify a field from a placeholder, an aria-label, an
// aria-labelledby, and a wrapped label, and reports honestly on the
// unassociated-label case (an accessibility anti-pattern we do not require).
// Seed: given_name=Alex, family_name=Sample, email=test@example.com, phone set.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "labels_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const key = (k) => execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k], { stdio: "inherit" });
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
let ok = true;
async function fillField(selector) {
  await page.locator(selector).first().focus();
  await sleep(2500);
  key("F");
  await sleep(3500);
}
const val = async (sel) => (await page.locator(sel).inputValue()).trim();

console.log("=== varied field labelling ===");

await fillField("#f_email");
{ const v = await val("#f_email"); const p = v.includes("test@example.com");
  console.log(`${p ? "PASS" : "FAIL"}  placeholder-only email: got ${JSON.stringify(v)}`); ok = ok && p; }

await fillField("#f_phone");
{ const v = await val("#f_phone"); const p = v.length > 0;
  console.log(`${p ? "PASS" : "FAIL"}  aria-label-only phone: got ${JSON.stringify(v)}`); ok = ok && p; }

await fillField("#f_fn");
{ const v = await val("#f_fn"); const p = v === "Alex";
  console.log(`${p ? "PASS" : "FAIL"}  aria-labelledby first name: got ${JSON.stringify(v)}`); ok = ok && p; }

await fillField("#f_ln");
{ const v = await val("#f_ln"); const p = v === "Sample";
  console.log(`${p ? "PASS" : "FAIL"}  wrapped-label last name: got ${JSON.stringify(v)}`); ok = ok && p; }

await fillField("#f_city");
{ const v = await val("#f_city");
  console.log(`INFO  unassociated 'City' label: got ${JSON.stringify(v)} (accessibility anti-pattern; not required to fill)`); }

await browser.close();
if (!ok) process.exit(1);
console.log("Fields identified from placeholder, aria-label, aria-labelledby and wrapped labels.");
