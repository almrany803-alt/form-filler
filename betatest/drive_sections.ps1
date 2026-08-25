# Drive the sections manager by keyboard on real NVDA:
#   NVDA+J opens the menu; "My sections..." is the last item, so Up wraps to it;
#   Enter opens it; in the sections list Personal(0) Education(1) Experience(2),
#   Down twice selects Experience; Alt+O opens it; NVDA speaks the first entry;
#   Down speaks the second. Everything spoken lands in the NVDA log, which the
#   workflow then checks for the entry summaries.
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Sect -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A
# open the NVDA+J menu
$k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
Start-Sleep -Seconds 2

Add-Type -AssemblyName System.Windows.Forms
# "My sections..." is the last menu item: Up wraps to it, Enter opens it.
[System.Windows.Forms.SendKeys]::SendWait("{UP}"); Start-Sleep -Milliseconds 800
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 3
# sections list: select Experience (Personal, Education, Experience)
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 800
# Open (Alt+O): NVDA speaks the first Experience entry
[System.Windows.Forms.SendKeys]::SendWait("%(o)"); Start-Sleep -Seconds 3
# arrow to the second entry so NVDA speaks it too
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Seconds 2
# close entries, then the sections dialog
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 1
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 1
Write-Host "drove sections: opened Experience, read two entries"
