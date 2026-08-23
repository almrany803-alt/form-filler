# __init__.py - the NVDA layer. It turns the core's decisions into real key
# presses and speech.
#
# IMPORTANT, and stated honestly: this module imports NVDA internals and CANNOT
# run or be tested in the Linux sandbox. It is written to the patterns we
# studied in AI-Hub (focused-field insertion via api.copyToClip + Ctrl+V) and
# clipContentsDesigner (focus/browse-mode handling, keyboard-layout awareness,
# settings panel lifecycle). It needs verification on real Windows + NVDA.

import os
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

from .core import matcher, controls, announce, profile
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
                    (S.HASPOPUP, "haspopup"), (S.MULTISELECTABLE, "multiselectable")):
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
        if kind in ("field", "form", "review"):
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
            from .core import cvparse
            fields = cvparse.cv_to_fields(
                cvparse.parse_cv_text(cvparse.extract_text(path)))
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
                else (fd.label or _("an unlabelled field")))
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
        for obj in objs:
            fd = _descriptor_from_object(obj)
            result = matcher.match_field(fd)
            key = result.key
            cc = controls.classify_control(controls.ControlDescriptor(
                role=fd.role, states=fd.states, autocomplete=fd.autocomplete))

            # Date: one row, three dropdowns in the editor.
            if (key == "date_of_birth" or fd.input_type == "date"
                    or cc == controls.DATEPICKER):
                records.append(self._review_record(
                    obj, fd, key, controls.EDITOR_DATE, [], None))
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
            return self._write_field(obj, fd, newval)
        except Exception:
            log.error("JFF review: writeback failed kind=%r" % kind,
                      exc_info=True)
            return False

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

        # Radios are special: the object's own label is the option ("Yes"), not
        # the question, so match the group instead of the single radio. Handle it
        # before the normal match, which would bail on the option label.
        early_kind = controls.classify_control(controls.ControlDescriptor(
            role=fd.role, states=fd.states, autocomplete=fd.autocomplete))
        if early_kind == controls.RADIO:
            key, pick, verdict = self._fill_radio_group(obj)
            if verdict == "confirmed":
                ui.message(_("{q} set to {a}.").format(
                    q=announce.human(key or _("this")),
                    a=(pick.label if pick else "")))
            elif verdict == "novalue":
                ui.message(_("Nothing saved for {field}.").format(
                    field=announce.human(key)))
            elif verdict == "none" and key is None:
                ui.message(_("I could not identify this question. Over to you."))
            else:
                ui.message(_("Could not set this one. Over to you."))
            return

        # Native date input: focus may land on a day/month/year spin button whose
        # own label is "day", not the question. Detect it and fill by segment.
        if (fd.input_type == "date"
                or (fd.role or "").lower() in ("spinbutton", "spin button")):
            key, verdict = self._fill_native_date(obj)
            if verdict == "confirmed":
                ui.message(_("Date of birth set."))
                return
            if verdict in ("none", "novalue"):
                # fall through to normal handling / decline below
                if verdict == "novalue":
                    ui.message(_("Nothing saved for date of birth."))
                    return
            else:
                ui.message(announce.hand_back(
                    _("the date"), controls.DATEPICKER, ""))
                return

        result = matcher.match_field(fd)
        log.info("JFF match: key=%r conf=%r src=%r lang=%r"
                 % (result.key, result.confidence, result.source, result.lang))

        if result.key is None:
            # Nothing usable: tell the user rather than guessing. The fallback
            # rungs (positional, remembered labels, OCR, AI) hook in here later.
            log.info("JFF action: declined, no confident match")
            ui.message(_("I could not identify this field. Over to you."))
            return

        value = self._profile.get(result.key)
        if not value:
            ui.message(_("Nothing saved for {field}.").format(
                field=announce.human(result.key)))
            return

        kind = controls.classify_control(controls.ControlDescriptor(
            role=fd.role, states=fd.states, autocomplete=fd.autocomplete))

        if kind == controls.CHECKBOX:
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
            early_kind = controls.classify_control(controls.ControlDescriptor(
                role=fd.role, states=fd.states, autocomplete=fd.autocomplete))
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
            value = self._profile.get(result.key)
            if not value:
                leftovers.append(announce.human(result.key))
                continue

            kind = controls.classify_control(controls.ControlDescriptor(
                role=fd.role, states=fd.states, autocomplete=fd.autocomplete))

            if kind == controls.CHECKBOX:
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
                concept = result.key if result.key == "country" else ""
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

        if kind == controls.ASYNC_COMBOBOX:
            verdict, pick = self._fill_async_combobox(obj, value)
            if verdict == "confirmed":
                ui.message(_("{f} set to {v}.").format(
                    f=label, v=(pick.label if pick else value)))
            else:
                ui.message(announce.hand_back(label, kind, value))
            return

        # Controls we deliberately do not automate yet: hand back clearly.
        if kind == controls.ASYNC_COMBOBOX:
            ui.message(announce.hand_back(label, kind, value))
            return
        if kind == controls.DATEPICKER:
            verdict = self._fill_date(obj, fd, value)
            if verdict == "confirmed":
                ui.message(_("{f} set to {v}.").format(f=label, v=value))
            else:
                ui.message(announce.hand_back(label, kind, value))
            return

        concept = result.key if result.key == "country" else ""
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
            log.info("JFF nsel[%s]: d%d role=%s name=%r"
                     % (tag, depth, getattr(role, "name", "?"), nm))
            if role in (LI, MI) and nm:
                labels.append(nm)
                opts.append(c)
            elif role in CONTAINERS:
                sub_l, sub_o = self._read_option_children(c, tag, depth + 1)
                labels.extend(sub_l)
                opts.extend(sub_o)
        return labels, opts

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
            # Fallback: focus mode, then arrow to the index. Works for a single
            # field; unreliable mid-form (kept only as a last resort).
            try:
                ti = getattr(obj, "treeInterceptor", None)
                if ti is not None:
                    ti.passThrough = True
                obj.setFocus()
                api.setFocusObject(obj)
                time.sleep(0.08)
                KeyboardInputGesture.fromName("escape").send()
                time.sleep(0.05)
                KeyboardInputGesture.fromName("home").send()
                time.sleep(0.05)
                for _k in range(pick.index):
                    KeyboardInputGesture.fromName("downArrow").send()
                    time.sleep(0.03)
            except Exception:
                log.error("JFF nsel: arrow fallback failed", exc_info=True)

        # Read back with a few retries: the select's exposed value can lag the
        # keystrokes, and a single early read gives a false mismatch (seen in the
        # whole-form path, where it wrongly marked a filled dropdown "needs you").
        after = ""
        verdict = "unknown"
        for _k in range(8):
            after = self._read_current_value(obj)
            verdict = controls.verify_selection(pick.label, after)
            if verdict == "confirmed":
                break
            time.sleep(0.08)
        log.info("JFF nsel: after=%r verdict=%r" % (after, verdict))
        return pick, verdict

    def _read_current_value(self, obj):
        # Read the LIVE value via a raw IA2 call; NVDA caches obj.value on the
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
        value = self._profile.get(result.key)
        if not value:
            return result.key, None, "novalue"
        pick = controls.choose_option(
            value, labels,
            concept=result.key if result.key == "country" else "")
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
        target = opts[pick.index]
        try:
            target.doAction()
        except Exception:
            try:
                target.setFocus()
                api.setFocusObject(target)
                KeyboardInputGesture.fromName("enter").send()
            except Exception:
                log.error("JFF async: select failed", exc_info=True)
        after = ""
        for _k in range(10):
            after = self._read_current_value(obj)
            if after and (after == pick.label or pick.label in after
                          or value.lower() in after.lower()):
                log.info("JFF async: after=%r verdict=confirmed" % after)
                return "confirmed", pick
            time.sleep(0.06)
        log.info("JFF async: after=%r verdict=mismatch" % after)
        return "mismatch", pick

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
