# Edit SCENARIO on real NVDA (seeded Experience): open My sections, open
# Experience, Edit the first entry, change the Job title to "Senior Tech
# Volunteer", OK, and hear NVDA announce "Entry updated." and read the updated
# summary. Judged by speech.
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Edit -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A
$k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
Start-Sleep -Seconds 2

Add-Type -AssemblyName System.Windows.Forms
# My sections (last item), open it, open Experience
[System.Windows.Forms.SendKeys]::SendWait("{UP}"); Start-Sleep -Milliseconds 800
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 3
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 700
[System.Windows.Forms.SendKeys]::SendWait("%(o)"); Start-Sleep -Seconds 3
# first entry selected; Edit (Alt+E) -> entry form, focus on Job title
[System.Windows.Forms.SendKeys]::SendWait("%(e)"); Start-Sleep -Seconds 2
# replace the Job title
[System.Windows.Forms.SendKeys]::SendWait("^(a)"); Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("Senior Tech Volunteer"); Start-Sleep -Milliseconds 500
# OK (Enter, since Job title is single-line) -> "Entry updated." then the summary
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 3
# re-read the edited entry
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{UP}"); Start-Sleep -Seconds 2
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 1
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 1
Write-Host "drove edit: changed the first Experience entry's job title"
