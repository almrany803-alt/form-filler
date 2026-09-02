# dialogs.py - the "My details" form. Named 'dialogs' (not 'gui') on purpose,
# so it does not shadow NVDA's own top-level 'gui' module.
#
# Holds several profiles, each a version (English, Arabic, a teaching CV). You
# pick a version from the selector, edit its fields, create new ones, delete
# ones you no longer want, and import a CV into the version you have selected.

import datetime
import re

import wx
import gui
from gui import guiHelper
import ui

from .core import announce, countries, cvparse, profile

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


_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _is_date_field(field):
    """Career dates (start_date, end_date, and any *_date) use the month/year
    picker instead of a free-text box."""
    return field == "date" or field.endswith("_date")


def _parse_monthyear(value):
    """(present, month 1-12 or 0, year int or 0) from a stored date string like
    'Sep 2023', 'September 2023', '2020' or 'present'."""
    v = (value or "").strip()
    if re.search(r"present|current|ongoing|\bnow\b|to date|till date", v, re.I):
        return True, 0, 0
    month = 0
    low = v.lower()
    for i, name in enumerate(_MONTHS):
        if name.lower()[:3] in low:
            month = i + 1
            break
    ym = re.search(r"(?:19|20)\d\d", v)
    return False, month, int(ym.group(0)) if ym else 0


def _format_monthyear(month, year):
    """A readable 'Sep 2023', or just the year, or '' (so summaries stay tidy)."""
    if year and 1 <= month <= 12:
        return "%s %d" % (_MONTH_ABBR[month - 1], year)
    if year:
        return str(year)
    return ""


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


class _MonthYearDialog(wx.Dialog):
    """A career-date picker in the same accessible dropdown idiom as the date of
    birth, fitted to CV dates: a 'When' choice at the top whose easy-to-reach
    first options are Present (ongoing) and No date, then Month and Year
    dropdowns for a specific date. Returns a readable 'Sep 2023', 'present', or
    '' so the entry summaries stay tidy. No day, because jobs and courses do not
    have one, and no free text to guess."""

    def __init__(self, parent, name, value):
        super().__init__(parent, title=_("Set date"))
        main = wx.BoxSizer(wx.VERTICAL)
        main.Add(wx.StaticText(
            self, label=_("Date for {name}:").format(name=name)), 0, wx.ALL, 8)

        present, month, year = _parse_monthyear(value)
        this_year = datetime.date.today().year
        # future years too, for an expected graduation date.
        self._years = [_("Year")] + [
            str(y) for y in range(this_year + 8, this_year - 71, -1)]

        self._status = self._labelled(main, _("When"), [
            _("Present (ongoing)"), _("No date"), _("A specific month and year")])
        self._month = self._labelled(main, _("Month"), [_("Month")] + _MONTHS)
        self._year = self._labelled(main, _("Year"), self._years)

        self._status.SetSelection(0 if present else 2)
        if month:
            self._month.SetSelection(month)
        if year and str(year) in self._years:
            self._year.SetSelection(self._years.index(str(year)))

        main.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0,
                 wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(main)
        self._status.SetFocus()

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

    def GetValue(self):
        s = self._status.GetSelection()
        if s == 0:
            return "present"
        if s == 1:
            return ""
        ysel = self._year.GetSelection()
        year = int(self._years[ysel]) if ysel > 0 else 0
        return _format_monthyear(self._month.GetSelection(), year)


