# drive_review_journey_full.ps1 - the methodical navigator drives ALL FIVE
# editors in the review list, each through its own accessible control:
#   Row 1 name    (text)   -> Edit, type, Enter
#   Row 2 country (single) -> Edit, chooser: Down (France -> United Kingdom), Enter
#   Row 3 auth    (yes/no) -> Edit, Up (No -> Yes), Enter
#   Row 4 dob     (date)   -> Edit, three dropdowns: day 15, month June, year
#                             2000, then OK  (-> 15/06/2000 via the DD/MM/YYYY hint)
#   Row 5 skills  (multi)  -> Edit, check Python and SQL, OK
# Deterministic counts; the year count is computed from the current year so the
# test does not drift over time. Changes apply on close.

$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name RevFull -Namespace Win32 -PassThru
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

# Row 1: name (text)
Send("%(e)"); Start-Sleep -Seconds 1
Send("Mohammed Alomrani"); Start-Sleep -Milliseconds 600
Send("{ENTER}"); Start-Sleep -Seconds 2

# Row 2: country (single-choice), France -> United Kingdom
Send("{DOWN}"); Start-Sleep -Milliseconds 800
Send("%(e)"); Start-Sleep -Seconds 2
Send("{DOWN}"); Start-Sleep -Milliseconds 600
Send("{ENTER}"); Start-Sleep -Seconds 2

# Row 3: auth (yes/no), Up lands on Yes
Send("{DOWN}"); Start-Sleep -Milliseconds 800
Send("%(e)"); Start-Sleep -Seconds 1
Send("{UP}"); Start-Sleep -Milliseconds 600
Send("{ENTER}"); Start-Sleep -Seconds 2

# Row 4: dob (date), three dropdowns. Day is focused first.
$yearCount = (Get-Date).Year - 2000 + 1        # steps from "Year" placeholder to 2000
Send("{DOWN}"); Start-Sleep -Milliseconds 800
Send("%(e)"); Start-Sleep -Seconds 2           # date dialog opens, day focused
Send("{DOWN 15}"); Start-Sleep -Milliseconds 500   # day 15
Send("{TAB}"); Start-Sleep -Milliseconds 300
Send("{DOWN 6}"); Start-Sleep -Milliseconds 500    # month June (index 6)
Send("{TAB}"); Start-Sleep -Milliseconds 300
Send("{DOWN $yearCount}"); Start-Sleep -Milliseconds 500   # year 2000
Send("{TAB}"); Start-Sleep -Milliseconds 300       # to OK
Send("{ENTER}"); Start-Sleep -Seconds 2

# Row 5: skills (multi), check Python (index 0) and SQL (index 2)
Send("{DOWN}"); Start-Sleep -Milliseconds 800
Send("%(e)"); Start-Sleep -Seconds 2           # multi-check dialog opens
Send(" "); Start-Sleep -Milliseconds 400        # Space: toggle Python
Send("{DOWN 2}"); Start-Sleep -Milliseconds 400 # move to SQL
Send(" "); Start-Sleep -Milliseconds 400        # Space: toggle SQL
Send("{TAB}"); Start-Sleep -Milliseconds 300    # to OK
Send("{ENTER}"); Start-Sleep -Seconds 2

# Close; changes apply on close
Send("{ESC}"); Start-Sleep -Seconds 5
Write-Host "review journey (full): name, country, auth, date 15/06/2000, skills Python+SQL"
