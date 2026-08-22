# setup-repo.ps1
# One command to put this project on GitHub and run the live NVDA test,
# using YOUR own GitHub CLI login. No token is typed into a chat or stored
# anywhere but your machine's keychain.
#
# One-time, before running this:
#   winget install GitHub.cli      # if you don't have gh
#   gh auth login                  # authenticates in your keychain, privately
#
# Then, from the project root (the folder containing the "addon" folder):
#   pwsh -File setup-repo.ps1 -RepoName jobformfiller -Private

param(
  [string]$RepoName = "jobformfiller",
  [switch]$Private,
  [switch]$RunWorkflow = $true
)

$ErrorActionPreference = "Stop"

# 0. sanity checks
gh auth status 1>$null 2>$null
if ($LASTEXITCODE -ne 0) { throw "Run 'gh auth login' first (it stores your login privately)." }

# 1. init git if needed
if (-not (Test-Path ".git")) { git init -b main | Out-Null }

# 2. a basic .gitignore so we don't push junk
@"
node_modules/
__pycache__/
*.pyc
live-tests/test-results/
"@ | Set-Content .gitignore

# 3. commit everything here
git add -A
git commit -m "Job Form Filler: add-on, tests, and live NVDA CI" | Out-Null

# 4. create the repo under your account and push (uses your gh login)
$visibility = if ($Private) { "--private" } else { "--public" }
gh repo create $RepoName $visibility --source . --remote origin --push

# 5. optionally trigger the live NVDA workflow
if ($RunWorkflow) {
  Write-Host "Triggering the live NVDA workflow..."
  gh workflow run "nvda-live.yml"
  Start-Sleep -Seconds 4
  gh run list --workflow "nvda-live.yml" --limit 1
  Write-Host "Watch it with:  gh run watch"
}

Write-Host "Done. Repo: $(gh repo view --json url -q .url)"
