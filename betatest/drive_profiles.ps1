param([string]$Mode = "create")

# open the My details dialog (test gesture NVDA+Shift+D)
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

if ($Mode -eq "create") {
    # Alt+N -> "New profile" -> name entry dialog
    [System.Windows.Forms.SendKeys]::SendWait("%(n)")
    Start-Sleep -Seconds 2
    [System.Windows.Forms.SendKeys]::SendWait("Teaching")
    Start-Sleep -Milliseconds 500
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")   # confirm the name
    Start-Sleep -Seconds 2                                  # focus lands on given name
    [System.Windows.Forms.SendKeys]::SendWait("Sarah")      # type into the new blank version
    Start-Sleep -Milliseconds 500
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")   # OK -> save
    Start-Sleep -Seconds 2
    Write-Host "created profile Teaching (Sarah)"
}
elseif ($Mode -eq "delete") {
    # Alt+L -> "Delete this profile" -> confirm Yes
    [System.Windows.Forms.SendKeys]::SendWait("%(l)")
    Start-Sleep -Seconds 2
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")   # Yes (default) confirms delete
    Start-Sleep -Seconds 2                                  # focus lands on given name (now the remaining version)
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")   # OK -> save
    Start-Sleep -Seconds 2
    Write-Host "deleted the active profile"
}
