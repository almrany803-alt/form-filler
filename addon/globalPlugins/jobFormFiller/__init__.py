# __init__.py - the NVDA layer. It turns the core's decisions into real key
# presses and speech.
#
# IMPORTANT, and stated honestly: this module imports NVDA internals and CANNOT
# run or be tested in the Linux sandbox. It is written to the patterns we
# studied in AI-Hub (focused-field insertion via api.copyToClip + Ctrl+V) and
# clipContentsDesigner (focus/browse-mode handling, keyboard-layout awareness,
# settings panel lifecycle). It needs verification on real Windows + NVDA.

import os
import re
import json
import time
import globalPluginHandler
import wx
import gui
import globalVars
import api
import ui
import controlTypes
import browseMode
import textInfos
from scriptHandler import script
from keyboardHandler import KeyboardInputGesture
import addonHandler

from .core import matcher, controls, announce, profile, fingerprints
from .core import vision, capture
from . import dialogs

try:
    from logHandler import log          # NVDA's logger; shows in Tools > View log
except Exception:
    import logging
    log = logging.getLogger("jobFormFiller")


def _fd_summary(fd):
    return ("label=%r aria=%r name=%r id=%r autocomplete=%r role=%r placeholder=%r"
            % (fd.label, fd.aria_label, fd.name, fd.id,
               fd.autocomplete, fd.role, fd.placeholder))


def _obj_from_item(item):
    """Get the NVDAObject for a browse-mode quick-nav item, across variations."""
    info = getattr(item, "textInfo", None)
    if info is not None:
        try:
            return info.NVDAObjectAtStart
        except Exception:
            pass
    return getattr(item, "obj", None)


def _digits(s):
    return "".join(c for c in (s or "") if c.isdigit())


def _date_order_from_hint(text):
    """Read a day/month/year order from a format hint like 'DD/MM/YYYY' or
    'mm-dd-yyyy'. Returns 'DMY', 'MDY', 'YMD', or '' if none is discernible."""
    order = ""
    for ch in (text or "").lower():
        u = ch.upper()
        if u in ("D", "M", "Y") and u not in order:
            order += u
        if len(order) == 3:
            break
    return order if set(order) == {"D", "M", "Y"} else ""


def _date_separator_from_hint(text, default="/"):
    for ch in (text or ""):
        if ch in "/-.":
            return ch
    return default


def _format_date(y, m, d, order, sep):
    part = {"Y": y, "M": m, "D": d}
    return sep.join(part[o] for o in order)


def _is_boolean_value(v):
    """True when a value is a yes/no answer, so a checkbox is only ever toggled
    from a real boolean, never from free text like a name or a country."""
    return str(v).strip().lower() in (
        "yes", "no", "true", "false", "1", "0", "on", "off", "checked",
        "unchecked", "y", "n", "نعم", "لا", "si", "sí", "oui", "non", "ja", "nein")


_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday",
             "saturday", "sunday")
_MONTHS = ("january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december")


def _looks_like_calendar_day(name):
    """True when a control's name is a calendar day cell like 'Monday, June 29th,
    2026' or 'June 29, 2026', so the review can skip an open calendar's day grid
    instead of reading dozens of day buttons."""
    t = (name or "").strip().lower()
    if not t or len(t) > 40:
        return False
    has_month = any(m in t for m in _MONTHS)
    has_year = bool(re.search(r"\b(19|20)\d\d\b", t))
    has_weekday = any(w in t for w in _WEEKDAYS)
    # a day cell reads as month + a day number, usually with a year or weekday
    return has_month and (has_year or has_weekday) and bool(re.search(r"\d", t))


def _is_placeholder_value(v):
    """True when a choice control's current value is a 'nothing chosen yet'
    placeholder rather than a real selection, so a whole-form fill may set it.
    Covers the supported languages and punctuation-only defaults."""
    if not v:
        return True
    t = " ".join(str(v).lower().replace("-", " ").split())
    if not t or all(not c.isalnum() for c in t):      # "", "--", "...", "/"
        return True
    for p in ("choose", "select", "please", "pick one", "not selected",
              "choisir", "selectionner", "seleccione", "auswahlen", "auswahl",
              "bitte", "seleziona", "wybierz", "selecteer", "kies", "اختر",
              "select one"):
        if t.startswith(p):
            return True
    return False

try:
    addonHandler.initTranslation()
except Exception:
    pass

# Ensure _() exists even if translation init failed, so class bodies below
# that call _() do not raise at import time.
try:
    _
except NameError:
    def _(s):
        return s


def _states_of(obj):
    names = set()
    S = controlTypes.State
    for st, tag in ((S.EDITABLE, "editable"), (S.MULTILINE, "multiline"),
                    (S.FOCUSED, "focused"), (S.CHECKABLE, "checkable"),
                    (S.HASPOPUP, "haspopup"), (S.MULTISELECTABLE, "multiselectable"),
                    (S.COLLAPSED, "collapsed"), (S.EXPANDED, "expanded")):
        try:
            if st in obj.states:
                names.add(tag)
        except Exception:
            pass
    return tuple(names)


def _descriptor_from_object(obj):
    """Build a matcher.FieldDescriptor from a live NVDA object, using the keys
    Chrome actually exposes in its IA2 attributes (confirmed on real Chrome):
      html-input-name -> the HTML name ("given-name", "email", "tel")
      text-input-type -> the input type ("email", "tel")
      name-from       -> how the label was derived (a real label vs a placeholder)
      xml-roles       -> the ARIA role ("combobox")
    """
    ia2 = getattr(obj, "IA2Attributes", {}) or {}
    log.info("JFF raw: ia2=%r" % dict(ia2))

    # role: prefer the ARIA role Chrome gives, else NVDA's role token.
    role = ia2.get("xml-roles", "")
    if not role:
        try:
            r = obj.role
            role = getattr(r, "name", str(r)).lower()
        except Exception:
            role = ""

    html_name = ia2.get("html-input-name", "") or ia2.get("name", "")
    input_type = (ia2.get("text-input-type", "") or "").lower()
    # Prefer the real HTML autocomplete token (given-name, family-name, email,
    # tel, address-line1, postal-code, country-name...): it is the strongest,
    # language-independent signal, and Chrome exposes it in IA2. Fall back to a
    # token synthesised from the input type. ARIA autocomplete values (list,
    # inline, both) are not fill tokens, so the matcher ignores them harmlessly.
    # NOTE (verified on real Chrome+NVDA): Chrome does NOT expose the HTML
    # autocomplete purpose (given-name, family-name...) here for plain inputs,
    # even inside a <form>. ia2['autocomplete'] only carries ARIA autocomplete
    # (list/inline/both) on comboboxes, which the matcher ignores but which
    # helps classify_control. Identity comes from label, html name, aria-label.
    ac_attr = (ia2.get("autocomplete", "") or "").strip().lower()
    synth = {"email": "email", "tel": "tel", "url": "url"}.get(input_type, "")
    autocomplete = ac_attr or synth

    # If the only "label" came from the placeholder or a tooltip, treat it as a
    # placeholder (a guess), not a real label (strong).
    label = obj.name or ""
    placeholder = ""
    if ia2.get("name-from", "") in ("placeholder", "tooltip"):
        placeholder, label = label, ""
    # Keep the raw HTML placeholder too (e.g. a date format like DD/MM/YYYY),
    # even when the field has a real label; used as a date format hint.
    if not placeholder:
        placeholder = ia2.get("placeholder", "") or ""

    return matcher.FieldDescriptor(
        role=role,
        label=label,
        aria_label="",
        name=html_name,
        id=ia2.get("id", ""),
        placeholder=placeholder,
        autocomplete=autocomplete,
        input_type=input_type,
        roledescription=(ia2.get("roledescription", "")
                         or getattr(obj, "roleText", "") or ""),
        dom_class=ia2.get("class", "") or "",
        haspopup=(ia2.get("haspopup", "") or "").lower(),
        states=_states_of(obj),
    )