def edit_field(parent, name, kind, options, current):
    """Show the accessible editor matching a field's kind and return the value
    the user chose, or None if they cancelled. Shared by the review dialog (per
    row) and the 'Fill this field' command (the focused field), so both offer
    the identical editor and there is a single implementation. Covers every kind
    the add-on supports: yes/no, single-choice, multi-choice, editable combobox,
    date, and plain text."""
    options = options or []
    if isinstance(current, list):
        current = "" if kind == "date" else ", ".join(current)
    current = str(current or "")

    if kind == "yesno":
        opts = [_("Yes"), _("No")]
        c = current.strip().lower()
        preset = 0 if c in ("yes", "true", "1", "on", "checked", "y") else 1
        with wx.SingleChoiceDialog(
                parent, _("Set {name} to:").format(name=name),
                _("Yes or no"), opts) as dlg:
            dlg.SetSelection(preset)
            return opts[dlg.GetSelection()] if dlg.ShowModal() == wx.ID_OK else None

    if kind == "multi" and options:
        curlist = [c.strip() for c in current.split(",") if c.strip()]
        preset = [j for j, o in enumerate(options) if o in curlist]
        with wx.MultiChoiceDialog(
                parent, _("Choose any that apply for {name}:").format(name=name),
                _("Choose several"), options) as dlg:
            dlg.SetSelections(preset)
            return ([options[j] for j in dlg.GetSelections()]
                    if dlg.ShowModal() == wx.ID_OK else None)

    if kind == "single" and options:
        preset = options.index(current) if current in options else 0
        with wx.SingleChoiceDialog(
                parent, _("Choose one for {name}:").format(name=name),
                _("Choose"), options) as dlg:
            dlg.SetSelection(preset)
            return (options[dlg.GetSelection()]
                    if dlg.ShowModal() == wx.ID_OK else None)

    if kind == "editable":
        with _ComboEntryDialog(
                parent, _("Type a value or choose one for {name}:").format(name=name),
                options, current) as dlg:
            return dlg.GetValue() if dlg.ShowModal() == wx.ID_OK else None

    if kind == "date":
        with _DateDialog(parent, name, current) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return None
            iso = dlg.GetISO()
            return iso or None      # ignore an incomplete date, don't clear

    # text: the default, and where single/multi fall back when we could not read
    # any options to offer (so the user can still type a value).
    with wx.TextEntryDialog(
            parent, _("Value for {name}:").format(name=name),
            _("Edit field"), value=current) as dlg:
        return dlg.GetValue() if dlg.ShowModal() == wx.ID_OK else None


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
        rec = self._records[i]
        if rec.get("kind") == "attachment":
            # A file to attach: the add-on cannot fill files, so it only
            # reminds you. Show the current filename if the page exposes one.
            return rec["value"] or _("attach this yourself")
        if rec["value"]:
            return rec["value"]
        fill = rec.get("fill")
        if fill:
            return _("will fill {v}").format(v=fill)
        return _("empty, needs you")

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
        rec = self._records[i]
        if rec.get("kind") == "attachment":
            ui.message(_("This is a file to attach. Use Go to, then attach it "
                         "yourself; the add-on cannot fill files."))
            return
        cur = self._pending.get(i, rec["value"])
        newval = edit_field(self, rec["name"], rec.get("kind", "text"),
                            rec.get("options"), cur)
        if newval is not None:
            self._pending[i] = newval
            self._refresh(i)

    def _onFill(self, evt):
        i = self._sel()
        if i is None:
            return
        if self._records[i].get("kind") == "attachment":
            ui.message(_("This is a file to attach. Use Go to, then attach it "
                         "yourself; the add-on cannot fill files."))
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
        if self._records[i].get("kind") == "attachment":
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


# ---------------------------------------------------------------------------
# Phase 7: sections (Experience, Education, Skills, or any you add). A shallow
# drill-down so a screen-reader user is always in a short list or a small form:
#   level 1  SectionsDialog  - Personal details + your sections
#   level 2  EntriesDialog   - the entries (rows) in one section
#   level 3  EntryFormDialog - one entry's handful of fields
# ---------------------------------------------------------------------------

_PERSONAL = _("Personal information")

_ENTRY_LABELS = {
    "job_title": _("Job title"), "employer": _("Employer"),
    "institution": _("Institution"), "qualification": _("Qualification"),
    "field_of_study": _("Field of study"), "start_date": _("Start date"),
    "end_date": _("End date"), "description": _("Description"),
    "skill": _("Skill"), "name": _("Name"), "issuer": _("Issuer"),
    "date": _("Date"), "language": _("Language"),
    "proficiency": _("Proficiency"), "title": _("Title"), "detail": _("Detail"),
}


def _entry_label(field):
    return _ENTRY_LABELS.get(field, field.replace("_", " ").capitalize())


def _fields_for(section, row):
    return profile.fields_for_section(section, row or {})


