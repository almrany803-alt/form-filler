param([string]$CvPath)

# --- open the My details dialog (test gesture NVDA+Shift+D) ---
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Keys -Namespace Win32 -PassThru
$INS = 0x2D; $SH = 0x10; $D = 0x44
$k::keybd_event($INS, 0, 0x1, [UIntPtr]::Zero)
$k::keybd_event($SH,  0, 0,   [UIntPtr]::Zero)
$k::keybd_event($D,   0, 0,   [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($D,   0, 0x2, [UIntPtr]::Zero)
$k::keybd_event($SH,  0, 0x2, [UIntPtr]::Zero)
$k::keybd_event($INS, 0, 0x3, [UIntPtr]::Zero)
Start-Sleep -Seconds 3

Add-Type -AssemblyName System.Windows.Forms

# Alt+I activates the "Import from CV..." button -> opens the file picker.
[System.Windows.Forms.SendKeys]::SendWait("%(i)")
Start-Sleep -Seconds 2

# Type the CV path into the file dialog's filename box and open it.
[System.Windows.Forms.SendKeys]::SendWait($CvPath)
Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Start-Sleep -Seconds 3          # let it read, parse, and populate the fields

# Save the reviewed details (Enter activates the default OK button).
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Start-Sleep -Seconds 2
Write-Host "imported CV: $CvPath"