def _paste_into_focused(obj, value):
    """Insert text the same way AI-Hub inserts transcriptions: copy then paste,
    so the page's own input events fire and React/Workday state updates.
    Layout note: on Arabic/Hebrew/Farsi layouts the paste key differs; the real
    build resolves it the way clipContentsDesigner resolves copy/cut."""
    api.copyToClip(value)
    KeyboardInputGesture.fromName("control+v").send()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("Job Form Filler")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._layerActive = False
        self._layerGen = 0
        # Encrypted profile store, in NVDA's config dir. On Windows the crypto is
        # DPAPI (tied to the user account); the store logic itself is our tested
        # code. self._profile is the active profile the fill commands read.
        try:
            import addonHandler
            _ver = addonHandler.getCodeAddon().version
        except Exception:
            _ver = "?"
        log.info("JFF: Job Form Filler %s starting" % _ver)
        self._store = None
        self._profile = {}
        try:
            data_dir = os.path.join(globalVars.appArgs.configPath, "jobFormFiller")
            os.makedirs(data_dir, exist_ok=True)
            self._store = profile.ProfileStore(
                os.path.join(data_dir, "profile.dat"), profile.default_crypto())
            self._store.load()
            self._profile = self._store.get_active() or {}
            log.info("JFF: profile store loaded, %d field(s) present"
                     % len(self._profile))
        except Exception:
            log.error("JFF: could not load profile store", exc_info=True)

        # A Tools-menu item to edit your details.
        self._detailsItem = None
        try:
            toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
            self._detailsItem = toolsMenu.Append(
                wx.ID_ANY, _("Job Form Filler: My details..."))
            gui.mainFrame.sysTrayIcon.Bind(
                wx.EVT_MENU, self._onDetails, self._detailsItem)
        except Exception:
            log.error("JFF: could not add menu item", exc_info=True)

    def _onDetails(self, evt):
        if self._store is None:
            ui.message(_("Your details cannot be stored on this system."))
            return
        saved = dialogs.edit_details(self._store)
        if saved is not None:
            self._profile = self._store.get_active() or {}

    # --- add-on menu: press NVDA+J for a navigable menu ----------------------
    # A real native popup menu: arrow to an item and press Enter, or press its
    # access key. NVDA announces each item, so it is discoverable rather than a
    # memorised letter. Fill actions run AFTER the menu closes, so focus is back
    # on the form field they act on.
    @script(
        description=_("Open the Job Form Filler menu"),
        gesture="kb:NVDA+j",
    )
    def script_menu(self, gesture):
        wx.CallAfter(self._popupMenu)

    def _popupMenu(self):
        savedFocus = api.getFocusObject()
        savedForeground = None
        try:
            import winUser
            savedForeground = winUser.getForegroundWindow()
        except Exception:
            pass
        self._menuAction = None
        menu = wx.Menu()
        mField = menu.Append(wx.ID_ANY, _("Fill this &field"))
        mForm = menu.Append(wx.ID_ANY, _("Fill &all fields"))
        mReview = menu.Append(wx.ID_ANY, _("&Review fields"))
        mScan = menu.Append(wx.ID_ANY, _("&Scan this form (report)"))
        mVision = menu.Append(wx.ID_ANY, _("&Vision (AI) settings..."))
        menu.AppendSeparator()

        # Profile submenu, always shown. Your details ARE a profile, so switch,
        # create, edit and delete all live here in one place.
        names = self._store.profile_names() if self._store else []
        active = self._store.active_name() if self._store else None
        has_profile = bool(active)
        profMenu = wx.Menu()
        radioIds = {}
        for n in names:
            it = profMenu.AppendRadioItem(wx.ID_ANY, n)
            if n == active:
                it.Check(True)
            radioIds[it.GetId()] = n
        if names:
            profMenu.AppendSeparator()
        mNew = profMenu.Append(wx.ID_ANY, _("&New profile..."))
        mEditP = profMenu.Append(wx.ID_ANY, _("&Edit profile..."))
        mDel = profMenu.Append(wx.ID_ANY, _("&Delete profile"))
        mEditP.Enable(has_profile)
        mDel.Enable(has_profile)
        menu.AppendSubMenu(
            profMenu, _("&Profile: {name}").format(name=active or _("none")))
        menu.AppendSeparator()

        mImport = menu.Append(wx.ID_ANY, _("&Import from CV..."))
        # The manual on-ramp only appears when there is no profile yet; once you
        # have one, editing lives in the Profile submenu (Edit profile).
        mEnter = None
        if not has_profile:
            mEnter = menu.Append(wx.ID_ANY, _("Enter your details &manually..."))

        frame = gui.mainFrame
        frame.prePopup()
        frame.Bind(wx.EVT_MENU, lambda e: self._setMenuAction("field"), mField)
        frame.Bind(wx.EVT_MENU, lambda e: self._setMenuAction("form"), mForm)
        frame.Bind(wx.EVT_MENU, lambda e: self._setMenuAction("review"), mReview)
        frame.Bind(wx.EVT_MENU, lambda e: self._setMenuAction("scan"), mScan)
        frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(self._openVisionSettings), mVision)
        frame.Bind(wx.EVT_MENU, lambda e: self._setMenuAction("new"), mNew)
        frame.Bind(wx.EVT_MENU, lambda e: self._setMenuAction("editp"), mEditP)
        frame.Bind(wx.EVT_MENU, lambda e: self._setMenuAction("del"), mDel)
        frame.Bind(wx.EVT_MENU, lambda e: self._setMenuAction("import"), mImport)
        if mEnter is not None:
            frame.Bind(wx.EVT_MENU,
                       lambda e: self._setMenuAction("new"), mEnter)
        for iid, n in radioIds.items():
            frame.Bind(
                wx.EVT_MENU,
                (lambda name: lambda e: self._setMenuAction("switch", name))(n),
                id=iid)
        frame.PopupMenu(menu)
        frame.postPopup()
        menu.Destroy()

        act = self._menuAction
        if not act:
            log.info("JFF menu: closed with no choice")
            return
        log.info("JFF menu: chose %r" % (act,))
        kind = act[0]
        if kind in ("field", "form", "review", "scan"):
            def runFill():
                if savedForeground:
                    try:
                        import winUser
                        winUser.setForegroundWindow(savedForeground)
                    except Exception:
                        pass
                if kind == "field":
                    self.script_fillField(None, focus=savedFocus)
                elif kind == "form":
                    self.script_fillForm(None, focus=savedFocus)
                elif kind == "scan":
                    self._scanForm(savedFocus)
                else:
                    self._openReview(savedFocus)
            wx.CallAfter(runFill)
            return
        after = {
            "editp": lambda: self._onDetails(None),
            "import": self._onImportCV,
            "new": self._onNewProfile,
            "del": self._onDeleteProfile,
            "switch": lambda: self._onSwitchProfile(act[1]),
        }.get(kind)
        if after:
            wx.CallAfter(after)

    def _setMenuAction(self, *action):
        self._menuAction = action

    def _critical(self, message, caption=None):
        # Critical messages must not be spoken-and-cancelled by the page's focus
        # announcement (that is the "message did not sound in time" bug). A modal
        # box cannot be cut off and forces acknowledgement.
        try:
            gui.messageBox(message, caption or _("Job Form Filler"),
                           wx.OK | wx.ICON_INFORMATION)
        except Exception:
            log.error("JFF: could not show message box", exc_info=True)
            ui.message(message)

    def _onSwitchProfile(self, name):
        if self._store is None:
            return
        self._store.set_active(name)
        try:
            self._store.save()
        except Exception:
            log.error("JFF: could not save active profile", exc_info=True)
        self._profile = self._store.get_active() or {}
        ui.message(_("Switched to {name}.").format(name=name))

    def _uniqueProfileName(self, name):
        # Never overwrite an existing profile: if the name is taken, add a number.
        existing = set(self._store.profile_names()) if self._store else set()
        if name not in existing:
            return name
        i = 2
        while "{0} {1}".format(name, i) in existing:
            i += 1
        return "{0} {1}".format(name, i)

    def _onNewProfile(self):
        if self._store is None:
            return
        with wx.TextEntryDialog(
                gui.mainFrame,
                _("Name for this version (for example Work or Teaching):"),
                _("New profile")) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            name = dlg.GetValue().strip()
        if not name:
            return
        name = self._uniqueProfileName(name)
        self._store.add_profile(name, {})
        self._store.set_active(name)
        try:
            self._store.save()
        except Exception:
            log.error("JFF: could not save new profile", exc_info=True)
        self._profile = self._store.get_active() or {}
        ui.message(_("New profile {name}.").format(name=name))
        self._onDetails(None)

    def _onDeleteProfile(self):
        if self._store is None or not self._store.active_name():
            ui.message(_("No profile to delete."))
            return
        name = self._store.active_name()
        with wx.MessageDialog(
                gui.mainFrame,
                _("Delete the profile {name}? This cannot be undone.").format(
                    name=name),
                _("Delete profile"), wx.YES_NO | wx.ICON_WARNING) as dlg:
            if dlg.ShowModal() != wx.ID_YES:
                return
        self._store.delete_profile(name)
        try:
            self._store.save()
        except Exception:
            log.error("JFF: could not save after delete", exc_info=True)
        self._profile = self._store.get_active() or {}
        ui.message(_("Deleted {name}.").format(name=name))

    def _onImportCV(self):
        if self._store is None:
            return
        # 1. Pick the CV.
        with wx.FileDialog(
                gui.mainFrame, _("Choose your CV"),
                wildcard=_("CV files (*.docx;*.pdf;*.txt)|*.docx;*.pdf;*.txt"),
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fd:
            if fd.ShowModal() != wx.ID_OK:
                return
            path = fd.GetPath()
        # 2. Parse it.
        try:
            from .core import cvparse, countries
            text = cvparse.extract_text(path)
            fields = cvparse.cv_to_fields(cvparse.parse_cv_text(text))
            # If the CV states a country, detect it (in any supported language,
            # or from the phone's calling code) and pre-fill it, so the country
            # dropdown starts on the right answer for you to confirm.
            if not fields.get("country"):
                detected = countries.detect_country(text, fields.get("phone", ""))
                if detected:
                    fields["country"] = detected
                    log.info("JFF import: detected country %r" % detected)
            log.info("JFF import: parsed %d field(s) from %s: %s"
                     % (len(fields), os.path.basename(path),
                        ", ".join(sorted(fields))))
        except Exception:
            log.error("JFF: CV import failed", exc_info=True)
            self._critical(_("Could not read that CV. Check the file and try "
                             "again. Word and text files work best."))
            return
        if not fields:
            self._critical(_("No details could be read from that CV. Try "
                             "entering your details by hand instead."))
            return
        # 3. Name the profile (like New profile), defaulting to the CV's name.
        default_name = ((fields.get("given_name", "") + " "
                         + fields.get("family_name", "")).strip()
                        or _("Imported"))
        with wx.TextEntryDialog(
                gui.mainFrame,
                _("Name for this version (for example Work or Teaching):"),
                _("Import from CV"), value=default_name) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            name = dlg.GetValue().strip() or default_name
        # 4. Create the profile WITH the parsed fields and save it now, so the
        #    import persists even if the review is cancelled. A unique name means
        #    an existing profile is never overwritten.
        name = self._uniqueProfileName(name)
        self._store.add_profile(name, dict(fields))
        self._store.set_active(name)
        try:
            self._store.save()
        except Exception:
            log.error("JFF import: save failed", exc_info=True)
            self._critical(_("Could not save the imported profile."))
            return
        self._profile = self._store.get_active() or {}
        log.info("JFF import: created profile %r with %d field(s)"
                 % (name, len(fields)))
        # 5. Open the dialog to review and adjust; it is already saved.
        dialogs.edit_details(self._store)
        self._profile = self._store.get_active() or {}

    # --- review list ---------------------------------------------------------
    def _form_field_objs(self, focus):
        ti = getattr(focus, "treeInterceptor", None)
        if ti is None or not isinstance(
                ti, browseMode.BrowseModeDocumentTreeInterceptor):
            return None
        try:
            start = ti.makeTextInfo(textInfos.POSITION_FIRST)
            items = list(ti._iterNodesByType("formField", "next", start))
        except Exception:
            log.error("JFF review: could not enumerate fields", exc_info=True)
            return None
        objs = []
        for item in items:
            o = _obj_from_item(item)
            if o is not None:
                objs.append(o)
        return objs

    def _selected_radio_label(self, group):
        """The label of the radio currently checked in a group, or ''. Reuses
        the same live-checked read the fill path verifies with."""
        if group is None:
            return ""
        for r in self._collect_radios(group):
            try:
                if self._live_checked(r):
                    return r.name or ""
            except Exception:
                continue
        return ""

    def _review_record(self, obj, fd, key, kind, options, group):
        """Build one review row. For a radio group the value is the option now
        selected and the name is the group's question, not the single option."""
        try:
            value = obj.value or ""
        except Exception:
            value = ""
        if group is not None:
            sel = self._selected_radio_label(group)
            if sel:
                value = sel
        name = (announce.human(key) if key
                else self._humanize_field(fd))
        if group is not None:
            try:
                gname = group.name or ""
            except Exception:
                gname = ""
            if gname:
                name = gname
        return {"obj": obj, "fd": fd, "key": key, "name": name,
                "value": value, "kind": kind, "options": options,
                "group": group}

    def _collect_review(self, focus):
        """Enumerate the form's fields and attach, to each, the accessible
        editor kind and its options, so the dialog stays pure UI. Mirrors the
        whole-form fill loop's order and dedup keys exactly, so the review list
        never drifts from how a field actually fills: date first, then a
        multi-select collapsed from its option listitems, then a radio group
        collapsed to its question, then the single-choice and text controls."""
        objs = self._form_field_objs(focus)
        if objs is None:
            return None
        records = []
        processed_radio = set()
        processed_multi = set()
        # Fillable review fields only: exclude file uploads and buttons/links,
        # the same rule as the whole-form summary. Without it the review listed
        # the Resume/CV attach as an editable row, misaligning every row.
        review_fillable = (
            controlTypes.Role.EDITABLETEXT, controlTypes.Role.COMBOBOX,
            controlTypes.Role.LIST, controlTypes.Role.LISTITEM,
            controlTypes.Role.CHECKBOX, controlTypes.Role.RADIOBUTTON,
            controlTypes.Role.SPINBUTTON)
        for obj in objs:
            fd = _descriptor_from_object(obj)
            result = matcher.match_field(fd)
            key = result.key
            cc = self._classify(fd)

            # Date: one row, three dropdowns in the editor. A date-picker combobox
            # (calendar) counts too, so the user gets our picker, not the grid.
            if (key == "date_of_birth" or fd.input_type == "date"
                    or cc == controls.DATEPICKER or self._is_date_picker(fd)):
                records.append(self._review_record(
                    obj, fd, key, controls.EDITOR_DATE, [], None))
                continue

            # A calendar day cell (gridcell, or a button named like a date) is not
            # a form field; skip it quietly so an open calendar doesn't flood the
            # review with dozens of day buttons.
            if (obj.role == controlTypes.Role.TABLECELL
                    or _looks_like_calendar_day(fd.label or fd.name or "")):
                continue

            # Not a fillable review field (file upload, button, link): skip, so
            # the review never offers a text editor for a file and its rows line
            # up with the real fields.
            if obj.role not in review_fillable or (fd.input_type or "").lower() == "file":
                log.info("JFF review: skip non-fillable %s %r"
                         % (obj.role, fd.label or fd.name or ""))
                continue

            # Multi-select: browse mode enumerates the option listitems, not the
            # listbox, so collapse to the parent, keyed as the fill loop keys it.
            try:
                parent = obj.parent if obj.role == controlTypes.Role.LISTITEM \
                    else None
                parent_multi = (parent is not None and
                                controlTypes.State.MULTISELECTABLE in parent.states)
            except Exception:
                parent, parent_multi = None, False
            if parent_multi:
                lfd = _descriptor_from_object(parent)
                lid = lfd.label or lfd.id or str(id(parent))
                if lid in processed_multi:
                    continue
                processed_multi.add(lid)
                labels, _opts = self._read_option_children(parent, "review-multi")
                lresult = matcher.match_field(lfd)
                records.append(self._review_record(
                    parent, lfd, lresult.key, controls.EDITOR_MULTI, labels, None))
                continue

            # Native multi-select where the listbox itself is the form field
            # (not its option listitems): read its options directly.
            if cc == controls.MULTISELECT:
                mid = fd.label or fd.id or str(id(obj))
                if mid in processed_multi:
                    continue
                processed_multi.add(mid)
                labels, _opts = self._read_option_children(obj, "review-multi")
                records.append(self._review_record(
                    obj, fd, key, controls.EDITOR_MULTI, labels, None))
                continue

            # Radios: collapse the group to one row, same key as the fill loop.
            if cc == controls.RADIO:
                group, radios = self._radio_group(obj)
                gid = ""
                try:
                    gid = (group.name if group is not None else "") or ""
                except Exception:
                    gid = ""
                gid = gid or fd.name or str(id(group))
                if gid in processed_radio:
                    continue
                processed_radio.add(gid)
                labels = []
                for r in radios:
                    try:
                        labels.append(r.name or "")
                    except Exception:
                        labels.append("")
                labels = [l for l in labels if l]
                records.append(self._review_record(
                    obj, fd, key, controls.EDITOR_SINGLE, labels, group))
                continue

            kind = controls.editor_kind(cc, key or "", fd.input_type or "")

            # Checkbox: Yes / No. No option list to read.
            if kind == controls.EDITOR_YESNO:
                records.append(self._review_record(
                    obj, fd, key, controls.EDITOR_YESNO, [], None))
                continue

            # Single-choice or editable combobox: read the real options so the
            # dialog can offer an accessible chooser. If a select-only custom
            # combobox hides its options behind a closed popup we cannot read,
            # fall back to a typed box rather than an empty chooser.
            if kind in (controls.EDITOR_SINGLE, controls.EDITOR_EDITABLE):
                labels, _opts = self._read_option_children(obj, "review-choice")
                if not labels and cc in (controls.NATIVE_SELECT,
                                         controls.ARIA_COMBOBOX,
                                         controls.EDITABLE_COMBOBOX,
                                         controls.ASYNC_COMBOBOX):
                    # Closed dropdown: open it by keyboard to read the options.
                    # arrow_open (plain Down) for custom/react-select comboboxes,
                    # which open on Down exactly as the user does by hand; native
                    # <select> stays on alt+Down only (a plain Down would move
                    # its selection). No mouse is involved either way.
                    labels = self._read_select_options(
                        obj, arrow_open=(cc != controls.NATIVE_SELECT))
                if not labels and kind == controls.EDITOR_SINGLE:
                    kind = controls.EDITOR_TEXT
                records.append(self._review_record(
                    obj, fd, key, kind, labels, None))
                continue

            # Text and async: a typed box. Async hands back to its live list at
            # fill time, since NVDA reports its network-loaded options as empty.
            records.append(self._review_record(
                obj, fd, key, controls.EDITOR_TEXT, [], None))
        log.info("JFF review: collected %d field(s) [%s]"
                 % (len(records), ", ".join(r["kind"] for r in records)))
        return records

    def _apply_review_change(self, rec, newval):
        """Write one review change back through the primitive that matches the
        field's kind, not a blind paste. The user chose an explicit value in the
        review list, so we set exactly that. Returns True if it took."""
        kind = rec.get("kind", "text")
        obj, fd = rec["obj"], rec["fd"]
        try:
            if kind == "single" and rec.get("group") is not None:
                return self._select_radio_by_label(rec["group"], newval)
            if kind == "single":
                _pick, verdict = self._fill_native_select(
                    obj, newval, rec.get("key") or "")
                return verdict == "confirmed"
            if kind == "yesno":
                return self._fill_checkbox(obj, fd, newval) == "confirmed"
            if kind == "multi":
                values = newval if isinstance(newval, list) else [newval]
                verdict, _sel = self._fill_multiselect(obj, values)
                return verdict == "confirmed"
            if kind == "date":
                return self._fill_date(obj, fd, newval) == "confirmed"
            if kind == "editable":
                return self._fill_editable_combobox(obj, fd, newval)
            return self._write_field(obj, fd, newval)
        except Exception:
            log.error("JFF review: writeback failed kind=%r" % kind,
                      exc_info=True)
            return False

    def _fill_editable_combobox(self, obj, fd, value):
        """Commit a value into an editable combobox (react-select and similar):
        type the value to open and filter the menu, then Enter to select the
        highlighted match, the way a user does. A plain paste filters but never
        selects, so the choice reverts on blur (the write-side twin of the
        Country false-confirm). Keyboard only, focus-verified; verifies the value
        stuck (not a placeholder). No mouse."""
        if not value:
            return self._write_field(obj, fd, value)
        ti = getattr(obj, "treeInterceptor", None)
        prev_pt = None
        try:
            obj.setFocus()
            api.setFocusObject(obj)
            time.sleep(0.12)
            # Safety: only type if focus actually landed on this field.
            foc = api.getFocusObject()
            fid = (getattr(foc, "IA2Attributes", {}) or {}).get("id", "")
            oid = (getattr(obj, "IA2Attributes", {}) or {}).get("id", "")
            if not (foc is obj or (fid and fid == oid)):
                log.info("JFF combo: focus did not land; plain write instead")
                return self._write_field(obj, fd, value)
            if ti is not None and hasattr(ti, "passThrough"):
                prev_pt = ti.passThrough
                ti.passThrough = True
                time.sleep(0.05)
            KeyboardInputGesture.fromName("control+a").send()
            time.sleep(0.05)
            _paste_into_focused(obj, value)          # fires the menu filter
            time.sleep(0.45)
            KeyboardInputGesture.fromName("enter").send()   # select the match
            time.sleep(0.25)
        except Exception:
            log.error("JFF combo: editable writeback failed", exc_info=True)
            return False
        finally:
            if prev_pt is not None:
                try:
                    ti.passThrough = prev_pt
                except Exception:
                    pass
        after = self._settled_value(obj)
        stuck = bool(after) and not _is_placeholder_value(after)
        log.info("JFF combo: after=%r stuck=%s" % (after, stuck))
        return stuck

    def _select_radio_by_label(self, group, label):
        """Select the radio in a group whose label matches the chosen text.
        Used by the review editor, where the user picked an explicit option."""
        radios = self._collect_radios(group)
        labels = []
        for r in radios:
            try:
                labels.append(r.name or "")
            except Exception:
                labels.append("")
        pick = controls.choose_option(label, labels)
        if pick.index is None or pick.index >= len(radios):
            log.info("JFF review: radio label %r not found" % label)
            return False
        target = radios[pick.index]
        if not self._live_checked(target):
            try:
                target.doAction()
            except Exception:
                try:
                    target.setFocus()
                    api.setFocusObject(target)
                    KeyboardInputGesture.fromName("space").send()
                except Exception:
                    log.error("JFF review: radio select failed", exc_info=True)
                    return False
        for _k in range(8):
            if self._live_checked(target):
                return True
            time.sleep(0.06)
        return False

    def _write_field(self, obj, fd, value):
        target_id = fd.id
        moved = False
        for _attempt in range(3):
            obj.setFocus()
            api.setFocusObject(obj)
            foc = api.getFocusObject()
            foc_id = (getattr(foc, "IA2Attributes", {}) or {}).get("id", "")
            if not target_id or not foc_id or foc_id == target_id:
                moved = True
                break
            time.sleep(0.05)
        if not moved:
            log.info("JFF review: focus did not land on %r" % target_id)
            return False
        KeyboardInputGesture.fromName("control+a").send()
        if value:
            _paste_into_focused(obj, value)
        else:
            KeyboardInputGesture.fromName("delete").send()
        return True

    def _scan_line(self, obj, idx):
        """One report line for a field: its name, detected control kind, the ATS
        platform, and what the add-on WOULD do, computed with the same helpers the
        fill uses. Reads nothing into the field and changes nothing."""
        fd = _descriptor_from_object(obj)
        plat = self._detect_platform(fd) or "-"
        result = matcher.match_field(fd)
        cc = self._classify(fd)
        seg = self._date_segment(fd)
        name = (announce.human(result.key) if result.key
                else self._humanize_field(fd))
        if seg and self._is_dob_field(fd):
            action = "fill date of birth %s from profile" % seg
        elif seg:
            action = "offer the date picker (date %s)" % seg
        elif (self._is_date_picker(fd) or cc == controls.DATEPICKER
              or fd.input_type == "date"):
            action = "open the date picker"
        elif cc == controls.CHECKBOX and result.key and not _is_boolean_value(
                self._value_for(result.key) or ""):
            action = "leave for you (checkbox, not a yes/no value)"
        elif result.key and self._value_for(result.key):
            action = "fill from profile: %s" % self._value_for(result.key)
        elif result.key:
            action = "identified as %s, nothing saved, offer editor" % result.key
        elif cc == controls.CHECKBOX:
            action = "offer Yes/No"
        elif cc == controls.RADIO:
            action = "offer the radio choices"
        elif cc in (controls.NATIVE_SELECT, controls.ARIA_COMBOBOX,
                    controls.EDITABLE_COMBOBOX, controls.ASYNC_COMBOBOX,
                    controls.MULTISELECT):
            action = "offer the options chooser"
        else:
            action = "offer a type box"
        return ("Field %2d: %r  [kind=%s, platform=%s]  -> %s"
                % (idx, name, cc, plat, action))

    def _scanForm(self, focus):
        """Walk the whole form and write a report of what the add-on sees and
        would do for every field, to a file the user can send and to the NVDA
        log. A read-only diagnostic and form overview: it never fills or submits."""
        objs = self._form_field_objs(focus)
        if not objs:
            ui.message(_("No form fields found here."))
            return
        lines = []
        for i, obj in enumerate(objs, 1):
            try:
                lines.append(self._scan_line(obj, i))
            except Exception:
                log.error("JFF scan: field %d failed" % i, exc_info=True)
        header = "Job Form Filler scan: %d field(s)" % len(lines)
        for ln in [header] + lines:
            log.info("JFF scan: %s" % ln)
        # Write a timestamped file so scans accumulate (you asked for more than
        # one), to a findable place: Documents\jobFormFiller if we can, else the
        # NVDA config folder. Announce the full folder so it's never a guess.
        import datetime
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder = ""
        for base in (os.path.join(os.path.expanduser("~"), "Documents"),
                     os.path.expanduser("~"),
                     globalVars.appArgs.configPath):
            try:
                cand = os.path.join(base, "jobFormFiller")
                os.makedirs(cand, exist_ok=True)
                folder = cand
                break
            except Exception:
                continue
        path = ""
        if folder:
            try:
                path = os.path.join(folder, "scan-%s.txt" % stamp)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(header + "\n\n" + "\n".join(lines) + "\n")
                self._prune_scans(folder, keep=20)
            except Exception:
                log.error("JFF scan: could not write the report", exc_info=True)
                path = ""
        if path:
            ui.message(_("Scanned {n} fields. Saved to the jobFormFiller folder "
                         "in {where}. It is also in the NVDA log.").format(
                         n=len(lines), where=folder))
        else:
            ui.message(_("Scanned {n} fields. The report is in the NVDA log."
                         ).format(n=len(lines)))

    def _prune_scans(self, folder, keep=20):
        """Keep only the most recent scan files so the folder doesn't grow without
        bound, while still holding a history (you asked for more than one)."""
        try:
            files = sorted(
                (os.path.join(folder, f) for f in os.listdir(folder)
                 if f.startswith("scan-") and f.endswith(".txt")),
                key=os.path.getmtime, reverse=True)
            for old in files[keep:]:
                try:
                    os.remove(old)
                except Exception:
                    pass
        except Exception:
            pass

    def _openReview(self, focus):
        records = self._collect_review(focus)
        if not records:
            ui.message(_("No form fields found here."))
            return
        result = dialogs.review_fields(records, self._profile)
        if result is None:
            return
        changes, goto = result
        log.info("JFF review: applying %d change(s), goto=%r"
                 % (len(changes), goto))
        applied = 0
        for idx, newval in changes:
            if self._apply_review_change(records[idx], newval):
                applied += 1
        if changes:
            ui.message(_("Applied {n} of {m} change(s).").format(
                n=applied, m=len(changes)))
        if goto is not None:
            try:
                records[goto]["obj"].setFocus()
                api.setFocusObject(records[goto]["obj"])
            except Exception:
                log.error("JFF review: go to field failed", exc_info=True)

    @script(
        description=_("Edit your saved details"),
    )
    def script_editDetails(self, gesture):
        self._onDetails(None)

    def terminate(self):
        try:
            if self._detailsItem is not None:
                gui.mainFrame.sysTrayIcon.toolsMenu.Remove(self._detailsItem)
        except Exception:
            pass
        super().terminate()

    def _date_segment(self, fd):
        """If this field is one segment of a segmented date control (day/month/
        year dropdowns, common on ATS forms and not just for birth dates), return
        'day'/'month'/'year', else None. Recognised by class ('date day'/'date
        month'/'date year') or id, since these segments carry no label."""
        hay = " ".join([(fd.id or ""),
                        (getattr(fd, "dom_class", "") or "")]).lower()
        if "date" not in hay and not any(w in hay
                                         for w in ("birth", "dob", "bday")):
            return None
        for seg in ("day", "month", "year"):
            if seg in hay:
                return seg
        return None

    def _is_dob_field(self, fd):
        """True when a date field is specifically a date of birth, so we fill it
        from the profile rather than just offering the picker."""
        hay = " ".join([(fd.id or ""),
                        (getattr(fd, "dom_class", "") or "")]).lower()
        return any(w in hay for w in ("birth", "dob", "bday"))

    def _humanize_field(self, fd):
        """Best human name for a field, so the review and the editor say the real
        label the page gives ('How Did You Hear About Us?'), a recognised date
        segment, or, only as a last resort, a name derived from the id."""
        if (fd.label or "").strip():
            return fd.label.strip()
        seg = self._date_segment(fd)
        if seg:
            what = _("Date of birth") if self._is_dob_field(fd) else _("Date")
            return "%s, %s" % (what, seg)
        raw = (fd.id or fd.name or "").strip()
        raw = re.sub(r"^(id[-_]|field[-_]|input[-_])", "", raw, flags=re.I)
        raw = re.sub(r"[-_]+", " ", raw).strip()
        if raw and not raw.isdigit():
            return raw[:1].upper() + raw[1:]
        return _("an unlabelled field")

    def _fill_dob_segment(self, obj, fd, seg):
        """Fill one day/month/year segment of a date of birth from the profile.
        The month dropdown may use a name or a number, so try both. Returns True
        if the segment took."""
        dob = (self._profile.get("date_of_birth") or "").strip()
        m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", dob)
        if not m:
            return False
        year, month, day = m.group(1), int(m.group(2)), int(m.group(3))
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November",
                  "December"]
        if seg == "day":
            cands = [str(day), "%02d" % day]
        elif seg == "year":
            cands = [year]
        else:
            cands = [months[month - 1], str(month), "%02d" % month,
                     months[month - 1][:3]]
        for val in cands:
            pick, verdict = self._fill_native_select(obj, val, "")
            if verdict == "confirmed":
                return True
        return False

    def _page_url(self):
        """The current document's URL, lower-cased, for platform detection.
        Workday and Taleo don't expose their markup markers to NVDA, but the URL
        is reliable. Best effort; '' if unavailable."""
        try:
            obj = api.getFocusObject()
            ti = getattr(obj, "treeInterceptor", None)
            root = getattr(ti, "rootNVDAObject", None) if ti else None
            u = getattr(root, "documentConstantIdentifier", "") or ""
            return u.lower() if isinstance(u, str) else ""
        except Exception:
            return ""

    def _detect_platform(self, fd):
        """Identify the ATS platform so dates and dropdowns can be routed the way
        each platform builds them. Detects by page URL first (Workday and Taleo
        hide their markup markers from NVDA), then by markup. Returns a short name
        or ''."""
        url = self._page_url()
        if url:
            if "myworkdayjobs" in url or ".workday." in url:
                return "workday"
            if "taleo.net" in url:
                return "taleo"
            if "successfactors" in url or "sapsf." in url:
                return "successfactors"
            if "icims.com" in url:
                return "icims"
            if "greenhouse.io" in url or "boards.greenhouse" in url:
                return "greenhouse"
            if "lever.co" in url:
                return "lever"
        cls = (getattr(fd, "dom_class", "") or "").lower()
        idn = (fd.id or "").lower()
        hay = cls + " " + idn
        if "select__" in cls or "greenhouse" in hay:
            return "greenhouse"
        if "ui5" in cls or "sapm" in cls or "sf" == idn[:2] or "fbclc" in idn:
            return "successfactors"
        # Workday's markup markers aren't exposed to NVDA and its classes are
        # hashed, but its field ids use a distinctive name--name pattern
        # (source--source, country--country, phoneNumber--countryPhoneCode). Use
        # that so a saved Workday page is still recognised without the live URL.
        if "--" in idn or "wd-" in cls or "workday" in hay:
            return "workday"
        if "select2" in cls:
            return "select2"
        if "taleo" in hay:
            return "taleo"
        if "icims" in hay:
            return "icims"
        return ""

    def _is_date_picker(self, fd):
        """A date-picker combobox opens a calendar (a dialog or grid popup) and is
        labelled as a date. Recognise it so we offer our own accessible date
        picker and type the result back, instead of leaving the user in a grid of
        day cells."""
        if getattr(fd, "haspopup", "") not in ("dialog", "grid"):
            return False
        hay = " ".join([(fd.label or ""), (fd.id or ""),
                        (getattr(fd, "dom_class", "") or ""),
                        (fd.placeholder or "")]).lower()
        return any(w in hay for w in ("date", "birth", "dob", "calendar"))

    def _fp_kind_to_addon(self, kind):
        """Translate a fingerprint's kind string into the add-on's kind constant.
        button_dropdown is identified as a dropdown for now; activating the button
        to reach its list is Phase 2 work."""
        return {
            "text": controls.TEXT,
            "async_combobox": controls.ASYNC_COMBOBOX,
            "editable_combobox": controls.EDITABLE_COMBOBOX,
            "native_select": controls.NATIVE_SELECT,
            "button_dropdown": controls.ASYNC_COMBOBOX,
            "checkbox": controls.CHECKBOX,
            "radio": controls.RADIO,
            "date": controls.DATEPICKER,
        }.get((kind or "").strip().lower(), "")

    def _classify(self, fd):
        """Classify a field the layered way: the shared fingerprint database first
        (exact known widgets, deterministic, per platform), then the heuristics.
        A database hit is logged so a real-machine log shows which layer decided.
        The result is still verified by behaviour downstream; the database only
        picks which method to try, it doesn't assert the fill worked."""
        fp = fingerprints.match_fingerprint(fd, self._detect_platform(fd))
        if fp and fp.get("kind"):
            mapped = self._fp_kind_to_addon(fp["kind"])
            if mapped:
                log.info("JFF fingerprint: %s -> %s (%s)"
                         % (fp.get("id", ""), fp["kind"], fp.get("note", "")))
                return mapped
        return controls.classify_control(controls.ControlDescriptor(
            role=fd.role, states=fd.states, autocomplete=fd.autocomplete,
            placeholder=fd.placeholder, roledescription=fd.roledescription,
            haspopup=getattr(fd, "haspopup", "")))

    def _data_dir(self):
        """The add-on's data folder, created if needed. Used for vision settings
        and the local disagreement log."""
        d = os.path.join(globalVars.appArgs.configPath, "jobFormFiller")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _vision_settings(self):
        """Vision settings, OFF by default. A plain JSON file so it's easy to
        inspect. Vision does nothing at all unless the user set enabled true."""
        s = {"enabled": False, "backend": "gemini", "api_key": "",
             "base_url": "", "model": ""}
        try:
            path = os.path.join(self._data_dir(), "vision_settings.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    loaded = json.load(f)
                for k in s:
                    if k in loaded:
                        s[k] = loaded[k]
        except Exception:
            pass
        return s

    def _save_vision_settings(self, s):
        try:
            path = os.path.join(self._data_dir(), "vision_settings.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(s, f)
        except Exception:
            log.error("JFF vision: could not save settings", exc_info=True)

    def _vision_provider(self):
        """Build the configured vision provider, or None if vision is off or not
        usable. Never raises."""
        s = self._vision_settings()
        if not s.get("enabled"):
            return None
        try:
            p = vision.get_provider(s.get("backend") or "pollinations",
                                    api_key=s.get("api_key", ""),
                                    base_url=s.get("base_url", ""),
                                    model=s.get("model", ""))
            return p if p.is_available() else None
        except Exception:
            return None

    def _vision_identify(self, obj):
        """Capture just this one control and ask the vision model what it is.
        Returns a reading dict or None. Opt-in and read-only: it changes nothing,
        sends only that control's pixels, and fails silently to None so the fill
        always falls back to today's behaviour."""
        provider = self._vision_provider()
        if provider is None:
            return None
        loc = getattr(obj, "location", None)
        if not loc:
            return None
        try:
            left, top, width, height = loc.left, loc.top, loc.width, loc.height
        except Exception:
            try:
                left, top, width, height = loc
            except Exception:
                return None
        if not width or not height:
            return None
        margin = 6
        png = capture.capture_rect_png(max(0, left - margin), max(0, top - margin),
                                       width + 2 * margin, height + 2 * margin)
        if not png:
            return None
        try:
            return provider.identify(png)
        except Exception as e:
            log.info("JFF vision: call failed (%s)" % e)
            try:
                ui.message(_("Vision couldn't reach the service. Check your API "
                             "key and backend in Vision settings."))
            except Exception:
                pass
            return None

    def _speak_vision_reading(self, fd, reading):
        """Tell the user what vision saw, and if it read a different KIND than our
        classification, record the structural disagreement locally (never the
        user's data) as raw material for improving the free heuristics."""
        kind = reading.get("kind") or _("a field")
        value = reading.get("current_value")
        label = reading.get("label")
        if label and not (fd.label or ""):
            ui.message(_("Vision: this looks like {k}, {l}.").format(
                k=kind, l=label))
        elif value:
            ui.message(_("Vision: this looks like {k}, showing {v}.").format(
                k=kind, v=value))
        else:
            ui.message(_("Vision: this looks like {k}.").format(k=kind))
        our_kind = self._classify(fd)
        if vision.disagrees(our_kind, reading.get("kind", "")):
            self._log_disagreement(fd, our_kind, reading)

    def _log_disagreement(self, fd, our_kind, reading):
        """Append one disagreement to the local log: the field's STRUCTURAL
        signals plus what each side said. Never the current value or anything the
        user typed. Nothing leaves the machine unless the user presses Share."""
        try:
            entry = {
                "platform": self._detect_platform(fd),
                "id": fd.id, "role": fd.role, "placeholder": fd.placeholder,
                "dom_class": getattr(fd, "dom_class", ""),
                "haspopup": getattr(fd, "haspopup", ""),
                "states": list(getattr(fd, "states", ()) or ()),
                "we_said": our_kind,
                "vision_said": reading.get("kind", ""),
                "vision_label": reading.get("label", ""),
            }
            path = os.path.join(self._data_dir(), "vision_disagreements.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            log.info("JFF vision: logged a disagreement (%s vs %s)"
                     % (our_kind, reading.get("kind", "")))
        except Exception:
            log.error("JFF vision: could not log disagreement", exc_info=True)

    def _openVisionSettings(self):
        """A small dialog to turn vision on or off, choose a backend, and share
        the local disagreement log with the developer. This is the only new UI the
        vision feature adds; the fill commands are unchanged."""
        s = self._vision_settings()
        backends = [("gemini", _("Google Gemini (free key; best quality)")),
                    ("mistral", _("Mistral (free key; best privacy)")),
                    ("groq", _("Groq (free key; fast, private)")),
                    ("ollama", _("Ollama (local, private; needs setup)")),
                    ("pollinations", _("Pollinations (needs a token)")),
                    ("openai_compatible", _("Own key (OpenAI-compatible)"))]
        gui.mainFrame.prePopup()
        try:
            dlg = wx.Dialog(gui.mainFrame, title=_("Job Form Filler: Vision (AI)"))
            root = wx.BoxSizer(wx.VERTICAL)
            enable = wx.CheckBox(dlg, label=_(
                "Use AI vision as a fallback when a field can't be identified "
                "(off by default; sends only the one field's image)"))
            enable.SetValue(bool(s.get("enabled")))
            root.Add(enable, 0, wx.ALL, 8)
            root.Add(wx.StaticText(dlg, label=_("Backend:")), 0, wx.LEFT, 8)
            choice = wx.Choice(dlg, choices=[b[1] for b in backends])
            cur = [i for i, b in enumerate(backends) if b[0] == s.get("backend")]
            choice.SetSelection(cur[0] if cur else 0)
            root.Add(choice, 0, wx.ALL, 8)
            root.Add(wx.StaticText(dlg, label=_(
                "API key (Gemini: get a free one at aistudio.google.com/apikey, "
                "no card needed). Not needed for Ollama:")), 0, wx.LEFT, 8)
            key = wx.TextCtrl(dlg, value=s.get("api_key", ""),
                              style=wx.TE_PASSWORD)
            root.Add(key, 0, wx.EXPAND | wx.ALL, 8)
            root.Add(wx.StaticText(dlg, label=_(
                "Model (leave blank for the backend's default; for Ollama try "
                "llava or qwen2.5vl:3b):")), 0, wx.LEFT, 8)
            model = wx.TextCtrl(dlg, value=s.get("model", ""))
            root.Add(model, 0, wx.EXPAND | wx.ALL, 8)
            root.Add(wx.StaticText(dlg, label=_(
                "Ollama host (only for local Ollama; blank means "
                "localhost:11434):")), 0, wx.LEFT, 8)
            base = wx.TextCtrl(dlg, value=s.get("base_url", ""))
            root.Add(base, 0, wx.EXPAND | wx.ALL, 8)
            share = wx.Button(dlg, label=_("Share disagreement log with "
                                           "developer..."))
            share.Bind(wx.EVT_BUTTON, lambda e: self._shareDisagreements())
            root.Add(share, 0, wx.ALL, 8)
            btns = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)
            root.Add(btns, 0, wx.ALL | wx.ALIGN_RIGHT, 8)
            dlg.SetSizerAndFit(root)
            if dlg.ShowModal() == wx.ID_OK:
                s["enabled"] = enable.GetValue()
                s["backend"] = backends[choice.GetSelection()][0]
                s["api_key"] = key.GetValue()
                s["model"] = model.GetValue().strip()
                s["base_url"] = base.GetValue().strip()
                self._save_vision_settings(s)
                ui.message(_("Vision {state}.").format(
                    state=_("on") if s["enabled"] else _("off")))
            dlg.Destroy()
        finally:
            gui.mainFrame.postPopup()

    def _shareDisagreements(self):
        """Open the local disagreement log so the user can send it to the
        developer. Nothing is uploaded; sharing is entirely the user's choice and
        the file holds only field structure, never their data."""
        path = os.path.join(self._data_dir(), "vision_disagreements.jsonl")
        if not os.path.exists(path):
            ui.message(_("No disagreements recorded yet."))
            return
        try:
            os.startfile(path)  # opens in the default editor for the user to send
            ui.message(_("Opened the disagreement log. It holds only field "
                         "structure, no personal data. Send it to the developer "
                         "if you'd like to contribute."))
        except Exception:
            ui.message(_("The disagreement log is at: {p}").format(p=path))

    def _record_for_field(self, obj):
        """Build one review record for the focused field: classify it, choose the
        editor kind, and read its options if it is a chooser (or its sibling
        radios for a radio group). Used by 'Fill this field' so the same editor
        the review offers is available on the single field the user is on."""
        fd = _descriptor_from_object(obj)
        plat = self._detect_platform(fd)
        if plat:
            log.info("JFF platform: %s" % plat)
        key = matcher.match_field(fd).key
        cc = self._classify(fd)
        kind = controls.editor_kind(cc, key or "", fd.input_type or "")
        # A date-picker combobox (opens a calendar) is a date, not a plain
        # chooser: offer our accessible day/month/year picker and type the result
        # back, so the user never has to navigate the calendar grid.
        if self._is_date_picker(fd):
            kind = controls.EDITOR_DATE
        group, options = None, []
        if cc == controls.RADIO:
            group, radios = self._radio_group(obj)
            options = [r.name for r in radios if (r.name or "").strip()]
            kind = controls.EDITOR_SINGLE
        elif kind in (controls.EDITOR_SINGLE, controls.EDITOR_EDITABLE):
            labels, _o = self._read_option_children(obj, "fill-choice")
            if not labels and cc in (controls.NATIVE_SELECT,
                                     controls.ARIA_COMBOBOX,
                                     controls.EDITABLE_COMBOBOX,
                                     controls.ASYNC_COMBOBOX):
                labels = self._read_select_options(
                    obj, arrow_open=(cc != controls.NATIVE_SELECT))
            options = labels
            if not labels and kind == controls.EDITOR_SINGLE:
                kind = controls.EDITOR_TEXT
        return self._review_record(obj, fd, key, kind, options, group)

    def _looks_like_country_list(self, options):
        """True if a dropdown's options are a list of countries, so we can fill it
        from the profile even when the field has no 'Country' label (select2 and
        similar show only the current value as their label)."""
        if not options or len(options) < 50:
            return False
        opts = set((o or "").strip().lower() for o in options)
        common = ["united kingdom", "united states", "canada", "australia",
                  "germany", "france", "india", "china", "saudi arabia",
                  "brazil", "japan", "italy", "spain"]
        return sum(1 for c in common if c in opts) >= 3

    def _offer_editor(self, obj):
        """The user pressed Fill on a field the add-on can't fill from the
        profile. Open the accessible editor for it (yes/no, chooser, date, or
        type box) so they can set it here, instead of just handing it back.
        Covers every field kind, and writes the choice back. Announces the
        outcome. Returns True if a value was set."""
        try:
            rec = self._record_for_field(obj)
        except Exception:
            log.error("JFF fill: could not build a field record", exc_info=True)
            rec = None
        if rec is None:
            ui.message(_("Over to you."))
            return False
        # If it's clearly a country dropdown (recognised by its options) and we
        # have a country saved, fill it instead of making the user pick from 200.
        country = self._profile.get("country")
        if (country and rec.get("kind") in ("single", "editable")
                and self._looks_like_country_list(rec.get("options"))):
            rec2 = dict(rec)
            rec2["kind"] = "single"
            if self._apply_review_change(rec2, country):
                ui.message(_("Country set to {c}.").format(c=country))
                return True
            # could not set it: fall through to the chooser
        # Vision fallback (opt-in, read-only): we're about to hand this field back
        # because we can't fill it from the profile. If vision is on, look at just
        # this one control and say what it is, logging any disagreement. It runs
        # only here, at the genuine dead-end, so it never delays a successful fill.
        reading = self._vision_identify(obj)
        if reading:
            try:
                self._speak_vision_reading(_descriptor_from_object(obj), reading)
            except Exception:
                log.error("JFF vision: reading failed", exc_info=True)
        gui.mainFrame.prePopup()
        try:
            newval = dialogs.edit_field(gui.mainFrame, rec["name"], rec["kind"],
                                        rec.get("options"), rec["value"])
        finally:
            gui.mainFrame.postPopup()
        if newval is None:
            ui.message(_("Left {name} for you.").format(name=rec["name"]))
            return False
        ok = self._apply_review_change(rec, newval)
        if ok:
            ui.message(_("{name} set.").format(name=rec["name"]))
        else:
            ui.message(_("Could not set {name}. Over to you.").format(
                name=rec["name"]))
        return ok

    @script(
        description=_("Fill the current field from your saved details"),
    )
    def script_fillField(self, gesture, focus=None):
        obj = focus or api.getFocusObject()
        if obj is None:
            ui.message(_("No field is focused."))
            return
        if not self._profile:
            self._critical(_("No details saved yet. Import a CV or enter your "
                             "details first."))
            return
        try:
            import controlTypes
            editable = (controlTypes.State.EDITABLE in obj.states
                        or obj.role in (controlTypes.Role.EDITABLETEXT,
                                        controlTypes.Role.COMBOBOX,
                                        controlTypes.Role.LIST,
                                        controlTypes.Role.SPINBUTTON,
                                        controlTypes.Role.CHECKBOX,
                                        controlTypes.Role.RADIOBUTTON))
        except Exception:
            editable = True  # if unsure, do not block
        if not editable:
            ui.message(_("This isn't a form field. Put your cursor in a field "
                         "and try again."))
            return

        fd = _descriptor_from_object(obj)
        log.info("JFF read: %s" % _fd_summary(fd))
        _plat = self._detect_platform(fd)
        if _plat:
            log.info("JFF platform: %s" % _plat)

        # Radios are special: the object's own label is the option ("Yes"), not
        # the question, so match the group instead of the single radio. Handle it
        # before the normal match, which would bail on the option label.
        early_kind = self._classify(fd)
        if early_kind == controls.RADIO:
            key, pick, verdict = self._fill_radio_group(obj)
            if verdict == "confirmed":
                ui.message(_("{q} set to {a}.").format(
                    q=announce.human(key or _("this")),
                    a=(pick.label if pick else "")))
            else:
                # Not filled from the profile: offer the radio choices here.
                self._offer_editor(obj)
            return

        # Native date input: focus may land on a day/month/year spin button whose
        # own label is "day", not the question. Detect it and fill by segment.
        if (fd.input_type == "date"
                or (fd.role or "").lower() in ("spinbutton", "spin button")):
            key, verdict = self._fill_native_date(obj)
            if verdict == "confirmed":
                ui.message(_("Date of birth set."))
                return
            if verdict == "none":
                pass                 # not actually a date; fall through to match
            else:
                # Recognised as a date but not filled from the profile: offer the
                # date picker here instead of handing it back.
                self._offer_editor(obj)
                return

        result = matcher.match_field(fd)
        log.info("JFF match: key=%r conf=%r src=%r lang=%r"
                 % (result.key, result.confidence, result.source, result.lang))

        # A segmented date (day/month/year dropdowns) has no label, so the matcher
        # can't see it. Recognise it: fill a date of birth from the profile, and
        # for any other date offer the chooser (with a real name) instead of a
        # dead "unlabelled field".
        seg = self._date_segment(fd)
        if result.key is None and seg:
            if self._is_dob_field(fd) and self._profile.get("date_of_birth"):
                if self._fill_dob_segment(obj, fd, seg):
                    ui.message(_("Date of birth {seg} set.").format(seg=seg))
                    return
            self._offer_editor(obj)
            return

        if result.key is None:
            # Not identified from the profile, but still let the user set it here
            # with the accessible editor instead of just handing it back.
            log.info("JFF action: no confident match, offering the editor")
            self._offer_editor(obj)
            return

        value = self._value_for(result.key)
        if not value:
            # Identified, but nothing saved for it: offer the editor to set it.
            self._offer_editor(obj)
            return

        kind = self._classify(fd)

        if kind == controls.CHECKBOX:
            # A checkbox is a yes/no control. If the matched value is free text
            # (a name, a country), the match is wrong (e.g. Workday's
            # "I have a preferred name" box, id name--preferredCheck, matching
            # full_name). Never toggle it from that; offer Yes/No instead.
            if not _is_boolean_value(value):
                self._offer_editor(obj)
                return
            verdict = self._fill_checkbox(obj, fd, value)
            ui.message(announce.choice_set(
                fd.label or announce.human(result.key), value, verdict))
            return
        if (result.key == "date_of_birth" or fd.input_type == "date"
                or kind == controls.DATEPICKER):
            verdict = self._fill_date(obj, fd, value)
            label = fd.label or announce.human(result.key)
            if verdict == "confirmed":
                ui.message(_("{f} set to {v}.").format(f=label, v=value))
            else:
                ui.message(announce.hand_back(label, controls.DATEPICKER, value))
            return
        if kind == controls.TEXT:
            self._fill_text(obj, fd, result, value)
        else:
            self._fill_choice(obj, fd, kind, result, value)

    def _value_for(self, key):
        """Profile value for a matched key. Synthesises full_name from
        given_name and family_name when the profile stores the parts
        separately, so a single 'Full name' field (Lever and many others use
        one) still gets filled."""
        if not key:
            return None
        v = self._profile.get(key)
        if not v and key == "full_name":
            given = (self._profile.get("given_name") or "").strip()
            family = (self._profile.get("family_name") or "").strip()
            v = (given + " " + family).strip() or None
        return v

    @script(
        description=_("Fill the whole form from your saved details"),
    )
    def script_fillForm(self, gesture, focus=None):
        focus = focus or api.getFocusObject()
        if not self._profile:
            self._critical(_("No details saved yet. Import a CV or enter your "
                             "details first."))
            return
        ti = getattr(focus, "treeInterceptor", None)
        if ti is None or not isinstance(ti, browseMode.BrowseModeDocumentTreeInterceptor):
            log.info("JFF form: not a browse-mode document; use single-field fill")
            ui.message(_("Put the cursor in the web page first."))
            return

        try:
            start = ti.makeTextInfo(textInfos.POSITION_FIRST)
            items = list(ti._iterNodesByType("formField", "next", start))
        except Exception:
            log.error("JFF form: could not enumerate form fields", exc_info=True)
            ui.message(_("Could not read the form."))
            return

        # Resolve every field to a solid object reference BEFORE we paste
        # anything. Pasting mutates the page, which invalidates any positions we
        # have not used yet, so we must capture the objects while positions are
        # still valid.
        objs = []
        for item in items:
            o = _obj_from_item(item)
            if o is not None:
                objs.append(o)
        log.info("JFF form: found %d form fields, resolved %d objects"
                 % (len(items), len(objs)))
        filled, guessed, leftovers, prefilled = [], [], [], []
        processed_radio = set()
        processed_multi = set()
        processed_date = set()
        native_date_left = False
        # Only these roles are fillable fields. Everything else NVDA enumerates
        # as a "form field" (buttons, links, the React-Select dropdown toggles,
        # upload widgets) is not a field the user must fill, so it must never
        # land in the summary as "needs you".
        fillable_roles = (
            controlTypes.Role.EDITABLETEXT, controlTypes.Role.COMBOBOX,
            controlTypes.Role.LIST, controlTypes.Role.LISTITEM,
            controlTypes.Role.CHECKBOX, controlTypes.Role.RADIOBUTTON,
            controlTypes.Role.SPINBUTTON,
        )

        for obj in objs:
            fd = _descriptor_from_object(obj)

            # Native date: browse mode may enumerate it as the day/month/year
            # spin buttons OR as a single "show date picker" button. In both
            # cases the date input container holds the segments; find it and fill
            # once from a segment.
            date_container = None
            if (obj.role == controlTypes.Role.SPINBUTTON
                    or fd.input_type == "date"):
                date_container = obj
                if len(self._collect_spinbuttons(obj)) < 2:
                    node = obj
                    for _step in range(4):
                        try:
                            p = node.parent
                        except Exception:
                            p = None
                        if p is None:
                            break
                        if len(self._collect_spinbuttons(p)) >= 2:
                            date_container = p
                            break
                        node = p
            elif obj.role == controlTypes.Role.BUTTON:
                try:
                    if len(self._collect_spinbuttons(obj.parent)) >= 2:
                        date_container = obj.parent
                    else:
                        # Segments not reachable from the button in browse mode.
                        # Still recognise it as a date so it is named clearly and
                        # the user is told exactly what to do.
                        pfd = _descriptor_from_object(obj.parent)
                        hint = ((fd.label or "") + " " + (fd.placeholder or "")
                                + " " + (pfd.label or "")).lower()
                        if pfd.input_type == "date" or "date" in hint:
                            native_date_left = True
                            leftovers.append(announce.human("date_of_birth"))
                            log.info("JFF form field: native date left "
                                     "(segments unreachable in whole-form)")
                            continue
                except Exception:
                    date_container = None
            if date_container is not None:
                did = str(id(date_container))
                if did in processed_date:
                    continue
                segs = self._collect_spinbuttons(date_container)
                seg0 = segs[0] if segs else obj
                key, verdict = self._fill_native_date(seg0)
                if verdict != "none":
                    processed_date.add(did)
                    if verdict == "confirmed":
                        filled.append("date_of_birth")
                        log.info("JFF form field: native date set")
                    else:
                        leftovers.append(announce.human("date_of_birth"))
                    continue

            # Skip controls that are not fillable fields (buttons, links, the
            # dropdown toggles, upload widgets). Date buttons were handled above.
            # Without this, NVDA's form-field enumeration floods the summary with
            # "Apply, Submit, Toggle flyout, Dropbox, ..." that are not fields.
            if obj.role not in fillable_roles:
                log.info("JFF form field: skip non-fillable %s %r"
                         % (obj.role, fd.label or fd.name or ""))
                continue

            # Multi-select: browse mode enumerates the option listitems, not the
            # listbox, so handle the parent listbox once from any of its options.
            try:
                parent = obj.parent if obj.role == controlTypes.Role.LISTITEM \
                    else None
                parent_multi = (parent is not None and
                                controlTypes.State.MULTISELECTABLE in parent.states)
            except Exception:
                parent, parent_multi = None, False
            if parent_multi:
                lfd = _descriptor_from_object(parent)
                lid = lfd.label or lfd.id or str(id(parent))
                if lid in processed_multi:
                    continue
                processed_multi.add(lid)
                lresult = matcher.match_field(lfd)
                lvalue = self._profile.get(lresult.key) if lresult.key else None
                if lresult.key and lvalue:
                    verdict, selected = self._fill_multiselect(parent, [lvalue])
                    if verdict == "confirmed":
                        filled.append(lresult.key)
                        log.info("JFF form field: multi-select %r set to %r"
                                 % (lresult.key, selected))
                    else:
                        leftovers.append(lfd.label
                                         or announce.human(lresult.key))
                else:
                    leftovers.append(lfd.label or _("a multi-select"))
                continue

            # Radios first: the object's own label is the option, not the
            # question, so the standard match would bail. Handle the group once.
            early_kind = self._classify(fd)
            if early_kind == controls.RADIO:
                group, radios = self._radio_group(obj)
                gid = ""
                try:
                    gid = (group.name if group is not None else "") or ""
                except Exception:
                    gid = ""
                gid = gid or fd.name or str(id(group))
                if gid in processed_radio:
                    continue
                processed_radio.add(gid)
                key, pick, verdict = self._fill_radio_group(obj, group, radios)
                qname = gid if gid else announce.human(key or "")
                if verdict == "confirmed":
                    (guessed if (pick and pick.confidence == "guess")
                     else filled).append(key)
                    log.info("JFF form field: radio %r set to %r"
                             % (key, pick.label if pick else ""))
                else:
                    leftovers.append(qname)
                    log.info("JFF form field: radio %r not set (verdict=%s)"
                             % (key, verdict))
                continue

            result = matcher.match_field(fd)
            log.info("JFF form field: %s -> key=%r conf=%r"
                     % (_fd_summary(fd), result.key, result.confidence))

            if result.key is None:
                leftovers.append(fd.label or _("an unlabelled field"))
                continue
            value = self._value_for(result.key)
            if not value:
                leftovers.append(announce.human(result.key))
                continue

            kind = self._classify(fd)

            if kind == controls.CHECKBOX:
                # A checkbox is yes/no. If the value is free text (a name), the
                # match is wrong (Workday's preferred-name box matching full_name):
                # leave it for the user rather than toggling it.
                if not _is_boolean_value(value):
                    leftovers.append(fd.label or announce.human(result.key))
                    continue
                # Only auto-toggle when the state is wrong; a checkbox already in
                # the wanted state is left alone (and counts as done).
                verdict = self._fill_checkbox(obj, fd, value)
                if verdict == "confirmed":
                    filled.append(result.key)
                    log.info("JFF form field: checkbox %r set" % result.key)
                else:
                    leftovers.append(fd.label or announce.human(result.key))
                continue

            if result.key == "date_of_birth" or kind == controls.DATEPICKER:
                # Text date field (a native input was handled above as segments);
                # format to the field's own hint or the country-implied order.
                verdict = self._fill_date(obj, fd, value)
                if verdict == "confirmed":
                    filled.append(result.key)
                    log.info("JFF form field: date %r set" % result.key)
                else:
                    leftovers.append(fd.label or announce.human(result.key))
                continue

            if kind == controls.MULTISELECT:
                verdict, selected = self._fill_multiselect(obj, [value])
                if verdict == "confirmed":
                    filled.append(result.key)
                    log.info("JFF form field: multi-select %r set to %r"
                             % (result.key, selected))
                else:
                    leftovers.append(fd.label or announce.human(result.key))
                continue

            if kind in (controls.NATIVE_SELECT, controls.ARIA_COMBOBOX):
                # A dropdown always has a value, often a placeholder. Only fill
                # when it is still on a placeholder; a real selection is left for
                # the user to review, like a pre-filled text field.
                try:
                    existing = obj.value
                except Exception:
                    existing = None
                if existing and not _is_placeholder_value(existing):
                    log.info("JFF form field: %r dropdown already on %r, left "
                             "as-is" % (result.key, existing))
                    prefilled.append(fd.label or announce.human(result.key))
                    continue
                concept = result.key if result.key in ("country", "nationality") else ""
                pick, verdict = self._fill_native_select(obj, value, concept)
                if verdict == "confirmed":
                    bucket = (guessed if (pick and pick.confidence == "guess")
                              else filled)
                    bucket.append(result.key)
                    log.info("JFF form field: %r dropdown set to %r"
                             % (result.key, pick.label if pick else value))
                else:
                    leftovers.append(fd.label or announce.human(result.key))
                    log.info("JFF form field: %r dropdown not set (verdict=%s)"
                             % (result.key, verdict))
                continue

            if kind != controls.TEXT:
                # multi-select, date picker, async search box, radio, checkbox:
                # these genuinely need the user for now.
                leftovers.append(fd.label or announce.human(result.key))
                log.info("JFF form field: %r is %s, left for you"
                         % (result.key, kind))
                continue

            # Skip fields that already hold a value, so we do not clobber them.
            # An ATS that auto-parsed the CV often puts a WRONG value here; we do
            # not overwrite it (we cannot know it is wrong), but we log it so the
            # mangled value is visible, and the review list lets the user fix it.
            try:
                existing = obj.value
            except Exception:
                existing = None
            if existing:
                log.info("JFF form field: %r already holds %r, left as-is "
                         "(use Review fields to correct it)"
                         % (result.key, existing))
                prefilled.append(fd.label or announce.human(result.key))
                continue

            # Focus the field, then paste, but ONLY once we've confirmed focus
            # actually landed on this field. setFocus is not always synchronous,
            # so if focus has not moved we skip and leave the field for the user,
            # rather than pasting the value into whatever still holds focus.
            try:
                target_id = fd.id
                moved = False
                for _attempt in range(3):
                    obj.setFocus()
                    api.setFocusObject(obj)
                    focused_now = api.getFocusObject()
                    foc_id = (getattr(focused_now, "IA2Attributes", {}) or {}).get("id", "")
                    if not target_id or not foc_id or foc_id == target_id:
                        moved = True
                        break
                    time.sleep(0.05)
                if not moved:
                    log.info("JFF form: focus did not land on %r (still on %r), "
                             "skipping to stay safe" % (target_id, foc_id))
                    leftovers.append(fd.label or announce.human(result.key))
                    continue
                _paste_into_focused(obj, value)
                log.info("JFF form action: filled %r with %r" % (result.key, value))
                (guessed if result.confidence == "guess" else filled).append(result.key)
            except Exception:
                log.error("JFF form action: failed on %r" % result.key, exc_info=True)
                leftovers.append(announce.human(result.key))

        summary = announce.build_summary(filled, guessed, leftovers)
        if native_date_left:
            summary += " " + _("For the date, put your cursor on it and press "
                               "fill this field.")
        if prefilled:
            summary += " " + _("{n} field(s) already had values; open Review "
                               "fields to check them.").format(n=len(prefilled))
        log.info("JFF form summary: %s (prefilled: %d)" % (summary, len(prefilled)))
        # Delay so the last field's focus announcement does not cancel this.
        wx.CallLater(400, ui.message, summary)

    # --- text ----------------------------------------------------------------
    def _fill_text(self, obj, fd, result, value):
        try:
            _paste_into_focused(obj, value)
        except Exception:
            log.error("JFF action: paste FAILED for %r" % result.key, exc_info=True)
            ui.message(_("Could not fill {field}.").format(
                field=announce.human(result.key)))
            return
        log.info("JFF action: filled text %r with %r (conf=%s)"
                 % (result.key, value, result.confidence))
        note = _(" (please check)") if result.confidence == "guess" else ""
        ui.message(_("{field} filled{note}.").format(
            field=announce.human(result.key), note=note))

    # --- choice --------------------------------------------------------------
    def _fill_choice(self, obj, fd, kind, result, value):
        label = fd.label or announce.human(result.key)

        if kind == controls.MULTISELECT:
            verdict, selected = self._fill_multiselect(obj, [value])
            if verdict == "confirmed":
                ui.message(_("{f} set to {v}.").format(
                    f=label, v=", ".join(selected)))
            else:
                ui.message(announce.hand_back(label, kind, value))
            return

        # Platform routing: Workday's comboboxes are type-to-filter (you type,
        # then press Enter), so the typing path is the reliable fill even when the
        # markup doesn't flag the field editable. Route Workday select comboboxes
        # there. Country/nationality keep the option-reading path, which our data
        # set drives across languages.
        if (self._detect_platform(fd) == "workday"
                and kind in (controls.ARIA_COMBOBOX, controls.EDITABLE_COMBOBOX)
                and result.key not in ("country", "nationality")):
            log.info("JFF platform: workday combobox -> type-and-Enter")
            kind = controls.ASYNC_COMBOBOX

        if kind == controls.ASYNC_COMBOBOX:
            verdict, pick = self._fill_async_combobox(obj, value)
            if verdict == "confirmed":
                ui.message(_("{f} set to {v}.").format(
                    f=label, v=(pick.label if pick else value)))
            else:
                ui.message(announce.hand_back(label, kind, value))
            return

        # Controls we deliberately do not automate yet: hand back clearly.
        if kind == controls.DATEPICKER:
            verdict = self._fill_date(obj, fd, value)
            if verdict == "confirmed":
                ui.message(_("{f} set to {v}.").format(f=label, v=value))
            else:
                ui.message(announce.hand_back(label, kind, value))
            return

        concept = result.key if result.key in ("country", "nationality") else ""
        pick, verdict = self._fill_native_select(obj, value, concept)
        if verdict in ("confirmed", "mismatch"):
            ui.message(announce.choice_set(label, pick.label, verdict))
            return
        # Could not read/choose (nothing matched, or options unreadable).
        ui.message(announce.hand_back(label, kind, value))

    def _read_option_children(self, root, tag, depth=0):
        """Collect (label, obj) for option-like descendants of root, logging each
        so the real tree is visible. Chrome nests native-select options inside a
        LIST (or menu) child of the combobox, so recurse into containers."""
        LI = controlTypes.Role.LISTITEM
        MI = controlTypes.Role.MENUITEM
        CONTAINERS = {controlTypes.Role.LIST, controlTypes.Role.MENU,
                      controlTypes.Role.POPUPMENU, controlTypes.Role.GROUPING,
                      controlTypes.Role.COMBOBOX}
        labels, opts = [], []
        if depth > 3:
            return labels, opts
        try:
            kids = list(root.children or [])
        except Exception:
            kids = []
        if depth == 0:
            try:
                rrole = getattr(root.role, "name", "?")
            except Exception:
                rrole = "?"
            log.info("JFF nsel[%s]: root role=%s children=%d"
                     % (tag, rrole, len(kids)))
        for c in kids:
            try:
                role = c.role
            except Exception:
                role = None
            try:
                nm = c.name or ""
            except Exception:
                nm = ""
            if role in (LI, MI) and nm:
                labels.append(nm)
                opts.append(c)
            elif role in CONTAINERS:
                sub_l, sub_o = self._read_option_children(c, tag, depth + 1)
                labels.extend(sub_l)
                opts.extend(sub_o)
        return labels, opts

    def _active_descendant(self, obj):
        """Read the option a combobox currently highlights via aria-activedescendant.
        Chrome exposes it as the container's accFocus, so a type-to-filter prompt
        (Workday) reveals its highlighted match here even when the listbox reads as
        empty. Returns (name, childObj) or ("", None). Read-only: it sends no key
        and never touches the mouse, it only reads, and any failure returns empty so
        callers fall back to today's behaviour."""
        try:
            iao = getattr(obj, "IAccessibleObject", None)
            if iao is None:
                return "", None
            focused = iao.accFocus
        except Exception:
            return "", None
        # CHILDID_SELF or a numeric child id we can't resolve here: nothing to read.
        if focused is None or isinstance(focused, int):
            return "", None
        try:
            import oleacc
            from NVDAObjects.IAccessible import IAccessible as _IA
            child_ia = focused.QueryInterface(oleacc.IAccessible)
            child = _IA(IAccessibleObject=child_ia, IAccessibleChildID=0)
            name = (child.name or "").strip()
        except Exception:
            return "", None
        if name:
            log.info("JFF nsel: aria-activedescendant -> %r" % name)
        return name, child

    def _options_via_controls(self, obj):
        """Read a combobox's options straight from the listbox it points at with
        aria-controls, using NVDA's controllerFor relation. This finds a listbox
        rendered far from the combobox (a portal at the end of the body), which
        walking the parent tree would miss. If that listbox reads empty, as a
        type-to-filter prompt does until you type, fall back to the single option
        the widget highlights via aria-activedescendant. Returns (labels, opts) or
        ([], []). Read-only: no keys, no mouse."""
        try:
            targets = obj.controllerFor or []
        except Exception:
            targets = []
        log.info("JFF nsel: aria-controls targets=%d" % len(targets))
        for target in targets:
            try:
                labels, opts = self._read_option_children(target, "aria-controls")
                if labels:
                    log.info("JFF nsel: read %d option(s) via aria-controls"
                             % len(labels))
                    return labels, opts
            except Exception:
                continue
        # The controlled listbox was absent or empty (a type-to-filter prompt shows
        # nothing until typed). Offer the highlighted option, which is the widget's
        # own state, not a stray document match.
        name, child = self._active_descendant(obj)
        if name and child is not None:
            return [name], [child]
        return [], []

    def _read_select_options(self, obj, arrow_open=False):
        """Read a dropdown's option labels by briefly opening it, then Escape to
        close, leaving the selection unchanged. Returns labels, or [].

        SAFETY: this never touches the mouse. It only sends keys, and only after
        confirming the field actually holds focus, so a key can never land
        anywhere but the field. alt+downArrow opens a native <select>; a plain
        downArrow opens a react-select / custom combobox (this is exactly what a
        user does by hand). arrow_open enables the plain-Down path; it is off for
        native selects, where a plain Down would move the selection."""
        # Fast path: read the controlled listbox via aria-controls, no opening.
        labels, _opts = self._options_via_controls(obj)
        if labels:
            return labels
        # Focus the field, and CONFIRM focus landed on it before sending any key.
        try:
            obj.setFocus()
            api.setFocusObject(obj)
            time.sleep(0.12)
        except Exception:
            log.error("JFF review: could not focus select", exc_info=True)
            return []
        foc = api.getFocusObject()
        same = False
        try:
            fid = (getattr(foc, "IA2Attributes", {}) or {}).get("id", "")
            oid = (getattr(obj, "IA2Attributes", {}) or {}).get("id", "")
            same = (foc is obj) or (bool(fid) and fid == oid)
        except Exception:
            same = (foc is obj)
        if not same:
            log.info("JFF review: focus did not land on the dropdown; not "
                     "sending any key (staying safe)")
            return []
        # Focus mode, so the key reaches the control and not browse navigation.
        ti = getattr(obj, "treeInterceptor", None)
        prev_pt = None
        if ti is not None and hasattr(ti, "passThrough"):
            try:
                prev_pt = ti.passThrough
                ti.passThrough = True
                time.sleep(0.05)
            except Exception:
                prev_pt = None
        openers = ["alt+downArrow"] + (["downArrow"] if arrow_open else [])
        labels = []
        for opener in openers:
            try:
                KeyboardInputGesture.fromName(opener).send()
            except Exception:
                continue
            # Async prompts (Workday) open an empty shell first and render their
            # options a moment later, taking a beat to settle on expanded, so poll
            # a few times before giving up instead of reading once. We only RE-READ
            # here, never re-press: alt+downArrow and downArrow open the list, and
            # if it is already open they only move the highlight, never commit.
            # (Enter would commit a value, so we never send it to open.)
            for _ in range(4):
                time.sleep(0.3)
                labels = self._read_open_menu(obj)
                if labels:
                    break
            if labels:
                log.info("JFF review: %s opened the menu, read %d option(s) "
                         "(polled for async render)" % (opener, len(labels)))
                break
        try:
            KeyboardInputGesture.fromName("escape").send()
            time.sleep(0.1)
        except Exception:
            pass
        if prev_pt is not None:
            try:
                ti.passThrough = prev_pt
            except Exception:
                pass
        if not labels:
            log.info("JFF review: opened select, polled, read 0 option(s)")
        return labels

    def _read_open_menu(self, obj):
        """After a dropdown is open, read its option labels wherever the menu
        rendered: via aria-controls, via a walk from the focus, or by a bounded
        search of the document (react-select portals the menu to the body)."""
        labels, _opts = self._options_via_controls(obj)  # menu now exists
        if labels:
            return labels
        foc = api.getFocusObject()
        for root in ([foc.parent, foc] if foc is not None else []):
            if root is None:
                continue
            try:
                labels, _o = self._read_option_children(root, "menu-open")
            except Exception:
                labels = []
            if labels:
                return labels
        # No reliable options found. We deliberately do NOT walk the whole
        # document for stray list items: that grabbed unrelated values from
        # elsewhere on the page (a different field's committed value), and offered
        # them as options here, which is worse than offering nothing. Correctly
        # built widgets are already read above via aria-controls. Returning empty
        # lets the caller be honest ("type to search this field") rather than
        # invent an option from a blind, leak-prone guess.
        log.info("JFF review: no options readable for this field "
                 "(no aria-controls, no readable menu); not guessing")
        return []

    def _fill_native_select(self, obj, value, concept):
        """Open a native <select>, read its options from the popup, choose the
        best match (locale aware), select that option, and verify. Returns
        (pick, verdict) where verdict is confirmed/mismatch/none/unknown."""
        # Open the popup so the options exist in the tree.
        try:
            obj.setFocus()
            api.setFocusObject(obj)
            time.sleep(0.1)
            KeyboardInputGesture.fromName("alt+downArrow").send()
            time.sleep(0.35)
        except Exception:
            log.error("JFF nsel: could not open the select", exc_info=True)
            return None, "unknown"

        foc = api.getFocusObject()
        try:
            frole = getattr(foc.role, "name", "?")
            fname = foc.name or ""
        except Exception:
            frole, fname = "?", ""
        log.info("JFF nsel: after open, focus role=%s name=%r" % (frole, fname))

        # A long list takes a moment to read from the tree. Say so, rather than
        # leaving the user in silence, on lists long enough to notice.
        try:
            setsize = int((getattr(foc, "IA2Attributes", {}) or {}).get("setsize")
                          or (getattr(obj, "IA2Attributes", {}) or {}).get("setsize")
                          or 0)
        except Exception:
            setsize = 0
        if setsize > 40:
            ui.message(_("Reading the list, one moment."))

        labels, opts = [], []
        roots = []
        if foc is not None:
            par = None
            try:
                par = foc.parent
            except Exception:
                par = None
            if par is not None:
                roots.append((par, "focus.parent"))
            roots.append((foc, "focus"))
        for root, tag in roots:
            labels, opts = self._read_option_children(root, tag)
            if labels:
                break
        if not labels:
            # Parent-walk found nothing: the listbox may be a portal, far from
            # the combobox. Follow aria-controls straight to it.
            labels, opts = self._options_via_controls(obj)
        log.info("JFF nsel: read %d option(s): %r" % (len(labels), labels[:20]))

        if not labels:
            try:
                KeyboardInputGesture.fromName("escape").send()
            except Exception:
                pass
            return None, "unknown"

        pick = controls.choose_option(value, labels, concept=concept)
        log.info("JFF nsel: value=%r -> idx=%r label=%r conf=%r"
                 % (value, pick.index, pick.label, pick.confidence))
        if pick.index is None:
            try:
                KeyboardInputGesture.fromName("escape").send()
            except Exception:
                pass
            return pick, "none"

        # Select synchronously via the option object's accessibility action.
        # Keyboard selection queues behind the running script and does not take
        # effect until the whole fill returns, which breaks verification and
        # multi-select forms; acting on the object applies immediately.
        target = opts[pick.index] if pick.index < len(opts) else None
        selected = False
        if target is not None:
            try:
                target.doAction()
                selected = True
                log.info("JFF nsel: selected via option doAction")
            except Exception:
                log.error("JFF nsel: doAction failed", exc_info=True)
        if not selected:
            self._arrow_select(obj, pick.index)

        # Verify it actually STUCK. A SAP/SuccessFactors <select> can read the
        # chosen option back transiently after doAction, then leave the native
        # field on its "- Select -" placeholder, which the old check confirmed as
        # success: the false confirm seen live on STC Country ("set to Saudi
        # Arabia" while the field stayed "- Select -, required"). So let it
        # settle, read the live committed value, and NEVER confirm a placeholder.
        after = self._settled_value(obj)
        verdict = ("mismatch" if _is_placeholder_value(after)
                   else controls.verify_selection(pick.label, after))
        if verdict != "confirmed":
            # Did not commit. Re-select by keyboard, which changes the native
            # select's value and fires its onchange the way a user does.
            self._arrow_select(obj, pick.index)
            after = self._settled_value(obj)
            verdict = ("mismatch" if _is_placeholder_value(after)
                       else controls.verify_selection(pick.label, after))
        log.info("JFF nsel: after=%r verdict=%r" % (after, verdict))
        return pick, verdict

    def _settled_value(self, obj):
        """Read a choice control's committed value AFTER the page's onchange and
        validation have settled, so a transient post-doAction value can't be
        mistaken for a real, stuck selection."""
        time.sleep(0.4)
        return self._read_current_value(obj)

    def _arrow_select(self, obj, index):
        """Commit a native <select> by keyboard: focus it, go Home, then Down to
        the target option. This changes the field's value and fires its native
        change/onchange the way a user does, and never touches the mouse."""
        try:
            ti = getattr(obj, "treeInterceptor", None)
            if ti is not None and hasattr(ti, "passThrough"):
                ti.passThrough = True
            obj.setFocus()
            api.setFocusObject(obj)
            time.sleep(0.08)
            KeyboardInputGesture.fromName("escape").send()
            time.sleep(0.05)
            KeyboardInputGesture.fromName("home").send()
            time.sleep(0.05)
            for _k in range(index):
                KeyboardInputGesture.fromName("downArrow").send()
                time.sleep(0.03)
        except Exception:
            log.error("JFF nsel: keyboard select failed", exc_info=True)

    def _read_current_value(self, obj):        # Read the LIVE value via a raw IA2 call; NVDA caches obj.value on the
        # object instance, so repeated polls would re-read a stale cached value.
        try:
            iao = getattr(obj, "IAccessibleObject", None)
            if iao is not None:
                cid = getattr(obj, "IAccessibleChildID", 0)
                v = iao.accValue(cid)
                if v:
                    return v
        except Exception:
            pass
        try:
            return obj.value or ""
        except Exception:
            return ""

    def _live_checked(self, obj):
        """Live checked/selected state via raw IA2 accState (NVDA caches states),
        so verifying a radio or checkbox does not read a stale value."""
        CHECKED = 0x10           # STATE_SYSTEM_CHECKED
        SELECTED = 0x2           # STATE_SYSTEM_SELECTED
        try:
            iao = getattr(obj, "IAccessibleObject", None)
            if iao is not None:
                cid = getattr(obj, "IAccessibleChildID", 0)
                st = iao.accState(cid)
                if isinstance(st, int):
                    return bool(st & (CHECKED | SELECTED))
        except Exception:
            pass
        try:
            S = controlTypes.State
            return (S.CHECKED in obj.states) or (S.SELECTED in obj.states)
        except Exception:
            return False

    def _radio_group(self, obj):
        """Find a radio's group container and its sibling radio options. Logs the
        parent chain so the real tree is visible for the first runs."""
        RB = controlTypes.Role.RADIOBUTTON
        chain = []
        node = obj
        group = None
        for _k in range(4):
            try:
                parent = node.parent
            except Exception:
                parent = None
            if parent is None:
                break
            try:
                prole = parent.role
                pname = parent.name or ""
            except Exception:
                prole, pname = None, ""
            chain.append((getattr(prole, "name", "?"), pname))
            # count radios directly under this parent
            radios = self._collect_radios(parent)
            if len(radios) >= 2:
                group = parent
                log.info("JFF radio: group at role=%s name=%r with %d options; "
                         "chain=%r" % (getattr(prole, "name", "?"), pname,
                                       len(radios), chain))
                return group, radios
            node = parent
        log.info("JFF radio: no multi-radio group found; chain=%r" % chain)
        return None, [obj]

    def _collect_radios(self, root, depth=0):
        RB = controlTypes.Role.RADIOBUTTON
        out = []
        if depth > 3:
            return out
        try:
            kids = list(root.children or [])
        except Exception:
            kids = []
        for c in kids:
            try:
                role = c.role
            except Exception:
                role = None
            if role == RB:
                out.append(c)
            else:
                out.extend(self._collect_radios(c, depth + 1))
        return out

    def _fill_radio_group(self, obj, group=None, radios=None):
        """Handle a radio as part of its group: find the question, match it to a
        saved detail, select the matching option, verify. Returns (key, pick,
        verdict) with verdict confirmed/mismatch/none/novalue."""
        if group is None and radios is None:
            group, radios = self._radio_group(obj)
        labels = []
        for r in radios:
            try:
                labels.append(r.name or "")
            except Exception:
                labels.append("")
        qlabel = ""
        if group is not None:
            try:
                qlabel = group.name or ""
            except Exception:
                qlabel = ""
        fd = _descriptor_from_object(obj)
        log.info("JFF radio: question=%r options=%r name=%r"
                 % (qlabel, labels, fd.name))
        # Match the question label; fall back to the shared html name / id.
        qfd = matcher.FieldDescriptor(label=qlabel, name=fd.name, id=fd.id,
                                      role="radiogroup")
        result = matcher.match_field(qfd)
        log.info("JFF radio: match key=%r conf=%r src=%r"
                 % (result.key, result.confidence, result.source))
        if result.key is None:
            return None, None, "none"
        value = self._value_for(result.key)
        if not value:
            return result.key, None, "novalue"
        pick = controls.choose_option(
            value, labels,
            concept=result.key if result.key in ("country", "nationality") else "")
        log.info("JFF radio: value=%r -> idx=%r label=%r"
                 % (value, pick.index, pick.label))
        if pick.index is None:
            return result.key, pick, "none"
        target = radios[pick.index]
        try:
            target.doAction()
        except Exception:
            try:
                target.setFocus()
                api.setFocusObject(target)
                KeyboardInputGesture.fromName("space").send()
            except Exception:
                log.error("JFF radio: select failed", exc_info=True)
        verdict = "unknown"
        for _k in range(8):
            if self._live_checked(target):
                verdict = "confirmed"
                break
            time.sleep(0.06)
        if verdict != "confirmed":
            verdict = "mismatch"
        log.info("JFF radio: verdict=%r" % verdict)
        return result.key, pick, verdict

    def _fill_checkbox(self, obj, fd, value):
        """Toggle a checkbox to match a truthy/falsey value. Verifies via live
        state. Most consent boxes have no saved value and reach here only from
        the review list (where the user supplies yes/no)."""
        want = str(value).strip().lower() in (
            "yes", "true", "1", "on", "checked", "y", "نعم", "si", "oui", "ja")
        cur = self._live_checked(obj)
        if cur != want:
            try:
                obj.doAction()
            except Exception:
                try:
                    obj.setFocus()
                    api.setFocusObject(obj)
                    KeyboardInputGesture.fromName("space").send()
                except Exception:
                    log.error("JFF checkbox: toggle failed", exc_info=True)
        now = False
        for _k in range(8):
            now = self._live_checked(obj)
            if now == want:
                break
            time.sleep(0.06)
        verdict = "confirmed" if now == want else "mismatch"
        log.info("JFF checkbox: want=%s now=%s verdict=%s" % (want, now, verdict))
        return verdict

    def _fill_multiselect(self, obj, values):
        """Select the option(s) matching the given value(s) in a multi-select,
        without disturbing options already chosen (a multi-select adds to the
        selection). Verifies each via the live selected state. Returns
        (verdict, [selected labels])."""
        # If focus landed on an option rather than the listbox itself, step up to
        # the container so its options can be read.
        root = obj
        try:
            if obj.role == controlTypes.Role.LISTITEM and obj.parent is not None:
                root = obj.parent
        except Exception:
            pass
        labels, opts = self._read_option_children(root, "multi")
        if not labels:
            log.info("JFF multi: no options read")
            return "unknown", []
        log.info("JFF multi: %d option(s): %r" % (len(labels), labels[:20]))
        selected = []
        for value in values:
            pick = controls.choose_option(value, labels)
            if pick.index is None or pick.index >= len(opts):
                log.info("JFF multi: value=%r no match" % (value,))
                continue
            target = opts[pick.index]
            if not self._live_checked(target):
                try:
                    target.doAction()
                except Exception:
                    try:
                        target.setFocus()
                        api.setFocusObject(target)
                        KeyboardInputGesture.fromName("space").send()
                    except Exception:
                        log.error("JFF multi: select failed", exc_info=True)
            ok = False
            for _k in range(8):
                if self._live_checked(target):
                    ok = True
                    break
                time.sleep(0.06)
            if ok:
                selected.append(pick.label)
            log.info("JFF multi: value=%r -> idx=%r label=%r selected=%s"
                     % (value, pick.index, pick.label, ok))
        return ("confirmed" if selected else "none"), selected

    def _find_listbox(self, root, depth=0):
        """Find a populated listbox near a combobox (the async results)."""
        if depth > 4 or root is None:
            return None
        try:
            kids = list(root.children or [])
        except Exception:
            kids = []
        for c in kids:
            try:
                r = c.role
            except Exception:
                r = None
            if r == controlTypes.Role.LIST:
                labels, _opts = self._read_option_children(c, "async-check")
                if labels:
                    return c
            found = self._find_listbox(c, depth + 1)
            if found is not None:
                return found
        return None

    def _read_async_options(self, obj):
        # The results listbox is usually a sibling of the combobox; search up a
        # couple of ancestors for a populated listbox.
        node = obj
        for _k in range(3):
            try:
                parent = node.parent
            except Exception:
                parent = None
            if parent is None:
                break
            lb = self._find_listbox(parent)
            if lb is not None:
                return self._read_option_children(lb, "async")
            node = parent
        return [], []

    def _fill_async_combobox(self, obj, value):
        """Type into a search-box combobox, wait for options to load over the
        network, then pick the best match. Returns (verdict, pick)."""
        try:
            obj.setFocus()
            api.setFocusObject(obj)
            time.sleep(0.05)
        except Exception:
            pass
        try:
            _paste_into_focused(obj, value)
        except Exception:
            log.error("JFF async: type failed", exc_info=True)
        log.info("JFF async: typed %r, waiting for options" % value)
        labels, opts = [], []
        for _k in range(30):                       # up to ~3s for the fetch
            labels, opts = self._read_async_options(obj)
            if labels:
                log.info("JFF async: %d option(s) after %d polls: %r"
                         % (len(labels), _k, labels[:10]))
                break
            time.sleep(0.1)
        if not labels:
            log.info("JFF async: no options loaded; dumping tree around combobox")
            try:
                par = obj.parent
                for c in (par.children or []):
                    try:
                        cr = getattr(c.role, "name", "?")
                        cn = (c.name or "")[:40]
                        gc = len(list(c.children or []))
                        log.info("JFF async tree: role=%s name=%r kids=%d"
                                 % (cr, cn, gc))
                        if cr in ("list", "listBox"):
                            for gcc in (c.children or []):
                                log.info("JFF async tree:   opt role=%s name=%r"
                                         % (getattr(gcc.role, "name", "?"),
                                            (gcc.name or "")[:40]))
                    except Exception:
                        pass
            except Exception:
                pass
            return "unknown", None
        pick = controls.choose_option(value, labels)
        log.info("JFF async: value=%r -> idx=%r label=%r"
                 % (value, pick.index, pick.label))
        if pick.index is None or pick.index >= len(opts):
            return "none", None
        # Commit by pressing Enter on the combobox: react-select selects the
        # highlighted first filtered result, and the typed value has already
        # filtered the list to the match. doAction on the option node does NOT
        # change the field (it leaves the typed search text, which react-select
        # clears to blank on blur, the false confirm seen live on Monzo Country).
        try:
            obj.setFocus()
            api.setFocusObject(obj)
            time.sleep(0.05)
            KeyboardInputGesture.fromName("enter").send()
            time.sleep(0.35)
        except Exception:
            log.error("JFF async: enter-select failed", exc_info=True)
        # react-select does NOT expose the committed value to the accessibility
        # tree (the input clears and the chosen label is presentational), so we
        # cannot read it back, confirmed by diagnostics: value, description and
        # the surrounding tree are all empty after a successful commit. Instead
        # verify by the mechanism: reaching here means the typed value filtered
        # to a real match, Enter selects react-select's highlighted match, and a
        # committed react-select COLLAPSES its menu. So confirm only if the menu
        # closed. The react-select-test fixture guards this by reading the real
        # onChange value.
        time.sleep(0.3)
        try:
            still_open = controlTypes.State.EXPANDED in obj.states
        except Exception:
            still_open = False
        if still_open:
            log.info("JFF async: still expanded after Enter, not committed")
            return "mismatch", pick
        log.info("JFF async: committed %r via Enter (menu collapsed)" % pick.label)
        return "confirmed", pick

    def _date_segment_type(self, seg):
        try:
            fd = _descriptor_from_object(seg)
            hint = ((seg.name or "") + " " + (fd.placeholder or "")).lower()
        except Exception:
            hint = ""
        if "year" in hint or "yy" in hint:
            return "Y"
        if "month" in hint or "mm" in hint:
            return "M"
        if "day" in hint or "dd" in hint:
            return "D"
        return ""

    def _collect_spinbuttons(self, root, depth=0):
        out = []
        if depth > 3:
            return out
        try:
            kids = list(root.children or [])
        except Exception:
            kids = []
        for c in kids:
            try:
                r = c.role
            except Exception:
                r = None
            if r == controlTypes.Role.SPINBUTTON:
                out.append(c)
            else:
                out.extend(self._collect_spinbuttons(c, depth + 1))
        return out

    def _fill_native_date(self, obj):
        """Fill a native <input type=date> segment by segment. Focus may be on a
        day, month, or year spin button whose own label is not the question, so
        walk up to the date container for the label, then type each segment's
        value in the order the segments appear (which is the browser's display
        order), so it is locale-independent (UK day-first, US month-first).
        Never opens or navigates a calendar grid. Returns (key, verdict)."""
        # Label: the focused segment's own name is like "Month Date of birth";
        # strip the segment words to get the question.
        def _strip_segments(text):
            out = text or ""
            for w in ("day", "month", "year", "hour", "minute",
                      "Day", "Month", "Year", "Hour", "Minute"):
                out = out.replace(w, "")
            return out.strip()
        try:
            label = _strip_segments(_descriptor_from_object(obj).label)
        except Exception:
            label = ""
        # Container: the nearest ancestor that holds the segment spin buttons.
        container = obj
        segs = [obj]
        node = obj
        for _k in range(4):
            try:
                parent = node.parent
            except Exception:
                parent = None
            if parent is None:
                break
            found = self._collect_spinbuttons(parent)
            if len(found) >= 2:
                container, segs = parent, found
                break
            node = parent
        if not label:
            try:
                label = _strip_segments(_descriptor_from_object(container).label)
            except Exception:
                label = ""
        result = matcher.match_field(matcher.FieldDescriptor(label=label))
        log.info("JFF ndate: label=%r key=%r segs=%d"
                 % (label, result.key, len(segs)))
        if result.key != "date_of_birth":
            return result.key, "none"
        value = self._profile.get("date_of_birth")
        if not value:
            return "date_of_birth", "novalue"
        parts = value.split("-")
        if len(parts) != 3:
            return "date_of_birth", "none"
        y, m, d = parts
        seq = ""
        for seg in segs:
            t = self._date_segment_type(seg)
            seq += {"D": d, "M": m, "Y": y}.get(t, "")
        log.info("JFF ndate: typing %r in display order" % seq)
        if not seq:
            return "date_of_birth", "mismatch"
        try:
            first = segs[0]
            first.setFocus()
            api.setFocusObject(first)
            time.sleep(0.06)
            for ch in seq:
                KeyboardInputGesture.fromName(ch).send()
                time.sleep(0.03)
        except Exception:
            log.error("JFF ndate: typing failed", exc_info=True)
        want = sorted(_digits(value))
        after = ""
        for _k in range(8):
            seg_digits = "".join(
                _digits(self._read_current_value(s)) for s in segs)
            cont = _digits(self._read_current_value(container))
            got = seg_digits or cont
            if got and sorted(got) == want:
                log.info("JFF ndate: segments=%r verdict=confirmed" % seg_digits)
                return "date_of_birth", "confirmed"
            after = got
            time.sleep(0.06)
        log.info("JFF ndate: got=%r verdict=mismatch" % after)
        return "date_of_birth", "mismatch"

    def _default_date_order(self):
        # No field hint: use the convention implied by the saved country.
        # United States is MM/DD/YYYY; the UK, Saudi, and most others DD/MM/YYYY.
        c = (self._profile.get("country", "") or "").lower()
        if "united states" in c or c in ("us", "usa", "america"):
            return "MDY"
        return "DMY"

    def _fill_date(self, obj, fd, value):
        """Fill a date field, accounting for format (UK DD/MM/YYYY vs US
        MM/DD/YYYY). value is stored ISO (YYYY-MM-DD). A native input type=date
        holds ISO in the DOM and shows it in the user's locale, so paste ISO. A
        text date field takes a formatted string: use the field's own hint
        (placeholder like DD/MM/YYYY), else the order implied by the saved
        country. Verify by digit set, so a reordered date still confirms."""
        try:
            role = getattr(obj.role, "name", "?")
        except Exception:
            role = "?"
        parts = value.split("-")
        if fd.input_type == "date":
            formatted = value                       # native date input: ISO
        elif len(parts) == 3:
            y, m, d = parts
            hint = fd.placeholder or ""
            if not any(c in hint for c in "/-."):
                hint = ""       # not a format pattern, e.g. a stray label
            order = _date_order_from_hint(hint) or self._default_date_order()
            sep = _date_separator_from_hint(hint, "/")
            formatted = _format_date(y, m, d, order, sep)
        else:
            formatted = value                       # not ISO; paste as given
        before = self._read_current_value(obj)
        log.info("JFF date: role=%s input_type=%r hint=%r before=%r target=%r "
                 "formatted=%r" % (role, fd.input_type, fd.placeholder, before,
                                   value, formatted))
        try:
            obj.setFocus()
            api.setFocusObject(obj)
            time.sleep(0.05)
        except Exception:
            pass
        try:
            _paste_into_focused(obj, formatted)
        except Exception:
            log.error("JFF date: paste failed", exc_info=True)
        want = sorted(_digits(value))
        after = ""
        for _k in range(8):
            after = self._read_current_value(obj)
            if after and sorted(_digits(after)) == want:
                log.info("JFF date: after=%r verdict=confirmed" % after)
                return "confirmed"
            time.sleep(0.06)
        log.info("JFF date: after=%r verdict=unconfirmed" % after)
        return "unconfirmed"
