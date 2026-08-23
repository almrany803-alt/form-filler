param([string]$Action, [string]$Name = "Teaching")
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name ProfMenu -Namespace Win32 -PassThru
$INS=0x2D; $J=0x4A; $P=0x50
function Open-ProfileSub {
  $k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 60
  $k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 900
  # P opens the Profile submenu
  $k::keybd_event($P,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 60; $k::keybd_event($P,0,0x2,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 900
}
Add-Type -AssemblyName System.Windows.Forms
if ($Action -eq "new") {
  Open-ProfileSub
  [System.Windows.Forms.SendKeys]::SendWait("n")          # New profile
  Start-Sleep -Seconds 2
  [System.Windows.Forms.SendKeys]::SendWait($Name); Start-Sleep -Milliseconds 400
  [System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 2   # name -> create
  [System.Windows.Forms.SendKeys]::SendWait("{ESC}"); Start-Sleep -Seconds 2     # close the details dialog
  Write-Host "profile menu: created $Name"
}
elseif ($Action -eq "del") {
  Open-ProfileSub
  [System.Windows.Forms.SendKeys]::SendWait("d")          # Delete profile
  Start-Sleep -Seconds 2
  [System.Windows.Forms.SendKeys]::SendWait("y")          # confirm Yes
  Start-Sleep -Seconds 2
  Write-Host "profile menu: deleted active"
}
elseif ($Action -eq "switch") {
  Open-ProfileSub
  [System.Windows.Forms.SendKeys]::SendWait("{UP}"); Start-Sleep -Milliseconds 500  # move to another version
  [System.Windows.Forms.SendKeys]::SendWait("{ENTER}"); Start-Sleep -Seconds 2
  Write-Host "profile menu: switched"
}
