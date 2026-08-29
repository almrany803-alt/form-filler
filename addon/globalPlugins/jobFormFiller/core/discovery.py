"""Opt-in, offline discovery of fields the fingerprint database does not yet
cover, so new fingerprints can be added for hard platforms.

This is deterministic and local: it only reads the field signatures the add-on
already has, and (via the Scan action) writes a shareable file. No network, no
AI, and it never changes how anything is filled. Its output is a list of
custom-widget signatures the database missed, each with a suggested fingerprint
stub a human can review and complete.
"""

# Roles that indicate a custom widget worth a fingerprint. Native text and
# select are handled without one, so they are not discovery targets.
_WIDGET_ROLES = {"combobox", "listbox", "menuitem"}


def is_custom_widget(sig):
    """True for a field that behaves like a custom control (a popup, a
    combobox/listbox role, or an editable box that expands/collapses), rather
    than a plain native input a fingerprint would not help with."""
    role = (sig.get("role") or "").lower()
    if (sig.get("haspopup") or "").strip():
        return True
    if role in _WIDGET_ROLES:
        return True
    states = tuple(str(s).lower() for s in (sig.get("states") or ()))
    if role == "editabletext" and ("collapsed" in states or "expanded" in states):
        return True
    return False


def _class_token(cls):
    """Pick a stable, human-looking class token (BEM 'block__el' or a short
    hyphenated name), skipping long hashed blobs, or '' if none fits."""
    for c in (cls or "").split():
        if "__" in c and 4 <= len(c) <= 30:
            return c
    for c in (cls or "").split():
        if "-" in c and 4 <= len(c) <= 24 and not _looks_hashed(c):
            return c
    return ""


def _looks_hashed(tok):
    """A token like 'css-1ab2cd' or 'jsx-1928' is unstable; avoid it."""
    digits = sum(ch.isdigit() for ch in tok)
    return digits >= 3


def suggest_when(sig, platform):
    """The most stable 'when' clause for a fingerprint stub: platform, an id or
    class pattern, and the role. A starting point for a human to refine."""
    when = {}
    if platform:
        when["platform"] = platform
    idn = sig.get("id") or ""
    if "--" in idn:                       # Workday name--name pattern
        head = idn.split("--")[0]
        when["id_contains"] = head + "--" + head
    else:
        tok = _class_token(sig.get("class") or "")
        if tok:
            when["class_contains"] = tok
    role = (sig.get("role") or "").lower()
    if role:
        when["role"] = role
    return when


def build_records(fields, platform, is_matched):
    """fields: list of signature dicts (id, role, placeholder, class, haspopup,
    states, label). is_matched(sig) -> bool says whether a fingerprint already
    covers the field. Returns discovery records for custom widgets NOT already
    covered, each with a suggested fingerprint stub (kind left as 'REVIEW' for a
    human to classify - we never guess how to fill a widget we do not know)."""
    records = []
    for sig in fields or []:
        try:
            if is_matched(sig):
                continue
            if not is_custom_widget(sig):
                continue
            records.append({
                "label": sig.get("label", ""),
                "signature": {k: sig.get(k, "") for k in
                              ("id", "role", "placeholder", "class", "haspopup")},
                "states": list(sig.get("states") or ()),
                "suggested_fingerprint": {
                    "when": suggest_when(sig, platform),
                    "kind": "REVIEW",
                },
            })
        except Exception:
            continue
    return records
