# Full import JOURNEY on real NVDA, the way a first-time user does it: open the
# NVDA+J menu, choose Import from CV (mnemonic i), pick a real CV file in the
# file dialog, accept the profile name, close the details review, then land in
# the sections manager, open Experience, and read its entries. The workflow then
# checks NVDA actually SPOKE the seeded entries. CV path is passed as $args[0].
param([string]$CvPath)

$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Imp -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A
# open the NVDA+J menu
$k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
Start-Sleep -Seconds 2

Add-Type -AssemblyName System.Windows.Forms
# "Import from CV..." (mnemonic i) -> opens the file picker
[System.Windows.Forms.SendKeys]::SendWait("i"); Start-Sleep -Seconds 3
# type the CV path and open it -> the add-on parses and opens the naming dialog
[System.Windows.Forms.SendKeys]::SendWait($CvPath); Start-Sleep -Milliseconds 900
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 6
# accept the default profile name -> the sections list opens directly
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 6
# sections list: Personal, Education, Experience -> select Experience
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 800
# Open (Alt+O): NVDA speaks the first Experience entry
[System.Windows.Forms.SendKeys]::SendWait("%(o)"); Start-Sleep -Seconds 3
# second entry
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Seconds 2
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 1
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 1
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 1
Write-Host "drove import journey: imported CV, opened Experience, read entries"
