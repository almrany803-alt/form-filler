# install-addon.ps1
# Load the Job Form Filler add-on into the NVDA that guidepup installed, so the
# live test exercises OUR command. guidepup records its NVDA location in the
# registry key HKCU\Software\Guidepup\Nvda.
#
# CONFIRM ON FIRST RUN: the exact config/addons path for the guidepup NVDA.
# Two reliable options, in order of preference:
#   A) Copy the add-on's files into the guidepup NVDA config's "addons" folder.
#   B) Use NVDA's developer scratchpad (drop globalPlugins/jobFormFiller into
#      <config>\scratchpad\globalPlugins and set enableScratchpadDir = True in
#      the config's nvda.ini). This is exactly what worked under Wine.

$ErrorActionPreference = "Stop"

$nvdaRoot = (Get-ItemProperty -Path "HKCU:\Software\Guidepup\Nvda" -ErrorAction SilentlyContinue).'(default)'
Write-Host "guidepup NVDA root (from registry): $nvdaRoot"

# The add-on source in this repo:
$src = Join-Path $PSScriptRoot "..\addon\globalPlugins\jobFormFiller"

# --- Option B: scratchpad (most robust; no add-on-store state to fight) -------
# Adjust $config to the guidepup NVDA's user config directory once confirmed.
$config = Join-Path $env:APPDATA "guidepup\nvda"   # <-- CONFIRM this path
$scratch = Join-Path $config "scratchpad\globalPlugins\jobFormFiller"

New-Item -ItemType Directory -Force -Path (Split-Path $scratch) | Out-Null
Copy-Item -Recurse -Force $src $scratch

$ini = Join-Path $config "nvda.ini"
if (-not (Test-Path $ini)) { New-Item -ItemType File -Force -Path $ini | Out-Null }
if (-not (Select-String -Path $ini -Pattern "enableScratchpadDir" -Quiet)) {
  Add-Content $ini "`n[development]`n`tenableScratchpadDir = True`n"
}

Write-Host "Add-on placed in scratchpad at: $scratch"
Write-Host "If the test cannot find the command, switch to Option A (config addons folder)."
