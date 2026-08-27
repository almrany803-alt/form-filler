"""Copy the add-on and strip ONLY the re-entry focus fix from SectionsDialog, to
recreate the exact bug the navigation machine should catch. The initial
focus-on-open (in __init__) is kept, so the dialog still works the first time,
just like the real bug: it only breaks after you leave a section.

Usage:  python make_buggy.py <src_addon_dir> <dst_addon_dir>
"""

import os
import shutil
import sys

src, dst = sys.argv[1], sys.argv[2]
if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(src, dst)

path = os.path.join(dst, "dialogs.py")
s = open(path, encoding="utf-8").read()

# 1) _onOpen, after a section's entries close: drop the refocus (and its comment)
s = s.replace(
    """        with EntriesDialog(self, self._store, section) as dlg:
            dlg.ShowModal()
        # Put focus back on the list so every section is reachable again, not
        # only the first time. Without this you are stranded on the buttons
        # after leaving a section, with no way back to the list.
        self._list.SetFocus()""",
    """        with EntriesDialog(self, self._store, section) as dlg:
            dlg.ShowModal()""")

# 2) _refresh (covers add / remove / rename): drop the refocus
s = s.replace(
    """        self._list.SetSelection(min(sel, self._list.GetCount() - 1))
        self._list.SetFocus()""",
    """        self._list.SetSelection(min(sel, self._list.GetCount() - 1))""")

open(path, "w", encoding="utf-8").write(s)
print("wrote buggy dialogs (re-entry focus fix removed) ->", path)
