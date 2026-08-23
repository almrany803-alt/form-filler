# dialogs.py - the "My details" form. Named 'dialogs' (not 'gui') on purpose,
# so it does not shadow NVDA's own top-level 'gui' module.
#
# Holds several profiles, each a version (English, Arabic, a teaching CV). You
# pick a version from the selector, edit its fields, create new ones, delete
# ones you no longer want, and import a CV into the version you have selected.

import wx
import gui
from gui import guiHelper
import ui

from .core import cvparse

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
    def __init__(self, parent, store, prefill=None):
        super().__init__(parent, title=_("Job Form Filler: My details"))
        self._store = store
        self._ctrls = {}
        self._current = store.active_name()

        main = wx.BoxSizer(wx.VERTICAL)
        helper = guiHelper.BoxSizerHelper(self, sizer=main)

        # Version selector plus New / Delete.
        self._choice = helper.addLabeledControl(
            _("&Profile (version):"), wx.Choice, choices=self._items())
        self._selectCurrent()
        self._choice.Bind(wx.EVT_CHOICE, self._onChoose)

        row = wx.BoxSizer(wx.HORIZONTAL)
        newBtn = wx.Button(self, label=_("&New profile..."))
        newBtn.Bind(wx.EVT_BUTTON, self._onNew)
        delBtn = wx.Button(self, label=_("De&lete this profile"))
        delBtn.Bind(wx.EVT_BUTTON, self._onDelete)
        row.Add(newBtn, flag=wx.RIGHT, border=8)
        row.Add(delBtn)
        main.Add(row, flag=wx.ALL, border=8)

        for key, label in FIELDS:
            self._ctrls[key] = helper.addLabeledControl(label + ":", wx.TextCtrl)
        self._loadFields(self._current)
        if prefill:
            for k, v in prefill.items():
                if k in self._ctrls and v:
                    self._ctrls[k].SetValue(v)

        importBtn = wx.Button(self, label=_("&Import from CV..."))
        importBtn.Bind(wx.EVT_BUTTON, self._onImport)
        main.Add(importBtn, flag=wx.ALL, border=8)

        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main.Add(buttons, flag=wx.EXPAND | wx.ALL, border=8)

        self.SetSizerAndFit(main)
        self._ctrls["given_name"].SetFocus()

    # --- profile selector ----------------------------------------------------
    def _items(self):
        return list(self._store.profile_names())

    def _selectCurrent(self):
        names = self._store.profile_names()
        if self._current in names:
            self._choice.SetSelection(names.index(self._current))
        elif names:
            self._choice.SetSelection(0)
            self._current = names[0]


    def _refresh(self):
        self._choice.Set(self._items())
        self._selectCurrent()

    def _fieldValues(self):
        return {k: c.GetValue().strip() for k, c in self._ctrls.items()}

    def _loadFields(self, name):
        vals = self._store.get_profile(name) if name else {}
        for k, c in self._ctrls.items():
            c.SetValue(vals.get(k, "") or "")

    def _stash(self):
        if self._current:
            for k, v in self._fieldValues().items():
                self._store.set_field(k, v, profile=self._current)

    def _onChoose(self, evt):
        sel = self._choice.GetStringSelection()
        if sel and sel != self._current:
            self._stash()
            self._current = sel
            self._store.set_active(sel)
            self._loadFields(sel)
            ui.message(_("Profile %s.") % sel)

    def _onNew(self, evt):
        name = self._promptName()
        if not name:
            return
        self._stash()
        self._store.add_profile(name, {})
        self._store.set_active(name)
        self._current = name
        self._refresh()
        self._loadFields(name)
        ui.message(_("New profile %s. Enter or import details.") % name)
        self._ctrls["given_name"].SetFocus()

    def _promptName(self):
        with wx.TextEntryDialog(
                self,
                _("Name for this version (for example English, Arabic, Teaching):"),
                _("New profile")) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return None
            return dlg.GetValue().strip() or None

    def _onDelete(self, evt):
        if not self._current:
            return
        with wx.MessageDialog(
                self,
                _("Delete the profile %s? This cannot be undone.") % self._current,
                _("Delete profile"), wx.YES_NO | wx.ICON_WARNING) as dlg:
            if dlg.ShowModal() != wx.ID_YES:
                return
        gone = self._current
        self._store.delete_profile(gone)
        self._current = self._store.active_name()
        self._refresh()
        self._loadFields(self._current)
        ui.message(_("Deleted %s.") % gone)
        self._ctrls["given_name"].SetFocus()

    # --- CV import -----------------------------------------------------------
    def _onImport(self, evt):
        with wx.FileDialog(
                self, _("Choose your CV"),
                wildcard=_("CV files (*.docx;*.pdf;*.txt)|*.docx;*.pdf;*.txt"),
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fd:
            if fd.ShowModal() != wx.ID_OK:
                return
            path = fd.GetPath()
        try:
            text = cvparse.extract_text(path)
            fields = cvparse.cv_to_fields(cvparse.parse_cv_text(text))
        except Exception:
            log.error("JFF: CV import failed", exc_info=True)
            ui.message(_("Could not read that CV. Check the file and try again."))
            return
        count = 0
        for key, value in fields.items():
            if key in self._ctrls and value:
                self._ctrls[key].SetValue(value)
                count += 1
        log.info("JFF: imported %d field(s) from CV" % count)
        ui.message(_("Imported %d detail(s) from your CV. Review them, then save.")
                   % count)
        self._ctrls["given_name"].SetFocus()

    # --- save ----------------------------------------------------------------
    def commit(self):
        """Write the current form into the active version. If every profile was
        deleted, create one from the form so the details are not lost."""
        if self._current:
            self._stash()
            return
        vals = self._fieldValues()
        if any(vals.values()):
            self._store.add_profile("default", vals)
            self._store.set_active("default")
            self._current = "default"


def edit_details(store, prefill=None):
    """Open the details form. On OK, save to the store. Returns the saved dict,
    or None if cancelled. Must be called on the main (GUI) thread."""
    gui.mainFrame.prePopup()
    saved = None
    try:
        dlg = DetailsDialog(gui.mainFrame, store, prefill=prefill)
        if dlg.ShowModal() == wx.ID_OK:
            dlg.commit()
            try:
                store.save()
                saved = store.get_active()
                ui.message(_("Details saved."))
                log.info("JFF: details saved for profile %r" % store.active_name())
            except Exception:
                log.error("JFF: could not save details", exc_info=True)
                ui.message(_("Could not save your details."))
        dlg.Destroy()
    finally:
        gui.mainFrame.postPopup()
    return saved
