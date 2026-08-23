# send_esc.ps1 - press Escape once (to close the review dialog after opening it).
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name KeysEsc -Namespace Win32Esc -PassThru
$ESC = 0x1B; $UP = 0x2
$k::keybd_event($ESC, 0, 0,   [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($ESC, 0, $UP, [UIntPtr]::Zero)
Write-Host "sent Escape"
