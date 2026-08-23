# Close any open menu/dialog by sending Escape.
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name EscKeys -Namespace Win32 -PassThru
$ESC = 0x1B
$k::keybd_event($ESC, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 50
$k::keybd_event($ESC, 0, 0x2, [UIntPtr]::Zero)
