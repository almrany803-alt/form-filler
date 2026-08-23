$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name RevAct -Namespace Win32 -PassThru
$INS=0x2D; $J=0x4A; $R=0x52
$k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 900
$k::keybd_event($R,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 60; $k::keybd_event($R,0,0x2,[UIntPtr]::Zero)
Start-Sleep -Seconds 3                       # review list open, first item (fn) selected

Add-Type -AssemblyName System.Windows.Forms
# EDIT the first field: Alt+E opens the edit box; type a value; Enter
[System.Windows.Forms.SendKeys]::SendWait("%(e)"); Start-Sleep -Seconds 1
[System.Windows.Forms.SendKeys]::SendWait("Edited Name"); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 1
# move to the second field (email, pre-filled) and CLEAR it: Alt+C
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("%(c)"); Start-Sleep -Seconds 1
# close the review list; changes apply on close
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 2
Write-Host "review actions: edited field 1, cleared field 2"
