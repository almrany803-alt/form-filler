# Open the add-on menu, choose Review fields, then on the first field use
# "Fill from profile" (the recognised detail is preselected) and close.
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name RevKeys -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A; $R = 0x52
# NVDA+J opens the menu
$k::keybd_event($INS, 0, 0x1, [UIntPtr]::Zero)
$k::keybd_event($J,   0, 0,   [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,   0, 0x2, [UIntPtr]::Zero)
$k::keybd_event($INS, 0, 0x3, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 900
# R selects "Review fields"
$k::keybd_event($R, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($R, 0, 0x2, [UIntPtr]::Zero)
Start-Sleep -Seconds 3            # review dialog opens; list focused, first item selected

Add-Type -AssemblyName System.Windows.Forms
# Alt+F = "Fill from profile" on the selected (first) field
[System.Windows.Forms.SendKeys]::SendWait("%(f)")
Start-Sleep -Seconds 2
# the recognised detail is preselected; Enter accepts it
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Start-Sleep -Seconds 2
# close the review dialog; changes apply on close
[System.Windows.Forms.SendKeys]::SendWait("{ESC}")
Start-Sleep -Seconds 2
Write-Host "review: filled first field from profile"
