# send_pick.ps1 - complete an open editor the way a user does: press Down to
# move onto a real option (past a "- Select -" first row), then Enter to confirm.
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name K2 -Namespace W2 -PassThru
$DOWN=0x28; $RET=0x0D; $UP=0x2
function tap($vk){ $k::keybd_event($vk,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 60; $k::keybd_event($vk,0,$UP,[UIntPtr]::Zero); Start-Sleep -Milliseconds 250 }
tap $DOWN
tap $DOWN
tap $RET
Write-Host "picked an option (Down, Down, Enter)"
