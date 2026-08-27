param([string]$Key = "ENTER")
Add-Type -AssemblyName System.Windows.Forms
Start-Sleep -Milliseconds 200
[System.Windows.Forms.SendKeys]::SendWait("{$Key}")
Write-Host "sent plain $Key"