class EntryFormDialog(wx.Dialog):
    """Level 3: one entry's fields. Dates use the month/year picker (Present, No
    date, or a specific month and year); other fields are text. 'present', a
    year alone, or 'Sep 2023' all round-trip. Returns the row via values()."""

    def __init__(self, parent, section, row, fields=None):
        super().__init__(
            parent, title=_("Entry in {section}").format(section=section))
        self._fields = (fields if fields is not None
                        else _fields_for(section, row or {}))
        self._ctrls = {}       # text fields:  field -> TextCtrl
        self._date_btns = {}   # date fields:  field -> Button
        self._date_vals = {}   # date fields:  field -> current value string
        main = wx.BoxSizer(wx.VERTICAL)
        helper = guiHelper.BoxSizerHelper(self, sizer=main)
        for f in self._fields:
            if _is_date_field(f):
                self._date_vals[f] = str((row or {}).get(f, ""))
                btn = wx.Button(self, label=self._date_label(f))
                btn.Bind(wx.EVT_BUTTON, lambda e, fld=f: self._pick_date(fld))
                helper.addItem(btn)
                self._date_btns[f] = btn
            else:
                style = wx.TE_MULTILINE if f == "description" else 0
                ctrl = helper.addLabeledControl(
                    _entry_label(f) + ":", wx.TextCtrl, style=style)
                ctrl.SetValue(str((row or {}).get(f, "")))
                self._ctrls[f] = ctrl
        main.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL),
                 flag=wx.EXPAND | wx.ALL, border=8)
        self.SetSizerAndFit(main)
        if self._fields:
            first = self._fields[0]
            (self._ctrls.get(first) or self._date_btns.get(first)).SetFocus()

    def _date_label(self, f):
        v = self._date_vals.get(f, "")
        return "%s: %s" % (_entry_label(f), v or _("Set date"))

    def _pick_date(self, f):
        with _MonthYearDialog(
                self, _entry_label(f), self._date_vals.get(f, "")) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._date_vals[f] = dlg.GetValue()
                self._date_btns[f].SetLabel(self._date_label(f))
                self.Layout()
        self._date_btns[f].SetFocus()

    def values(self):
        """The row the user entered: field -> value, with empties dropped."""
        out = {}
        for f, ctrl in self._ctrls.items():
            v = ctrl.GetValue().strip()
            if v:
                out[f] = v
        for f, v in self._date_vals.items():
            if v.strip():
                out[f] = v.strip()
        return out


