# drive_review_journey.ps1 - the methodical navigator walks the review list and
# changes one field of each kind through its OWN accessible editor, the way a
# real screen-reader user would: Alt+E to edit, arrow to choose, Enter, Esc to
# close. Deterministic arrow counts, because the fixture's option order is fixed.
#   Row 1 name    (text)   -> Edit, type a value, Enter
#   Row 2 country (single) -> Edit, chooser: Down (France -> United Kingdom), Enter
#   Row 3 auth    (yes/no) -> Edit, Up (No -> Yes), Enter
# Changes apply on close.

$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name RevJourney -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A; $R = 0x52

# NVDA+J then R : open the review list
$k::keybd_event($INS, 0, 0x1, [UIntPtr]::Zero); $k::keybd_event($J, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J, 0, 0x2, [UIntPtr]::Zero); $k::keybd_event($INS, 0, 0x3, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 900
$k::keybd_event($R, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60; $k::keybd_event($R, 0, 0x2, [UIntPtr]::Zero)
Start-Sleep -Seconds 3                          # review list open, row 1 selected

Add-Type -AssemblyName System.Windows.Forms
function Send($s) { [System.Windows.Forms.SendKeys]::SendWait($s) }

# Row 1: name (text) -> Edit, type, Enter
Send("%(e)"); Start-Sleep -Seconds 1
Send("Mohammed Alomrani"); Start-Sleep -Milliseconds 600
Send("{ENTER}"); Start-Sleep -Seconds 2         # back on row 1

# Row 2: country (single-choice) -> down to the row, Edit, chooser Down to
# United Kingdom (France is preselected at index 0), Enter
Send("{DOWN}"); Start-Sleep -Milliseconds 800
Send("%(e)"); Start-Sleep -Seconds 2            # chooser opens and reads options
Send("{DOWN}"); Start-Sleep -Milliseconds 600   # France -> United Kingdom
Send("{ENTER}"); Start-Sleep -Seconds 2

# Row 3: auth (yes/no) -> down to the row, Edit, Up to Yes, Enter. Up from either
# preselect lands on Yes (index 0), so this is robust.
Send("{DOWN}"); Start-Sleep -Milliseconds 800
Send("%(e)"); Start-Sleep -Seconds 1
Send("{UP}"); Start-Sleep -Milliseconds 600     # No -> Yes
Send("{ENTER}"); Start-Sleep -Seconds 2

# Close the review list; changes apply on close
Send("{ESC}"); Start-Sleep -Seconds 4
Write-Host "review journey: typed name, picked United Kingdom, set auth to Yes"
