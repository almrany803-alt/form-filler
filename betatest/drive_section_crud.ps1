# Add/remove SCENARIOS on real NVDA, driven from a seeded profile (Experience has
# two entries). Story 1 (Guidebook - add): open My sections, Add section, name it
# "Awards", hear it confirmed. Story 2 (Rained-Out - delete): open Experience,
# Remove the first entry, confirm, hear "Removed. 1 entries." and the remaining
# entry. Everything is judged by what NVDA speaks (checked in the workflow).
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Crud -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A
$k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
Start-Sleep -Seconds 2

Add-Type -AssemblyName System.Windows.Forms
# "My sections..." is the last menu item: Up wraps to it, Enter opens it.
[System.Windows.Forms.SendKeys]::SendWait("{UP}"); Start-Sleep -Milliseconds 800
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 3

# --- ADD a section (Alt+A), name it Awards, confirm ---
[System.Windows.Forms.SendKeys]::SendWait("%(a)"); Start-Sleep -Seconds 2
[System.Windows.Forms.SendKeys]::SendWait("Awards"); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 2

# --- REMOVE an entry from Experience ---
# back to the top of the list, then Personal, Education, Experience
[System.Windows.Forms.SendKeys]::SendWait("{HOME}"); Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait("{DOWN}"); Start-Sleep -Milliseconds 700
[System.Windows.Forms.SendKeys]::SendWait("%(o)"); Start-Sleep -Seconds 3   # open Experience
# first entry is selected; Remove (Alt+R) -> confirm dialog -> Yes
[System.Windows.Forms.SendKeys]::SendWait("%(r)"); Start-Sleep -Seconds 2
[System.Windows.Forms.SendKeys]::SendWait("y"); Start-Sleep -Seconds 3      # hear "Removed. 1 entries."
# the remaining entry is now read
Start-Sleep -Seconds 1
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 1
[System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 1
Write-Host "drove crud: added section Awards, removed one Experience entry"
