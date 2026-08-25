# A real applicant journey on real NVDA, the re-entry path that was broken:
# open Education, close it, then reach Experience (the bug), open an entry to
# check the date picker, close, reach Skills, re-open Education AGAIN, then add
# and remove a section. Everything is judged by what NVDA speaks.
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Jrny -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A
$k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
Start-Sleep -Seconds 2

Add-Type -AssemblyName System.Windows.Forms
function K($s){ [System.Windows.Forms.SendKeys]::SendWait($s) }
# open My sections (last menu item)
K("{UP}"); Start-Sleep -Milliseconds 800
K("{ENTER}"); Start-Sleep -Seconds 3

# 1) open Education (index 1), then close it
K("{HOME}"); Start-Sleep -Milliseconds 400
K("{DOWN}"); Start-Sleep -Milliseconds 500
K("%(o)"); Start-Sleep -Seconds 3
K("{ESC}"); Start-Sleep -Seconds 2

# 2) THE RE-ENTRY: reach Experience (index 2) after leaving Education
K("{HOME}"); Start-Sleep -Milliseconds 400
K("{DOWN}{DOWN}"); Start-Sleep -Milliseconds 500
K("%(o)"); Start-Sleep -Seconds 3
# check the date picker: Edit the first entry, read its Start date control, cancel
K("%(e)"); Start-Sleep -Seconds 3
K("{ESC}"); Start-Sleep -Seconds 2
K("{ESC}"); Start-Sleep -Seconds 2

# 3) reach Skills (index 3)
K("{HOME}"); Start-Sleep -Milliseconds 400
K("{DOWN}{DOWN}{DOWN}"); Start-Sleep -Milliseconds 500
K("%(o)"); Start-Sleep -Seconds 3
K("{ESC}"); Start-Sleep -Seconds 2

# 4) re-open Education AGAIN (repeated re-entry)
K("{HOME}"); Start-Sleep -Milliseconds 400
K("{DOWN}"); Start-Sleep -Milliseconds 500
K("%(o)"); Start-Sleep -Seconds 3
K("{ESC}"); Start-Sleep -Seconds 2

# 5) add a section, then remove it
K("%(a)"); Start-Sleep -Seconds 2
K("Certifications"); Start-Sleep -Milliseconds 500
K("{ENTER}"); Start-Sleep -Seconds 2
K("%(r)"); Start-Sleep -Seconds 2
K("y"); Start-Sleep -Seconds 2
K("{ESC}"); Start-Sleep -Seconds 1
Write-Host "drove full journey: Education, Experience(+date picker), Skills, Education again, add+remove section"
