# send_nvda_key.ps1 [-Key A|F|D|...] - open the Job Form Filler command layer
# (NVDA+J) and then press the command letter. NVDA's modifier is Insert.
#   A = fill whole form, F = fill current field, D = details.
# Any other letter is a "random key into the layer" (used by the abuse test).
param([string]$Key = "A")

$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name Keys -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A
$DOWN_EXT = 0x1; $UP = 0x2; $UP_EXT = 0x3

# NVDA+J : open the command layer
$k::keybd_event($INS, 0, $DOWN_EXT, [UIntPtr]::Zero)
$k::keybd_event($J,   0, 0,         [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($J,   0, $UP,     [UIntPtr]::Zero)
$k::keybd_event($INS, 0, $UP_EXT, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 900        # let the layer open (and announce)

# the command letter, no modifiers
$VK = [byte][char]([string]$Key).ToUpper()[0]
$k::keybd_event($VK, 0, 0,    [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
$k::keybd_event($VK, 0, $UP,  [UIntPtr]::Zero)
Write-Host "sent NVDA+J then $Key"
