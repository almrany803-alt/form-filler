param([string]$CvPath)
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name ImpKeys -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A; $I = 0x49
# NVDA+J opens the menu
$k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 900
# I = Import from CV
$k::keybd_event($I,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 60; $k::keybd_event($I,0,0x2,[UIntPtr]::Zero)
Start-Sleep -Seconds 2
Add-Type -AssemblyName System.Windows.Forms
# file picker: type path + open
[System.Windows.Forms.SendKeys]::SendWait($CvPath); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 2
# name dialog: accept the default (from the CV), Enter
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 2
# review dialog opens (already saved); Enter closes/saves
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 2
Write-Host "import via menu: $CvPath"
