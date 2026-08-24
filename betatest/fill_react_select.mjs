// Drive the add-on's fill on a REAL react-select, and judge by react-select's
// actual committed value (its onChange), NOT by what the add-on announces.
// This is the test that catches "typed the search but never selected".
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const url = "file:///" + path.resolve(here, "..", "react_select_form.html").replace(/\\/g, "/");

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(url);
try { await page.waitForSelector("#country", { timeout: 25000 }); }
catch { console.error("FAIL  react-select did not render (CDN blocked?)"); await browser.close(); process.exit(3); }
await page.locator("#country").focus();
await sleep(2500);

// NVDA+J then F = fill this field from the seeded profile's country.
execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", "F"], { stdio: "inherit" });
await sleep(9000);

// GROUND TRUTH: what react-select actually committed (its own onChange value).
const committed = await page.locator("#committed").getAttribute("data-committed");
await browser.close();
console.log("=== react-select fill result ===");
console.log(`  COMMITTED (react-select onChange, the truth): ${JSON.stringify(committed)}`);
const ok = !!committed && committed.trim().length > 0;
console.log(ok ? "PASS  the selection actually committed" : "FAIL  nothing committed (typed but never selected)");
if (!ok) process.exit(1);
