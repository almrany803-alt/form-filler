# dialogs.py - the "My details" form. Named 'dialogs' (not 'gui') on purpose,
# so it does not shadow NVDA's own top-level 'gui' module.
#
# Holds several profiles, each a version (English, Arabic, a teaching CV). You
# pick a version from the selector, edit its fields, create new ones, delete
# ones you no longer want, and import a CV into the version you have selected.

import datetime

import wx
import gui
from gui import guiHelper
import ui

from .core import announce, countries

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
    ("date_of_birth", _("Date of birth (optional)")),
    ("linkedin", _("LinkedIn")),
    ("work_authorisation", _("Work authorisation")),
]

# Country and nationality are chosen from the bundled country list, not typed,
# so you pick once cleanly and the value is a canonical name the fill path can
# match in any language.
COUNTRY_FIELDS = {"country", "nationality"}


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
            if key == "date_of_birth":
                days, months, self._dob_years = _dob_lists()
                self._dob_day = helper.addLabeledControl(
                    _("Date of birth, day:"), wx.Choice, choices=days)
                self._dob_month = helper.addLabeledControl(
                    _("Month:"), wx.Choice, choices=months)
                self._dob_year = helper.addLabeledControl(
                    _("Year:"), wx.Choice, choices=self._dob_years)
                for ch in (self._dob_day, self._dob_month, self._dob_year):
                    ch.SetSelection(0)
            elif key in COUNTRY_FIELDS:
                names = countries.country_names()
                ctrl = helper.addLabeledControl(
                    label + ":", wx.ComboBox, choices=[""] + names)
                try:
                    ctrl.AutoComplete(names)   # type "sau" -> Saudi Arabia
                except Exception:
                    pass
                self._ctrls[key] = ctrl
            else:
                self._ctrls[key] = helper.addLabeledControl(
                    label + ":", wx.TextCtrl)
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

    def _dob_get(self):
        if not hasattr(self, "_dob_day"):
            return ""
        return _dob_iso(self._dob_day.GetSelection(),
                        self._dob_month.GetSelection(),
                        self._dob_year.GetSelection(), self._dob_years)

    def _dob_set(self, iso):
        if not hasattr(self, "_dob_day"):
            return
        y, m, d = _dob_split(iso)
        self._dob_day.SetSelection(d if 1 <= d <= 31 else 0)
        self._dob_month.SetSelection(m if 1 <= m <= 12 else 0)
        self._dob_year.SetSelection(
            self._dob_years.index(str(y)) if str(y) in self._dob_years else 0)

    def _fieldValues(self):
        out = {}
        for k, c in self._ctrls.items():
            v = c.GetValue().strip()
            if k in COUNTRY_FIELDS and v:
                v = countries.canonical(v) or v   # "saudi"/"KSA" -> Saudi Arabia
            out[k] = v
        out["date_of_birth"] = self._dob_get()
        return out

    def _loadFields(self, name):
        vals = self._store.get_profile(name) if name else {}
        for k, c in self._ctrls.items():
            c.SetValue(vals.get(k, "") or "")
        self._dob_set(vals.get("date_of_birth", ""))

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


_MONTHS = [_("January"), _("February"), _("March"), _("April"), _("May"),
           _("June"), _("July"), _("August"), _("September"), _("October"),
           _("November"), _("December")]


def _dob_lists():
    """The day, month and year choice lists, each with a placeholder at index 0.
    Shared by the review date dialog and the profile date row so they can never
    drift apart."""
    this_year = datetime.date.today().year
    days = [_("Day")] + ["%d" % d for d in range(1, 32)]
    months = [_("Month")] + _MONTHS
    years = [_("Year")] + [str(y) for y in range(this_year, this_year - 101, -1)]
    return days, months, years


def _dob_split(iso):
    """(year, month, day) as ints from an ISO date, or (0, 0, 0)."""
    try:
        parts = str(iso or "").split("-")
        if len(parts) == 3:
            return int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        pass
    return 0, 0, 0


def _dob_iso(day_sel, month_sel, year_idx, years):
    """ISO date from three choice selections (0 == unset), or '' if incomplete."""
    if day_sel <= 0 or month_sel <= 0 or year_idx <= 0:
        return ""
    return "%s-%02d-%02d" % (years[year_idx], month_sel, day_sel)


class _ComboEntryDialog(wx.Dialog):
    """An accessible editable combo box: type a value, or arrow the options and
    pick one. This is how the review editor makes an inaccessible editable
    combobox usable, in its own idiom, rather than flattening it to a text box."""

    def __init__(self, parent, message, options, value):
        super().__init__(parent, title=_("Type or choose"))
        main = wx.BoxSizer(wx.VERTICAL)
        main.Add(wx.StaticText(self, label=message), 0, wx.ALL, 8)
        self._combo = wx.ComboBox(self, value=value, choices=options,
                                  style=wx.CB_DROPDOWN)
        main.Add(self._combo, 0, wx.EXPAND | wx.ALL, 8)
        main.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0,
                 wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(main)
        self._combo.SetFocus()

    def GetValue(self):
        return self._combo.GetValue()


