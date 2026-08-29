// scan_discovery.mjs - run the opt-in Scan action (NVDA+J then S) on a form with
// a custom combobox that no fingerprint covers, and confirm the add-on writes a
// discovery file capturing that unknown widget for review. Read-only: Scan never
// fills or submits.
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
const here = path.dirname(fileURLToPath(import.meta.url));
const formUrl = "file:///" + path.resolve(here, "..", "react_select_form.html").replace(/\\/g, "/");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const nvda = (k) => execFileSync("powershell", ["-File", path.join(here, "send_nvda_key.ps1"), "-Key", k], { stdio: "inherit" });

const browser = await chromium.launch({ channel: "chrome", headless: false });
const page = await browser.newPage();
await page.goto(formUrl);
await page.bringToFront();
await page.locator("input").first().focus();
await sleep(4000);
nvda("S");                 // NVDA+J then S = Scan this form (writes discovery file)
await sleep(7000);

const dirs = [
  path.join(os.homedir(), "Documents", "jobFormFiller"),
  path.join(os.homedir(), "jobFormFiller"),
];
if (process.env.JFF_CFG) dirs.push(path.join(process.env.JFF_CFG, "jobFormFiller"));
let found = null;
for (const d of dirs) {
  try {
    if (!fs.existsSync(d)) continue;
    const files = fs.readdirSync(d).filter((f) => f.startsWith("discovery-") && f.endsWith(".json"));
    if (files.length) { found = path.join(d, files.sort().pop()); break; }
  } catch {}
}
console.log("=== discovery ===");
if (!found) { console.log("FAIL  no discovery file was written"); await browser.close(); process.exit(1); }
const data = JSON.parse(fs.readFileSync(found, "utf-8"));
console.log("discovery file:", found);
console.log("captured fields:", data.fields.length);
const combo = data.fields.find((f) => ((f.signature.role || "").includes("combobox")) || (f.signature.haspopup || ""));
if (combo) console.log("stub:", JSON.stringify(combo.suggested_fingerprint));
const ok = data.fields.length >= 1 && !!combo;
console.log(`${ok ? "PASS" : "FAIL"}  Scan wrote a discovery record for the unknown custom widget`);
await browser.close();
if (!ok) process.exit(1);
console.log("Opt-in Scan captured an unknown widget's structure to a shareable file.");
