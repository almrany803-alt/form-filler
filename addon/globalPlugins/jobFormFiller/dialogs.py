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

from .core import announce

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
    ("nationality", _("Nationality (optional)")),
    ("date_of_birth", _("Date of birth (optional, YYYY-MM-DD)")),
    ("linkedin", _("LinkedIn")),
    ("work_authorisation", _("Work authorisation")),
]


class DetailsDialog(wx.Dialog):
    def __init__(self, parent, store):
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
                _("Name for this version (for example Work or Teaching):"),
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

    # --- save ----------------------------------------------------------------
    def commit(self):
        """Write the current form into the active version. If there is no
        profile yet, create one from the form so the details are not lost, named
        after the person (or "My details"), never a confusing "default"."""
        if self._current:
            self._stash()
            return
        vals = self._fieldValues()
        if any(vals.values()):
            name = ((vals.get("given_name", "") + " "
                     + vals.get("family_name", "")).strip() or _("My details"))
            self._store.add_profile(name, vals)
            self._store.set_active(name)
            self._current = name


def edit_details(store):
    """Open the details form. On OK, save to the store. Returns the saved dict,
    or None if cancelled. Must be called on the main (GUI) thread."""
    gui.mainFrame.prePopup()
    saved = None
    try:
        dlg = DetailsDialog(gui.mainFrame, store)
        if dlg.ShowModal() == wx.ID_OK:
            dlg.commit()
            try:
                store.save()
                saved = store.get_active()
                ui.message(_("Details saved."))
                log.info("JFF: details saved for profile %r" % store.active_name())
            except Exception:
                log.error("JFF: could not save details", exc_info=True)
                gui.messageBox(_("Could not save your details."),
                               _("Job Form Filler"), wx.OK | wx.ICON_ERROR)
        dlg.Destroy()
    finally:
        gui.mainFrame.postPopup()
    return saved


class ReviewDialog(wx.Dialog):
    """An accessible list over the form you are filling: every field, one per
    line, with its current value or "empty, needs you". Arrow through the list,
    Tab to the actions. Edit types a value in (an accessible box over a field
    that may not be), Fill from profile picks a saved detail, Clear empties it,
    Go to jumps to the field in the page. Changes are applied when you close."""

    def __init__(self, parent, records, profile):
        super().__init__(parent, title=_("Job Form Filler: review fields"))
        self._records = records
        self._profile = profile or {}
        self._pending = {}     # index -> new value ("" means clear)
        self._goto = None

        main = wx.BoxSizer(wx.VERTICAL)
        self._list = wx.ListBox(self, choices=self._lines(), style=wx.LB_SINGLE)
        if records:
            self._list.SetSelection(0)
        main.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (
            (_("&Go to"), self._onGoto),
            (_("&Edit..."), self._onEdit),
            (_("&Fill from profile..."), self._onFill),
            (_("&Clear"), self._onClear),
        ):
            b = wx.Button(self, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            row.Add(b, 0, wx.RIGHT, 6)
        main.Add(row, 0, wx.ALL, 8)
        main.Add(self.CreateButtonSizer(wx.CLOSE), 0, wx.EXPAND | wx.ALL, 8)
        self.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_OK), id=wx.ID_CLOSE)

        self.SetSizerAndFit(main)
        self._list.SetFocus()

    def _shownValue(self, i):
        if i in self._pending:
            return self._pending[i] or _("empty")
        return self._records[i]["value"] or _("empty, needs you")

    def _lines(self):
        return ["{name}: {val}".format(name=r["name"], val=self._shownValue(i))
                for i, r in enumerate(self._records)]

    def _refresh(self, keep):
        self._list.Set(self._lines())
        self._list.SetSelection(keep)

    def _sel(self):
        i = self._list.GetSelection()
        return None if i == wx.NOT_FOUND else i

    def _onGoto(self, evt):
        i = self._sel()
        if i is None:
            return
        self._goto = i
        self.EndModal(wx.ID_OK)

    def _onEdit(self, evt):
        i = self._sel()
        if i is None:
            return
        cur = self._pending.get(i, self._records[i]["value"])
        with wx.TextEntryDialog(
                self, _("Value for {name}:").format(name=self._records[i]["name"]),
                _("Edit field"), value=cur) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            self._pending[i] = dlg.GetValue()
        self._refresh(i)

    def _onFill(self, evt):
        i = self._sel()
        if i is None:
            return
        keys = [k for k in self._profile if self._profile.get(k)]
        if not keys:
            ui.message(_("No saved details to choose from."))
            return
        labels = ["{name}: {val}".format(name=announce.human(k), val=self._profile[k])
                  for k in keys]
        rec_key = self._records[i]["key"]
        preselect = keys.index(rec_key) if rec_key in keys else 0
        with wx.SingleChoiceDialog(
                self,
                _("Which detail goes in {name}?").format(
                    name=self._records[i]["name"]),
                _("Fill from profile"), labels) as dlg:
            dlg.SetSelection(preselect)
            if dlg.ShowModal() != wx.ID_OK:
                return
            self._pending[i] = self._profile[keys[dlg.GetSelection()]]
        self._refresh(i)

    def _onClear(self, evt):
        i = self._sel()
        if i is None:
            return
        self._pending[i] = ""
        self._refresh(i)


def review_fields(records, profile):
    """Open the review list. Returns (changes, goto) where changes is a list of
    (index, new_value) and goto is an index to focus, or None. Main thread only."""
    gui.mainFrame.prePopup()
    try:
        dlg = ReviewDialog(gui.mainFrame, records, profile)
        dlg.ShowModal()
        changes = list(dlg._pending.items())
        goto = dlg._goto
        dlg.Destroy()
    finally:
        gui.mainFrame.postPopup()
    return changes, goto
