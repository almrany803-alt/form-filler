import { defineConfig } from "@playwright/test";

// Serve the repo's test_form.html so NVDA reads a real page in a real browser.
export default defineConfig({
  testDir: ".",
  timeout: 120000,          // NVDA start + browser is slow; be generous
  retries: 0,
  workers: 1,               // one screen reader, one browser, in order
  reporter: [["list"]],
  use: {
    headless: false,        // a screen reader needs a real window to read
    baseURL: "http://127.0.0.1:5173",
  },
  webServer: {
    // simple static server for the form; the file lives one level up
    command: "npx --yes http-server .. -p 5173 -s",
    url: "http://127.0.0.1:5173/test_form.html",
    reuseExistingServer: true,
    timeout: 60000,
  },
});
