# Consolidated keyboard drive of the CURRENT dialog (post-0.9.58 layout), five
# behaviours in sequence, judged afterwards by verify_dialog_flow.py on the
# store and by NVDA speech in the log:
#   A  type personal details and save (Enter = OK)
#   B  Cancel (Esc) does NOT save a change
#   C  remove a section (Alt+R, confirm)
#   D  edit an entry's first field (Alt+E, type, Enter)
#   E  create a profile (Profile > New), then delete it (Profile > Delete)
$sig = @"
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
"@
$k = Add-Type -MemberDefinition $sig -Name DFlow -Namespace Win32 -PassThru
$INS = 0x2D; $J = 0x4A
function NvdaJ {
  $k::keybd_event($INS,0,0x1,[UIntPtr]::Zero); $k::keybd_event($J,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 60
  $k::keybd_event($J,0,0x2,[UIntPtr]::Zero); $k::keybd_event($INS,0,0x3,[UIntPtr]::Zero)
  Start-Sleep -Seconds 2
}
Add-Type -AssemblyName System.Windows.Forms
function K($s){ [System.Windows.Forms.SendKeys]::SendWait($s) }

# --- A: personal details by keyboard, saved with Enter ----------------------
NvdaJ; K("p"); Start-Sleep -Seconds 2; K("e"); Start-Sleep -Seconds 3   # sections list, Personal information selected
K("{ENTER}"); Start-Sleep -Seconds 3                                    # Personal information dialog, First name focused
K("^a"); K("Mohammed");        Start-Sleep -Milliseconds 400; K("{TAB}"); Start-Sleep -Milliseconds 500
K("^a"); K("Al Omrani");       Start-Sleep -Milliseconds 400; K("{TAB}"); Start-Sleep -Milliseconds 500
K("^a"); K("test@example.com");Start-Sleep -Milliseconds 400; K("{TAB}"); Start-Sleep -Milliseconds 500
K("^a"); K("07700 900000");    Start-Sleep -Milliseconds 400
K("{ENTER}"); Start-Sleep -Seconds 3                                    # OK -> "Details saved."
Write-Host "A: typed details and pressed Enter"

# --- B: a change followed by Cancel must not save ----------------------------
K("{HOME}"); Start-Sleep -Milliseconds 500
K("{ENTER}"); Start-Sleep -Seconds 3                                    # Personal information again
K("^a"); K("WRONG"); Start-Sleep -Milliseconds 400
K("{ESC}"); Start-Sleep -Seconds 2                                      # Cancel
Write-Host "B: typed WRONG then Cancel"

# --- C: remove the last section (with confirm) --------------------------------
K("{END}"); Start-Sleep -Milliseconds 600                               # last section
K("%(r)"); Start-Sleep -Seconds 2                                       # Remove -> confirm dialog
K("{ENTER}"); Start-Sleep -Seconds 2                                    # Yes
Write-Host "C: removed the last section"

# --- D: edit the first entry of the first section -----------------------------
K("{HOME}"); Start-Sleep -Milliseconds 400
K("{DOWN}"); Start-Sleep -Milliseconds 600                              # first section (Education)
K("{ENTER}"); Start-Sleep -Seconds 3                                    # entries list
K("{HOME}"); Start-Sleep -Milliseconds 500                              # select entry 1
K("%(e)"); Start-Sleep -Seconds 3                                       # Edit -> entry form, first field focused
K("^a"); K("Edited Qualification"); Start-Sleep -Milliseconds 500
K("{ENTER}"); Start-Sleep -Seconds 3                                    # OK
K("{ESC}"); Start-Sleep -Seconds 2                                      # close entries list
K("{ESC}"); Start-Sleep -Seconds 2                                      # close sections list
Write-Host "D: edited entry 1's first field"

# --- E: create a profile, then delete it ------------------------------------
NvdaJ; K("p"); Start-Sleep -Seconds 2; K("n"); Start-Sleep -Seconds 3   # New profile prompt
K("Testprof"); Start-Sleep -Milliseconds 500; K("{ENTER}"); Start-Sleep -Seconds 3
Write-Host "E1: created Testprof"
NvdaJ; K("p"); Start-Sleep -Seconds 2; K("d"); Start-Sleep -Seconds 3   # Delete profile confirm
K("{ENTER}"); Start-Sleep -Seconds 3                                    # Yes
Write-Host "E2: deleted the active profile"
Write-Host "drove the current dialog flow: A save, B cancel, C remove section, D edit entry, E profile create/delete"
