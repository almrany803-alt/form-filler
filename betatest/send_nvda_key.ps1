# send_nvda_key.ps1 [-Key A|F] - inject NVDA(Insert)+Shift+<Key> at OS level.
#   A = fill whole form, F = fill current field. NVDA's modifier is Insert.
param([string]$Key = "A")

$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Keys -Namespace Win32 -PassThru

$VK_INSERT = 0x2D; $VK_SHIFT = 0x10
$letters = @{ "A" = 0x41; "F" = 0x46 }
$VK_LET = $letters[$Key.ToUpper()]
$DOWN_EXT = 0x1; $UP = 0x2; $UP_EXT = 0x3

$k::keybd_event($VK_INSERT, 0, $DOWN_EXT, [UIntPtr]::Zero)
$k::keybd_event($VK_SHIFT,  0, 0,         [UIntPtr]::Zero)
$k::keybd_event($VK_LET,    0, 0,         [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($VK_LET,    0, $UP,     [UIntPtr]::Zero)
$k::keybd_event($VK_SHIFT,  0, $UP,     [UIntPtr]::Zero)
$k::keybd_event($VK_INSERT, 0, $UP_EXT, [UIntPtr]::Zero)
Write-Host "sent NVDA+Shift+$Key"
