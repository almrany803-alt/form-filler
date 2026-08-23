# controls.py - the brain for dropdowns and other choice controls.
#
# The NVDA layer reads the live control (role, states, options, current value)
# and performs the actual selection. THIS module only decides:
#   - what kind of control it is (so the NVDA layer picks the right method)
#   - which option matches the user's value (locale/multilingual aware)
#   - whether a selection actually stuck (verify-back)
# All pure Python, all testable.

from dataclasses import dataclass, field


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

    # 2. locale aliases (value in one language, option in another).
    if concept == "country":
        aliases = COUNTRY_ALIASES.get(v)
        if aliases:
            alias_set = {_norm(a) for lst in aliases.values() for a in lst}
            for i, o in enumerate(norm_opts):
                if o in alias_set:
                    return OptionMatch(i, options[i], "strong")

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
