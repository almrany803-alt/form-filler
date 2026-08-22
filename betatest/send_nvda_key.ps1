# send_nvda_key.ps1 - press NVDA(Insert)+Shift+A at the OS level, so NVDA's
# global "fill whole form" command fires regardless of which window has focus.
# NVDA's default modifier is Insert (an extended key).

$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Keys -Namespace Win32 -PassThru

$VK_INSERT = 0x2D; $VK_SHIFT = 0x10; $VK_A = 0x41
$DOWN_EXT = 0x1        # KEYEVENTF_EXTENDEDKEY
$UP       = 0x2        # KEYEVENTF_KEYUP
$UP_EXT   = 0x3        # extended + keyup

# press down: Insert, Shift, A
$k::keybd_event($VK_INSERT, 0, $DOWN_EXT, [UIntPtr]::Zero)
$k::keybd_event($VK_SHIFT,  0, 0,         [UIntPtr]::Zero)
$k::keybd_event($VK_A,      0, 0,         [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
# release: A, Shift, Insert
$k::keybd_event($VK_A,      0, $UP,     [UIntPtr]::Zero)
$k::keybd_event($VK_SHIFT,  0, $UP,     [UIntPtr]::Zero)
$k::keybd_event($VK_INSERT, 0, $UP_EXT, [UIntPtr]::Zero)
Write-Host "sent NVDA+Shift+A"
