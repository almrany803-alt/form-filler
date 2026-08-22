# dialogs.py - the "My details" form. Named 'dialogs' (not 'gui') on purpose,
# so it does not shadow NVDA's own top-level 'gui' module.
#
# NVDA-dependent (wx + NVDA's gui). Cannot run in the Linux sandbox; written to
# the settings/dialog patterns from clipContentsDesigner and AI-Hub.

import wx
import gui
from gui import guiHelper
import ui

try:
    from logHandler import log
except Exception:
    import logging
    log = logging.getLogger("jobFormFiller")

try:
    _
except NameError:
    def _(s):
        return s

# (profile key, label) in a sensible reading order.
FIELDS = [
    ("given_name", _("First name")),
    ("family_name", _("Last name")),
    ("email", _("Email")),
    ("phone", _("Phone")),
    ("address_line1", _("Address")),
    ("city", _("City")),
    ("postcode", _("Postcode")),
    ("country", _("Country")),
    ("linkedin", _("LinkedIn")),
    ("work_authorisation", _("Work authorisation")),
]


class DetailsDialog(wx.Dialog):
    def __init__(self, parent, values):
        super().__init__(parent, title=_("Job Form Filler: My details"))
        self._ctrls = {}
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        helper = guiHelper.BoxSizerHelper(self, sizer=mainSizer)

        for key, label in FIELDS:
            ctrl = helper.addLabeledControl(label + ":", wx.TextCtrl)
            ctrl.SetValue(values.get(key, "") or "")
            self._ctrls[key] = ctrl

        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        mainSizer.Add(buttons, flag=wx.EXPAND | wx.ALL, border=8)

        self.SetSizerAndFit(mainSizer)
        self._ctrls["given_name"].SetFocus()

    def get_values(self):
        return {k: c.GetValue().strip() for k, c in self._ctrls.items()}


def edit_details(store, prefill=None):
    """Open the details form, prefilled from the store (and optionally from a
    parsed CV). On OK, save to the store. Returns the saved dict, or None if
    cancelled. Must be called on the main (GUI) thread, e.g. a menu handler."""
    values = dict(store.get_active() or {})
    if prefill:
        values.update({k: v for k, v in prefill.items() if v})

    gui.mainFrame.prePopup()
    saved = None
    try:
        dlg = DetailsDialog(gui.mainFrame, values)
        if dlg.ShowModal() == wx.ID_OK:
            vals = dlg.get_values()
            if not store.profile_names():
                store.add_profile("default", vals)
            else:
                for k, v in vals.items():
                    store.set_field(k, v)
            try:
                store.save()
                saved = vals
                ui.message(_("Details saved."))
                log.info("JFF: details saved (%d fields set)"
                         % sum(1 for v in vals.values() if v))
            except Exception:
                log.error("JFF: could not save details", exc_info=True)
                ui.message(_("Could not save your details."))
        dlg.Destroy()
    finally:
        gui.mainFrame.postPopup()
    return saved
