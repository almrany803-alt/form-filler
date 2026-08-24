# controls.py - the brain for dropdowns and other choice controls.
#
# The NVDA layer reads the live control (role, states, options, current value)
# and performs the actual selection. THIS module only decides:
#   - what kind of control it is (so the NVDA layer picks the right method)
#   - which option matches the user's value (locale/multilingual aware)
#   - whether a selection actually stuck (verify-back)
# All pure Python, all testable.

from dataclasses import dataclass, field

# The country dataset lives beside this module. Import it robustly: the add-on
# loads these as a package (from .core import controls), while the test harness
# loads them flat (import controls with core/ on the path). Support both, so a
# broken country match can never hide behind a silently-swallowed ImportError.
try:
    from . import countries as _countries
except ImportError:  # pragma: no cover - flat import path (tests)
    try:
        import countries as _countries
    except ImportError:
        _countries = None


@dataclass
class ControlDescriptor:
    role: str = "edit"            # edit, combobox, listbox, button, checkbox, radio...
    states: tuple = ()            # e.g. ("editable", "haspopup", "multiselectable")
    autocomplete: str = ""        # "list"/"both" hint an editable/async combobox
    option_count: int = 0         # options readable up front (0 = none yet loaded)


# Control kinds we dispatch on.
NATIVE_SELECT = "native_select"
ARIA_COMBOBOX = "aria_combobox"       # select-only custom combobox
EDITABLE_COMBOBOX = "editable_combobox"
ASYNC_COMBOBOX = "async_combobox"     # options load over the network as you type
MULTISELECT = "multiselect"
RADIO = "radio"
CHECKBOX = "checkbox"
DATEPICKER = "datepicker"
TEXT = "text"


def classify_control(c: ControlDescriptor) -> str:
    """Work out which kind of control we are facing, so the NVDA layer can pick
    a method. Deliberately conservative: when unsure, return the safer kind that
    triggers a read-and-verify rather than blind typing."""
    role = (c.role or "").lower()
    states = tuple(s.lower() for s in c.states)

    if role == "checkbox":
        return CHECKBOX
    if role in ("radiobutton", "radio"):
        return RADIO
    if "datepicker" in role or "date" == role:
        return DATEPICKER
    if "multiselectable" in states:
        return MULTISELECT

    if role in ("combobox", "listbox"):
        editable = "editable" in states
        list_ac = (c.autocomplete or "").lower() in ("list", "both", "inline")
        if editable and list_ac and c.option_count == 0:
            # editable, filters a list, nothing loaded up front -> fetched async.
            return ASYNC_COMBOBOX
        if editable:
            return EDITABLE_COMBOBOX
        # not editable: native select vs custom select-only combobox.
        # A native select exposes its options up front.
        return NATIVE_SELECT if c.option_count > 0 else ARIA_COMBOBOX

    return TEXT


# How the NVDA layer should try to set each kind, in order. Purely advisory
# data the NVDA layer reads; kept here so it is visible and testable.
METHOD_PLAN = {
    NATIVE_SELECT: ["selection_pattern", "typeahead"],
    ARIA_COMBOBOX: ["selection_pattern", "open_then_typeahead", "arrow_commit"],
    EDITABLE_COMBOBOX: ["type_then_pick"],
    ASYNC_COMBOBOX: ["type_wait_pick", "hand_back"],
    RADIO: ["selection_pattern", "focus_space"],
    CHECKBOX: ["toggle_to_state"],
    MULTISELECT: ["hand_back"],
    DATEPICKER: ["type_in_field", "hand_back"],
    TEXT: ["type"],
}


# --- review editor kinds ------------------------------------------------------
# Which accessible control the review dialog shows for a field. The whole point
# of the review editor is to make an inaccessible control accessible in its own
# idiom: a combobox becomes an accessible combobox you arrow through, a radio
# group an accessible chooser, a multi-select an accessible multi-check list, a
# date three dropdowns. It never flattens a chooser into a plain text box.
EDITOR_TEXT = "text"          # a typed edit box (also async: type then hand back)
EDITOR_SINGLE = "single"      # accessible chooser: arrow the options, pick one
EDITOR_EDITABLE = "editable"  # accessible editable combobox: type OR arrow-pick
EDITOR_YESNO = "yesno"        # accessible Yes / No
EDITOR_MULTI = "multi"        # accessible list: check several
EDITOR_DATE = "date"          # three dropdowns: day, month, year


