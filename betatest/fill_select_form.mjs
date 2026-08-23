// fill_select_form.mjs - whole-form fill over text + a native select, plus the
// "don't clobber a real prior selection" rule.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "select_whole_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("#fn").focus();
await sleep(4000);
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "A"], { stdio: "inherit" });
await sleep(6000);
const EXP = { fn: "Mohammed", ln: "Al Omrani", em: "test@example.com",
              country: "United Kingdom", country2: "Germany" };
let ok = true;
console.log("=== whole-form fill: text + select ===");
for (const [id, want] of Object.entries(EXP)) {
  const got = await page.locator("#" + id).inputValue();
  const p = got === want; ok = ok && p;
  const note = id === "country2" ? " (pre-set, must be left)" : "";
  console.log(`${p?"PASS":"FAIL"}  #${id}${note}: expected ${JSON.stringify(want)}, got ${JSON.stringify(got)}`);
}
await browser.close();
if (!ok) process.exit(1);
console.log("Whole-form fill set text and the placeholder dropdown; left the real one.");