class EntriesDialog(wx.Dialog):
    """Level 2: the entries in one section, one summary line each. Add, edit and
    remove rows."""

    def __init__(self, parent, store, section):
        super().__init__(
            parent, title=_("Job Form Filler: {s}").format(s=section))
        self._store = store
        self._section = section
        main = wx.BoxSizer(wx.VERTICAL)
        helper = guiHelper.BoxSizerHelper(self, sizer=main)
        self._list = helper.addLabeledControl(
            _("&Entries:"), wx.ListBox, choices=self._lines())
        if self._rows():
            self._list.SetSelection(0)
        # Enter or double-click opens the selected entry.
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._onEdit)
        self.Bind(wx.EVT_CHAR_HOOK, self._onCharHook)

        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in ((_("&Add entry"), self._onAdd),
                               (_("&Edit"), self._onEdit),
                               (_("&Remove"), self._onRemove)):
            b = wx.Button(self, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            row.Add(b, flag=wx.RIGHT, border=8)
        main.Add(row, flag=wx.ALL, border=8)
        main.Add(self.CreateButtonSizer(wx.CLOSE),
                 flag=wx.EXPAND | wx.ALL, border=8)
        self.Bind(wx.EVT_BUTTON, self._onClose, id=wx.ID_CLOSE)
        self.SetSizerAndFit(main)
        self._list.SetFocus()

    def _onCharHook(self, evt):
        if (evt.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER)
                and self.FindFocus() is self._list and self._rows()):
            self._onEdit(evt)
        else:
            evt.Skip()

    def _rows(self):
        return self._store.section_rows(self._section)

    def _lines(self):
        rows = self._rows()
        return [announce.entry_summary(r) for r in rows] or [_("(no entries yet)")]

    def _refresh(self, sel=0):
        rows = self._rows()
        self._list.Set(self._lines())
        if rows:
            self._list.SetSelection(min(sel, len(rows) - 1))
        self._list.SetFocus()

    def _sel(self):
        i = self._list.GetSelection()
        return i if (i != wx.NOT_FOUND and self._rows()) else None

    def _onAdd(self, evt):
        fields = self._fields_for_new_entry()
        if fields is None:
            return
        with EntryFormDialog(self, self._section, {}, fields=fields) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            row = dlg.values()
        if not row:
            return
        self._store.add_row(self._section, row)
        self._refresh(len(self._rows()) - 1)
        ui.message(_("Added. {n} entries.").format(n=len(self._rows())))

    def _fields_for_new_entry(self):
        """Fields for a new entry: from the section's type, or asked each time in
        an 'Other' section. None if the type choice is cancelled."""
        t = self._store.section_type(self._section)
        if t != "Other":
            return profile.fields_for_type(t)
        choices = ["Work", "Education", "Skills", "Certification",
                   "Languages", "Custom"]
        with wx.SingleChoiceDialog(
                self, _("What kind of entry is this?"),
                _("Entry type"), choices) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return None
            chosen = dlg.GetStringSelection()
        return profile.fields_for_type(
            "Other" if chosen == "Custom" else chosen)

    def _onEdit(self, evt):
        i = self._sel()
        if i is None:
            return
        row = self._rows()[i]
        fields = profile.fields_for_type(
            self._store.section_type(self._section), row)
        with EntryFormDialog(self, self._section, row, fields=fields) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            new = dlg.values()
        self._store.update_row(self._section, i, new)
        self._refresh(i)
        ui.message(_("Entry updated."))

    def _onRemove(self, evt):
        i = self._sel()
        if i is None:
            return
        summary = announce.entry_summary(self._rows()[i])
        with wx.MessageDialog(
                self, _("Remove this entry?\n{s}").format(s=summary),
                _("Remove entry"), wx.YES_NO | wx.ICON_WARNING) as dlg:
            if dlg.ShowModal() != wx.ID_YES:
                return
        self._store.remove_row(self._section, i)
        self._refresh(max(0, i - 1))
        ui.message(_("Removed. {n} entries.").format(n=len(self._rows())))

    def _onClose(self, evt):
        self.EndModal(wx.ID_CLOSE)


def _apply_import(store, fields, sections, take_personal, take_sections):
    """Apply the chosen parts of a parsed CV to the active profile, REPLACING:
    personal fields overwrite (only the fields the CV actually has), and each
    chosen section's entries are replaced wholesale. take_sections is a set of
    section names. Pure store operations, so it is testable without a dialog.
    Returns the number of section entries added."""
    if take_personal:
        for k, v in fields.items():
            store.set_field(k, v)
    added = 0
    for sname, rows in sections.items():
        if sname in take_sections:
            for i in range(len(store.section_rows(sname)) - 1, -1, -1):
                store.remove_row(sname, i)
            for row in rows:
                store.add_row(sname, row)
                added += 1
    return added


def _import_summary(store, fields, sections):
    """A plain description of what importing this CV would change, so you can
    say yes or no with your eyes open."""
    lines = []
    if fields:
        lines.append(_("Personal information: {names}").format(
            names=", ".join(announce.human(k) for k in fields)))
    for sname, rows in sections.items():
        have = len(store.section_rows(sname))
        if have:
            lines.append(_("{name}: replace your {have} entries with {n} from "
                           "the CV").format(name=sname, have=have,
                                            n=len(rows)))
        else:
            lines.append(_("{name}: add {n} entries").format(
                name=sname, n=len(rows)))
    return lines


