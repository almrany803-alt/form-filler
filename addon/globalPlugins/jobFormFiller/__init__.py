# __init__.py - the NVDA layer. It turns the core's decisions into real key
# presses and speech.
#
# IMPORTANT, and stated honestly: this module imports NVDA internals and CANNOT
# run or be tested in the Linux sandbox. It is written to the patterns we
# studied in AI-Hub (focused-field insertion via api.copyToClip + Ctrl+V) and
# clipContentsDesigner (focus/browse-mode handling, keyboard-layout awareness,
# settings panel lifecycle). It needs verification on real Windows + NVDA.

import os
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
    autocomplete = {"email": "email", "tel": "tel", "url": "url"}.get(input_type, "")

    # If the only "label" came from the placeholder or a tooltip, treat it as a
    # placeholder (a guess), not a real label (strong).
    label = obj.name or ""
    placeholder = ""
    if ia2.get("name-from", "") in ("placeholder", "tooltip"):
        placeholder, label = label, ""

    return matcher.FieldDescriptor(
        role=role,
        label=label,
        aria_label="",
        name=html_name,
        id=ia2.get("id", ""),
        placeholder=placeholder,
        autocomplete=autocomplete,
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
        # Encrypted profile store, in NVDA's config dir. On Windows the crypto is
        # DPAPI (tied to the user account); the store logic itself is our tested
        # code. self._profile is the active profile the fill commands read.
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
        # Default key; free in stock NVDA. Change it in Input Gestures if it ever
        # clashes with another add-on, under the "Job Form Filler" category.
        gesture="kb:NVDA+shift+f",
    )
    def script_fillField(self, gesture):
        obj = api.getFocusObject()
        if obj is None:
            ui.message(_("No field is focused."))
            return

        fd = _descriptor_from_object(obj)
        result = matcher.match_field(fd)
        log.info("JFF read: %s" % _fd_summary(fd))
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

        if kind == controls.TEXT:
            self._fill_text(obj, fd, result, value)
        else:
            self._fill_choice(obj, fd, kind, result, value)

    @script(
        description=_("Fill the whole form from your saved details"),
        # Default key; change it in Input Gestures if it clashes with an add-on.
        gesture="kb:NVDA+shift+a",
    )
    def script_fillForm(self, gesture):
        focus = api.getFocusObject()
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
        filled, guessed, leftovers = [], [], []

        for obj in objs:
            fd = _descriptor_from_object(obj)
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
            if kind != controls.TEXT:
                # dropdowns and other choice controls are not wired in yet.
                leftovers.append(fd.label or announce.human(result.key))
                log.info("JFF form field: %r is %s, skipped for now"
                         % (result.key, kind))
                continue

            # Skip fields that already hold a value, so we do not clobber them.
            try:
                existing = obj.value
            except Exception:
                existing = None
            if existing:
                log.info("JFF form field: %r already filled, skipping" % result.key)
                continue

            # Focus the field, then paste. THIS is the spot most likely to need
            # tuning: setFocus is not always synchronous, so we log the focused
            # object right before pasting to prove focus actually moved.
            try:
                obj.setFocus()
                api.setFocusObject(obj)
                focused_now = api.getFocusObject()
                log.info("JFF form: focus before paste is id=%r name=%r"
                         % (getattr(focused_now, "IA2Attributes", {}).get("id", ""),
                            focused_now.name))
                _paste_into_focused(obj, value)
                log.info("JFF form action: filled %r with %r" % (result.key, value))
                (guessed if result.confidence == "guess" else filled).append(result.key)
            except Exception:
                log.error("JFF form action: failed on %r" % result.key, exc_info=True)
                leftovers.append(announce.human(result.key))

        summary = announce.build_summary(filled, guessed, leftovers)
        log.info("JFF form summary: %s" % summary)
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

        # Controls we deliberately do not automate: hand back clearly.
        if kind in (controls.MULTISELECT, controls.DATEPICKER, controls.ASYNC_COMBOBOX):
            ui.message(announce.hand_back(label, kind, value))
            return

        # Real build: read the option labels from obj's children/list, then:
        options = self._read_options(obj)                     # -> list[str]
        pick = controls.choose_option(value, options,
                                      concept=result.key if result.key == "country" else "")
        if pick.index is None:
            ui.message(announce.hand_back(label, kind, value))
            return

        self._select_option(obj, pick)                        # pattern or keyboard
        after = self._read_current_value(obj)                 # read it back
        verdict = controls.verify_selection(pick.label, after)
        ui.message(announce.choice_set(label, pick.label, verdict))

    # --- NVDA plumbing to be fleshed out and tested on hardware --------------
    def _read_options(self, obj):
        # From native <select>: iterate obj children (role listItem/option).
        # From an ARIA combobox: open it and read the popped-up listbox.
        return []

    def _select_option(self, obj, pick):
        # Prefer the accessibility selection pattern (UIA SelectionItem.Select /
        # IA2 accSelect). Fall back to: open, typeahead/arrow, commit Enter/Tab.
        pass

    def _read_current_value(self, obj):
        # Re-read the control's exposed value to verify the selection stuck.
        try:
            return obj.value or ""
        except Exception:
            return ""
