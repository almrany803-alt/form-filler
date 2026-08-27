"""Show the REAL SectionsDialog outside NVDA so pywinauto can drive it.

dialogs.py depends on a few NVDA modules (gui, gui.guiHelper, ui, logHandler)
and on the gettext _() builtin. We stub those with the minimum the dialogs need,
then load the add-on's real dialogs.py (and its real core) as a package so the
relative imports resolve. The dialog we show is the actual one shipped, so its
focus and navigation behaviour is exactly what a user gets.

Usage:  python dialog_harness.py <addon_dir>
where <addon_dir> is the folder that contains dialogs.py and core/.
"""

import builtins
import os
import sys
import tempfile
import types

builtins._ = lambda s: s          # gettext no-op

import wx  # noqa: E402


# --- stub the NVDA modules dialogs.py imports, before importing it ----------
class _BoxSizerHelper:
    def __init__(self, parent, sizer=None, orientation=wx.VERTICAL):
        self.parent = parent
        self.sizer = sizer if sizer is not None else wx.BoxSizer(orientation)

    def addLabeledControl(self, labelText, ctrlClass, **kw):
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self.parent, label=labelText), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        ctrl = ctrlClass(self.parent, **kw)
        row.Add(ctrl, 1)
        self.sizer.Add(row, 0, wx.EXPAND | wx.ALL, 4)
        return ctrl

    def addItem(self, item, **kw):
        self.sizer.Add(item, 0, wx.ALL, 4)
        return item


_guiHelper = types.ModuleType("gui.guiHelper")
_guiHelper.BoxSizerHelper = _BoxSizerHelper

_gui = types.ModuleType("gui")
_gui.guiHelper = _guiHelper
_gui.mainFrame = None
sys.modules["gui"] = _gui
sys.modules["gui.guiHelper"] = _guiHelper

_ui = types.ModuleType("ui")
_ui.message = lambda msg=None: None
sys.modules["ui"] = _ui


class _Log:
    def __getattr__(self, name):
        return lambda *a, **k: None


_logh = types.ModuleType("logHandler")
_logh.log = _Log()
sys.modules["logHandler"] = _logh


def _load_dialogs(addon_dir):
    """Load addon_dir/dialogs.py as jff.dialogs so 'from .core import ...' works."""
    pkg = types.ModuleType("jff")
    pkg.__path__ = [addon_dir]
    sys.modules["jff"] = pkg
    import importlib
    profile = importlib.import_module("jff.core.profile")
    dialogs = importlib.import_module("jff.dialogs")
    return dialogs, profile


def main():
    addon_dir = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join("addon", "globalPlugins", "jobFormFiller")
    dialogs, profile = _load_dialogs(os.path.abspath(addon_dir))

    app = wx.App()
    frame = wx.Frame(None, title="JFF harness")
    _gui.mainFrame = frame
    frame.Show()

    store = profile.ProfileStore(
        os.path.join(tempfile.mkdtemp(), "p.dat"), profile.NullCrypto())
    store.load()
    store.add_profile("P", {"given_name": "Test"})
    store.set_active("P")
    store.add_row("Experience", {"job_title": "Engineer", "employer": "Acme"})
    store.add_row("Experience", {"job_title": "Teacher", "employer": "School"})
    store.add_row("Education", {"qualification": "BSc", "institution": "Uni"})

    dlg = dialogs.SectionsDialog(frame, store)
    dlg.Show()          # modeless so an external driver can act on it
    dlg.Raise()
    app.MainLoop()


if __name__ == "__main__":
    main()