def import_cv_into_active(parent, store):
    """Pick a CV, describe what it would change, and on Yes REPLACE those parts
    of the active profile with it (personal fields overwrite; a section's
    entries are replaced). Returns the number of section entries added, or -1 if
    cancelled or nothing could be read. Nothing is submitted anywhere; you
    review the result in the list afterwards."""
    if store is None or store.active_name() is None:
        return -1
    with wx.FileDialog(
            parent, _("Choose your CV"),
            wildcard=_("CV files (*.docx;*.pdf;*.txt)|*.docx;*.pdf;*.txt"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fd:
        if fd.ShowModal() != wx.ID_OK:
            return -1
        path = fd.GetPath()
    try:
        text = cvparse.extract_text(path)
        fields = cvparse.cv_to_fields(cvparse.parse_cv_text(text))
        if not fields.get("country"):
            c = countries.detect_country(text, fields.get("phone", ""))
            if c:
                fields["country"] = c
        sections = cvparse.parse_cv_sections(text)
    except Exception:
        log.error("JFF: in-dialog CV import failed", exc_info=True)
        return -1
    if not fields and not sections:
        ui.message(_("Nothing could be read from that CV."))
        return -1
    message = (_("Importing this CV will make these changes:\n\n")
               + "\n".join(_import_summary(store, fields, sections))
               + _("\n\nAnything not mentioned is left as it is. Import now?"))
    with wx.MessageDialog(parent, message, _("Import from CV"),
                          wx.YES_NO | wx.ICON_QUESTION) as dlg:
        if dlg.ShowModal() != wx.ID_YES:
            return -1
    added = _apply_import(store, fields, sections,
                          take_personal=bool(fields),
                          take_sections=set(sections))
    try:
        store.save()
    except Exception:
        log.error("JFF: save after in-dialog import failed", exc_info=True)
    return added


class AddSectionDialog(wx.Dialog):
    """Name and type for a new section. The type (Work, Education, Skills,
    Certification, Other) decides its entries' fields; an 'Other' section asks
    the entry type each time you add one."""

    def __init__(self, parent):
        super().__init__(parent, title=_("Add section"))
        main = wx.BoxSizer(wx.VERTICAL)
        helper = guiHelper.BoxSizerHelper(self, sizer=main)
        self._name = helper.addLabeledControl(_("&Name:"), wx.TextCtrl)
        self._type = helper.addLabeledControl(
            _("&Type:"), wx.Choice, choices=profile.SECTION_TYPES)
        self._type.SetSelection(0)
        main.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL),
                 flag=wx.EXPAND | wx.ALL, border=8)
        self.SetSizerAndFit(main)
        self._name.SetFocus()

    def name(self):
        return self._name.GetValue().strip()

    def section_type(self):
        return profile.SECTION_TYPES[max(0, self._type.GetSelection())]


def choose_entries(parent, section_name, rows):
    """A checklist of a section's entries (already ordered most recent first),
    all ticked, so the user picks which go on this application. Returns the
    chosen rows in the shown order, or None if cancelled. Empty in, empty out."""
    if not rows:
        return []
    labels = [announce.entry_summary(r) or _("(entry)") for r in rows]
    # prePopup/postPopup are NVDA's way of bringing a dialog launched from NVDA
    # to the foreground reliably. Without them Windows can leave the browser in
    # front, the dialog never gets focus, and the fill hangs waiting on it
    # (seen live: "Foreground took too long to change"). Every other dialog here
    # already does this.
    gui.mainFrame.prePopup()
    try:
        with wx.MultiChoiceDialog(
                parent,
                _("Which {name} entries should go on this form? "
                  "Most recent first.").format(name=section_name),
                _("Fill {name}").format(name=section_name), labels) as dlg:
            dlg.SetSelections(list(range(len(rows))))   # all ticked by default
            if dlg.ShowModal() != wx.ID_OK:
                return None
            picks = dlg.GetSelections()
    finally:
        gui.mainFrame.postPopup()
    return [rows[i] for i in picks]


