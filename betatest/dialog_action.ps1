param([string]$Mode)

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

switch ($Mode) {
  "cancel" {
    # focus opens on the first field (prepopulated). Change it, then cancel.
    [System.Windows.Forms.SendKeys]::SendWait("^(a)CHANGED")
    Start-Sleep -Milliseconds 600
    [System.Windows.Forms.SendKeys]::SendWait("{ESC}")     # cancel the dialog
  }
  "edit" {
    # select all in the first field, type a new value, save with Enter.
    [System.Windows.Forms.SendKeys]::SendWait("^(a)Edited{ENTER}")
  }
  "unicode" {
    # paste an Arabic given name, then an apostrophe+CJK surname, then save.
    Set-Clipboard -Value ([string]([char]0x0645 + [char]0x062D + [char]0x0645 + [char]0x062F))  # محمد
    [System.Windows.Forms.SendKeys]::SendWait("^(a)")
    Start-Sleep -Milliseconds 200
    [System.Windows.Forms.SendKeys]::SendWait("^(v)")
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("{TAB}")
    Set-Clipboard -Value ("O'Brien-" + [char]0x674E)        # O'Brien-李
    [System.Windows.Forms.SendKeys]::SendWait("^(a)")
    Start-Sleep -Milliseconds 200
    [System.Windows.Forms.SendKeys]::SendWait("^(v)")
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")    # save
  }
}
Start-Sleep -Seconds 2
Write-Host "dialog action done: $Mode"
