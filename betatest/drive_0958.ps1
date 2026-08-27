# Live check of the 0.9.58 dialog changes, judged by NVDA speech:
#   - Enter opens a section from the list (no Open button any more)
#   - Add section asks for a Type (combo box)
#   - a Work-typed section's new entry shows Work fields (Job title, Start date)
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name D958 -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A
$k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
Start-Sleep -Seconds 2

Add-Type -AssemblyName System.Windows.Forms
function K($s){ [System.Windows.Forms.SendKeys]::SendWait($s) }

# open the sections list through Edit profile (Profile submenu)
K("p"); Start-Sleep -Seconds 2
K("e"); Start-Sleep -Seconds 1
K("{ENTER}"); Start-Sleep -Seconds 3

# Enter opens the selected section (Education), no Open button
K("{HOME}"); Start-Sleep -Milliseconds 400
K("{DOWN}"); Start-Sleep -Milliseconds 500
K("{ENTER}"); Start-Sleep -Seconds 3        # must open Education entries
K("{ESC}"); Start-Sleep -Seconds 2          # back to the list

# add a section, which now asks for a Type
K("%(a)"); Start-Sleep -Seconds 2           # Add section dialog (Name edit)
K("Testwork"); Start-Sleep -Milliseconds 500
K("{TAB}"); Start-Sleep -Seconds 1          # Type combo box (NVDA reads it)
K("{TAB}"); Start-Sleep -Milliseconds 600   # OK button
K("{ENTER}"); Start-Sleep -Seconds 2        # added; list, Testwork selected

# open the new Work section and add an entry -> Work fields appear
K("{ENTER}"); Start-Sleep -Seconds 2        # open Testwork (empty entries)
K("%(a)"); Start-Sleep -Seconds 3           # Add entry -> Work entry form
K("{TAB}"); Start-Sleep -Milliseconds 800   # Employer
K("{TAB}"); Start-Sleep -Seconds 1          # Start date button
K("{ESC}"); Start-Sleep -Seconds 2          # cancel the entry form
K("{ESC}"); Start-Sleep -Seconds 1          # close the entries list
Write-Host "drove 0.9.58: Enter-open, add typed section, Work entry fields"
