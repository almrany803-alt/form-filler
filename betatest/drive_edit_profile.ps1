# The path the user actually takes, which the earlier test skipped: reach the
# profile through Edit profile (in the Profile submenu), NOT through My sections.
# It must open the SECTIONS LIST (not the dead-end first-name/last-name form),
# let you open Personal information and come back, reach Education, and show the
# Import from CV button. Judged by NVDA speech.
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name EditP -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A
$k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
Start-Sleep -Seconds 2

Add-Type -AssemblyName System.Windows.Forms
function K($s){ [System.Windows.Forms.SendKeys]::SendWait($s) }
# open the Profile submenu (mnemonic p), then Edit profile (mnemonic e)
K("p"); Start-Sleep -Seconds 2
K("e"); Start-Sleep -Seconds 1
K("{ENTER}"); Start-Sleep -Seconds 3      # must open the SECTIONS LIST

# open Personal information (item 0), then come back (tests the focus fix)
K("{HOME}"); Start-Sleep -Milliseconds 500
K("%(o)"); Start-Sleep -Seconds 3         # details form (first name etc)
K("{ESC}"); Start-Sleep -Seconds 2        # back to the list

# reach Education (item 1) FROM the Edit-profile entry point
K("{HOME}"); Start-Sleep -Milliseconds 400
K("{DOWN}"); Start-Sleep -Milliseconds 500
K("%(o)"); Start-Sleep -Seconds 3         # Education entries
K("{ESC}"); Start-Sleep -Seconds 2

# tab to the Import from CV button so NVDA announces it
K("{TAB}"); Start-Sleep -Milliseconds 800
K("{TAB}"); Start-Sleep -Seconds 2
K("{ESC}"); Start-Sleep -Seconds 1
Write-Host "drove Edit profile -> list -> Personal info -> Education, and reached the Import button"