class SectionsDialog(wx.Dialog):
    """Level 1: Personal details plus every section. Open one, or add, rename
    and remove sections. Personal details opens the details form; a section
    opens its entries. Personal details cannot be renamed or removed."""

    def __init__(self, parent, store):
        super().__init__(
            parent, title=_("Job Form Filler: My details and sections"))
        self._store = store
        main = wx.BoxSizer(wx.VERTICAL)
        helper = guiHelper.BoxSizerHelper(self, sizer=main)
        self._list = helper.addLabeledControl(
            _("&Sections:"), wx.ListBox, choices=self._items())
        self._list.SetSelection(0)
        # Enter or double-click opens the selected item; no Open button needed.
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._onOpen)
        self.Bind(wx.EVT_CHAR_HOOK, self._onCharHook)

        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in ((_("&Import from CV..."), self._onImport),
                               (_("&Add section"), self._onAdd),
                               (_("Re&name"), self._onRename),
                               (_("&Remove"), self._onRemove)):
            b = wx.Button(self, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            row.Add(b, flag=wx.RIGHT, border=8)
        main.Add(row, flag=wx.ALL, border=8)
        main.Add(self.CreateButtonSizer(wx.CLOSE),
                 flag=wx.EXPAND | wx.ALL, border=8)
        self.Bind(wx.EVT_BUTTON, self._onClose, id=wx.ID_CLOSE)
        self.SetSizerAndFit(main)
        self._list.SetFocus()

    def _onCharHook(self, evt):
        if (evt.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER)
                and self.FindFocus() is self._list):
            self._onOpen(evt)
        else:
            evt.Skip()

    def _items(self):
        return [_PERSONAL] + self._store.section_names()

    def _refresh(self, sel=0):
        self._list.Set(self._items())
        self._list.SetSelection(min(sel, self._list.GetCount() - 1))
        self._list.SetFocus()

    def _selected_section(self):
        """The selected section name, or None for Personal details / no
        selection (so the caller blocks rename and remove on Personal)."""
        i = self._list.GetSelection()
        if i == wx.NOT_FOUND or i == 0:
            return None
        names = self._store.section_names()
        return names[i - 1] if (i - 1) < len(names) else None

    def _onOpen(self, evt):
        i = self._list.GetSelection()
        if i == 0:
            dlg = DetailsDialog(self, self._store)
            if dlg.ShowModal() == wx.ID_OK:
                dlg.commit()
                try:
                    self._store.save()
                    ui.message(_("Details saved."))
                except Exception:
                    log.error("JFF: could not save details", exc_info=True)
            dlg.Destroy()
            self._list.SetFocus()
            return
        section = self._selected_section()
        if section is None:
            return
        with EntriesDialog(self, self._store, section) as dlg:
            dlg.ShowModal()
        # Put focus back on the list so every section is reachable again, not
        # only the first time. Without this you are stranded on the buttons
        # after leaving a section, with no way back to the list.
        self._list.SetFocus()

    def _onImport(self, evt):
        n = import_cv_into_active(self, self._store)
        if n >= 0:
            self._refresh()
            ui.message(_("Imported. {n} entries.").format(n=n) if n
                       else _("Imported your personal information."))
        self._list.SetFocus()

    def _onAdd(self, evt):
        with AddSectionDialog(self) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            name = dlg.name()
            stype = dlg.section_type()
        if not name or name == _PERSONAL or name in self._store.section_names():
            return
        self._store.add_section(name, stype)
        self._refresh(self._list.GetCount())   # select the new one
        ui.message(_("Added section {name}.").format(name=name))

    def _onRename(self, evt):
        section = self._selected_section()
        if section is None:
            ui.message(_("Pick a section to rename. "
                         "Personal details cannot be renamed."))
            return
        with wx.TextEntryDialog(
                self, _("New name for {name}:").format(name=section),
                _("Rename section"), value=section) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            new = dlg.GetValue().strip()
        if not new or new == section or new in self._store.section_names():
            return
        self._store.rename_section(section, new)
        self._refresh(self._list.GetSelection())
        ui.message(_("Renamed to {name}.").format(name=new))

    def _onRemove(self, evt):
        section = self._selected_section()
        if section is None:
            ui.message(_("Pick a section to remove. "
                         "Personal details cannot be removed."))
            return
        with wx.MessageDialog(
                self,
                _("Remove the section {name} and all its entries?").format(
                    name=section),
                _("Remove section"), wx.YES_NO | wx.ICON_WARNING) as dlg:
            if dlg.ShowModal() != wx.ID_YES:
                return
        self._store.remove_section(section)
        self._refresh(0)
        ui.message(_("Removed section {name}.").format(name=section))

    def _onClose(self, evt):
        self.EndModal(wx.ID_CLOSE)


def manage_sections(store):
    """Open the sections manager (level 1). Saves on close. Main thread only."""
    gui.mainFrame.prePopup()
    try:
        with SectionsDialog(gui.mainFrame, store) as dlg:
            dlg.ShowModal()
        try:
            store.save()
        except Exception:
            log.error("JFF: could not save sections", exc_info=True)
    finally:
        gui.mainFrame.postPopup()
