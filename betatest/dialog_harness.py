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


def _seed(profile):
    import tempfile
    store = profile.ProfileStore(
        os.path.join(tempfile.mkdtemp(), "p.dat"), profile.NullCrypto())
    store.load()
    store.add_profile("P", {"given_name": "Test"})
    store.set_active("P")
    store.add_row("Experience", {"job_title": "Engineer", "employer": "Acme"})
    store.add_row("Experience", {"job_title": "Teacher", "employer": "School"})
    store.add_row("Education", {"qualification": "BSc", "institution": "Uni"})
    return store


def _args():
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    addon_dir = positional[0] if positional else os.path.join(
        "addon", "globalPlugins", "jobFormFiller")
    return os.path.abspath(addon_dir)


def selftest():
    dialogs, profile = _load_dialogs(_args())
    app = wx.App()
    frame = wx.Frame(None, title="JFF harness")
    _gui.mainFrame = frame
    dlg = dialogs.SectionsDialog(frame, _seed(profile))
    print("SELFTEST OK; dialog title:", repr(dlg.GetTitle()))
    lst = dlg._list
    print("list class:", lst.__class__.__name__, "items:", lst.GetCount())


def main():
    dialogs, profile = _load_dialogs(_args())
    app = wx.App()
    frame = wx.Frame(None, title="JFF harness")
    _gui.mainFrame = frame
    frame.Show()
    dlg = dialogs.SectionsDialog(frame, _seed(profile))
    dlg.Show()          # modeless so an external driver can act on it
    dlg.Raise()
    app.MainLoop()


if __name__ == "__main__":
    try:
        if "--selftest" in sys.argv:
            selftest()
        else:
            main()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        try:
            with open("harness_error.log", "w", encoding="utf-8") as f:
                f.write(tb)
        except Exception:
            pass
        sys.stderr.write(tb)
        raise
