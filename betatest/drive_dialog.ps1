# drive_dialog.ps1 - open the "My details" dialog and fill it in by keyboard,
# the way a user would: type a field, Tab to the next, and Enter to save.
# The dialog is opened via a test-only gesture (NVDA+Shift+D) the workflow binds.

$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Keys -Namespace Win32 -PassThru
$INS = 0x2D; $SH = 0x10; $D = 0x44; $DOWN_EXT = 0x1; $UP = 0x2; $UP_EXT = 0x3

# Open the dialog: NVDA(Insert)+Shift+D
$k::keybd_event($INS, 0, $DOWN_EXT, [UIntPtr]::Zero)
$k::keybd_event($SH,  0, 0,         [UIntPtr]::Zero)
$k::keybd_event($D,   0, 0,         [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($D,   0, $UP,     [UIntPtr]::Zero)
$k::keybd_event($SH,  0, $UP,     [UIntPtr]::Zero)
$k::keybd_event($INS, 0, $UP_EXT, [UIntPtr]::Zero)
Start-Sleep -Seconds 3

# Type into the dialog. Focus opens on the first field (first name). Tab moves
# between fields; Enter activates the default OK button and saves.
Add-Type -AssemblyName System.Windows.Forms
$seq = "Mohammed{TAB}Al Omrani{TAB}test@example.com{TAB}07700 900000{TAB}" +
       "12 High Street{TAB}Bristol{TAB}BS1 1AA{TAB}United Kingdom{ENTER}"
[System.Windows.Forms.SendKeys]::SendWait($seq)
Start-Sleep -Seconds 3
Write-Host "drove the My details dialog by keyboard"