class _DateDialog(wx.Dialog):
    """Three accessible dropdowns: day, month, year. No format to guess and no
    calendar to trap you. Returns an ISO date; the fill layer then formats it to
    whatever the field on the page actually wants (segments, UK or US text)."""

    def __init__(self, parent, name, iso):
        super().__init__(parent, title=_("Set date"))
        main = wx.BoxSizer(wx.VERTICAL)
        main.Add(wx.StaticText(
            self, label=_("Date for {name}:").format(name=name)), 0, wx.ALL, 8)

        days, months, self._years = _dob_lists()
        self._day = self._labelled(main, _("Day"), days)
        self._month = self._labelled(main, _("Month"), months)
        self._year = self._labelled(main, _("Year"), self._years)

        y, m, d = _dob_split(iso)
        if 1 <= d <= 31:
            self._day.SetSelection(d)
        if 1 <= m <= 12:
            self._month.SetSelection(m)
        if str(y) in self._years:
            self._year.SetSelection(self._years.index(str(y)))

        main.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0,
                 wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(main)
        self._day.SetFocus()

    def _labelled(self, sizer, label, choices):
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label=label + ":"), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        ch = wx.Choice(self, choices=choices)
        ch.SetSelection(0)
        try:
            ch.SetName(label)
        except Exception:
            pass
        row.Add(ch, 0)
        sizer.Add(row, 0, wx.ALL, 6)
        return ch

    @staticmethod
    def _split(iso):
        return _dob_split(iso)

    def GetISO(self):
        return _dob_iso(self._day.GetSelection(), self._month.GetSelection(),
                        self._year.GetSelection(), self._years)


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
            v = self._pending[i]
            if isinstance(v, list):
                return ", ".join(v) if v else _("empty")
            return v or _("empty")
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
        kind = self._records[i].get("kind", "text")
        if kind == "single":
            self._editChoice(i, multiple=False)
        elif kind == "multi":
            self._editChoice(i, multiple=True)
        elif kind == "yesno":
            self._editYesNo(i)
        elif kind == "date":
            self._editDate(i)
        elif kind == "editable":
            self._editEditable(i)
        else:
            self._editText(i)

    def _editText(self, i):
        rec = self._records[i]
        cur = self._pending.get(i, rec["value"])
        if isinstance(cur, list):
            cur = ", ".join(cur)
        with wx.TextEntryDialog(
                self, _("Value for {name}:").format(name=rec["name"]),
                _("Edit field"), value=cur or "") as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            self._pending[i] = dlg.GetValue()
        self._refresh(i)

    def _editChoice(self, i, multiple):
        rec = self._records[i]
        options = rec.get("options") or []
        if not options:
            # We could not read this control's options, so fall back to typing.
            self._editText(i)
            return
        cur = self._pending.get(i, rec["value"])
        if multiple:
            if isinstance(cur, str):
                cur = [c.strip() for c in cur.split(",") if c.strip()]
            preset = [j for j, o in enumerate(options) if o in (cur or [])]
            with wx.MultiChoiceDialog(
                    self, _("Choose any that apply for {name}:").format(
                        name=rec["name"]),
                    _("Choose several"), options) as dlg:
                dlg.SetSelections(preset)
                if dlg.ShowModal() != wx.ID_OK:
                    return
                self._pending[i] = [options[j] for j in dlg.GetSelections()]
        else:
            preset = (options.index(cur)
                      if isinstance(cur, str) and cur in options else 0)
            with wx.SingleChoiceDialog(
                    self, _("Choose one for {name}:").format(name=rec["name"]),
                    _("Choose"), options) as dlg:
                dlg.SetSelection(preset)
                if dlg.ShowModal() != wx.ID_OK:
                    return
                self._pending[i] = options[dlg.GetSelection()]
        self._refresh(i)

    def _editYesNo(self, i):
        rec = self._records[i]
        opts = [_("Yes"), _("No")]
        cur = str(self._pending.get(i, rec["value"]) or "").strip().lower()
        preset = 0 if cur in ("yes", "true", "1", "on", "checked", "y") else 1
        with wx.SingleChoiceDialog(
                self, _("Set {name} to:").format(name=rec["name"]),
                _("Yes or no"), opts) as dlg:
            dlg.SetSelection(preset)
            if dlg.ShowModal() != wx.ID_OK:
                return
            self._pending[i] = opts[dlg.GetSelection()]
        self._refresh(i)

    def _editEditable(self, i):
        rec = self._records[i]
        cur = self._pending.get(i, rec["value"])
        if isinstance(cur, list):
            cur = ", ".join(cur)
        with _ComboEntryDialog(
                self, _("Type a value or choose one for {name}:").format(
                    name=rec["name"]),
                rec.get("options") or [], cur or "") as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            self._pending[i] = dlg.GetValue()
        self._refresh(i)

    def _editDate(self, i):
        rec = self._records[i]
        cur = self._pending.get(i, rec["value"])
        if isinstance(cur, list):
            cur = ""
        with _DateDialog(self, rec["name"], cur or "") as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            iso = dlg.GetISO()
            if iso:                      # ignore an incomplete date, don't clear
                self._pending[i] = iso
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
