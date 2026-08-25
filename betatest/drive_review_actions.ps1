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
Start-Sleep -Seconds 3                       # review list open

Add-Type -AssemblyName System.Windows.Forms
# Reach fields by CONTENT, not position. The review lists rows in form order, and
# this real Lever form has a "Resume/CV" attachment row among the fields, so a
# fixed "row 1 / row 2" would land on the wrong rows. Every row starts with a
# unique letter here (Full, Email, Resume, Twitter), so list type-ahead selects
# reliably regardless of how many attachment rows precede the field.
# Select "Full name" (type f) and EDIT it: Alt+E opens the edit box; type; Enter.
[System.Windows.Forms.SendKeys]::SendWait("f"); Start-Sleep -Milliseconds 700
[System.Windows.Forms.SendKeys]::SendWait("%(e)"); Start-Sleep -Seconds 1
[System.Windows.Forms.SendKeys]::SendWait("Edited Name"); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 1
# Select "Email" (type e) and CLEAR it: Alt+C.
[System.Windows.Forms.SendKeys]::SendWait("e"); Start-Sleep -Milliseconds 700
[System.Windows.Forms.SendKeys]::SendWait("%(c)"); Start-Sleep -Seconds 1
# close the review list; changes apply on close
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 2
Write-Host "review actions: edited Full name, cleared Email"