def editor_kind(control_kind: str, key: str = "", input_type: str = "") -> str:
    """Map a classify_control kind to the accessible editor the review dialog
    offers. Pure and testable; reading the options and collapsing groups lives
    in the NVDA layer. Date wins first, matching the fill path's ordering.

    ARIA_COMBOBOX maps to a chooser structurally, but if its options sit behind
    a closed popup the NVDA layer cannot read, that layer downgrades it to a
    typed box. Async stays a typed box: its options load over the network and
    NVDA reports them empty to us, so we type and hand back to the live list."""
    if key == "date_of_birth" or input_type == "date" or control_kind == DATEPICKER:
        return EDITOR_DATE
    if control_kind == CHECKBOX:
        return EDITOR_YESNO
    if control_kind in (RADIO, NATIVE_SELECT, ARIA_COMBOBOX):
        return EDITOR_SINGLE
    if control_kind == MULTISELECT:
        return EDITOR_MULTI
    if control_kind in (EDITABLE_COMBOBOX, ASYNC_COMBOBOX):
        # Editable and async look identical when closed. Many are react-select
        # dropdowns whose menu renders when you press Down on the focused field
        # (Country, demographics). Route both through the editable editor so the
        # NVDA layer opens them by keyboard and reads the options.
        return EDITOR_EDITABLE
    return EDITOR_TEXT


# --- value to option matching -------------------------------------------------

# A tiny locale option map: the same concept named differently per language.
# Real build would grow this / defer to AI; this shows the mechanism and the
# classic country case (a French form lists Royaume-Uni, not United Kingdom).
COUNTRY_ALIASES = {
    "united kingdom": {"en": ["united kingdom", "uk", "great britain"],
                       "fr": ["royaume-uni"], "de": ["vereinigtes konigreich"],
                       "es": ["reino unido"], "ar": ["المملكة المتحدة"]},
    "saudi arabia": {"en": ["saudi arabia", "ksa"],
                     "fr": ["arabie saoudite"], "de": ["saudi-arabien"],
                     "es": ["arabia saudita"], "ar": ["السعودية", "المملكة العربية السعودية"]},
}


@dataclass
class OptionMatch:
    index: int | None            # index into the options list, or None
    label: str = ""              # the option label we would pick
    confidence: str = "none"     # "strong", "guess", "none"


def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace("_", " ").replace("-", " ").split())


def choose_option(value: str, options: list[str], concept: str = "") -> OptionMatch:
    """Pick the option that best matches the user's value.
    options are the labels as they appear in the form (possibly another language).
    concept lets us use a locale alias table, e.g. concept='country'."""
    v = _norm(value)
    norm_opts = [_norm(o) for o in options]

    # 1. exact match on the value itself.
    for i, o in enumerate(norm_opts):
        if o == v:
            return OptionMatch(i, options[i], "strong")

    # 2. country and nationality: match through the full country dataset, which
    # knows every country's name in two dozen languages plus its demonyms, so
    # "Saudi" or "Saudi Arabia" matches السعودية on an Arabic form, and a
    # nationality field that lists countries resolves the same way.
    if concept in ("country", "nationality") and _countries is not None:
        try:
            idx, label, conf = _countries.match_country(value, options)
            if idx is not None:
                return OptionMatch(idx, label,
                                   "strong" if conf == "strong" else "guess")
        except Exception:
            pass

    # 3. containment either way - a softer, flagged guess.
    for i, o in enumerate(norm_opts):
        if v and (v in o or o in v):
            return OptionMatch(i, options[i], "guess")

    # 4. no confident match - leave it to the user.
    return OptionMatch(None, "", "none")


# --- verify that a selection actually stuck -----------------------------------

def verify_selection(expected_label: str, control_value_after: str) -> str:
    """After we set a choice, the NVDA layer reads the control's value back and
    passes it here. A set can silently fail, so we never assume it worked.
    Returns 'confirmed', 'mismatch', or 'unknown'."""
    if not control_value_after:
        return "unknown"                 # could not read it back
    if _norm(control_value_after) == _norm(expected_label):
        return "confirmed"
    if _norm(expected_label) in _norm(control_value_after):
        return "confirmed"
    return "mismatch"
