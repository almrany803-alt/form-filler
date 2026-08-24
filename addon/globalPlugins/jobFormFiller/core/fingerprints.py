"""Field fingerprint database (deterministic, offline, shareable).

A fingerprint maps a field's STABLE signals (platform, id pattern, role,
placeholder, class, states) to its true classification. The add-on checks this
database before falling back to the heuristics, so a known widget is classified
correctly with no guessing and no AI at runtime. Because platforms like Workday
and Taleo repeat the same field structure across thousands of employers, one
entry covers a huge share of real forms, which is exactly what makes a small,
crowd-sourced database worthwhile (the ad-blocker filter-list model).

The data lives in field_fingerprints.json next to this file so it can be updated
and shared on its own, without touching code. Vision (opt-in) is what discovers
new fingerprints to add; this database is what applies them, free and offline.
"""

import os
import re
import json

_DB_PATH = os.path.join(os.path.dirname(__file__), "field_fingerprints.json")
_CACHE = None


def _load():
    global _CACHE
    if _CACHE is None:
        try:
            with open(_DB_PATH, encoding="utf-8") as f:
                _CACHE = json.load(f).get("fingerprints", [])
        except Exception:
            _CACHE = []
    return _CACHE


def _signals(fd, platform):
    """The comparable signals of a field, all lower-cased."""
    return {
        "platform": (platform or "").lower(),
        "id": (getattr(fd, "id", "") or "").lower(),
        "role": (getattr(fd, "role", "") or "").lower(),
        "placeholder": (getattr(fd, "placeholder", "") or "").lower(),
        "dom_class": (getattr(fd, "dom_class", "") or "").lower(),
        "haspopup": (getattr(fd, "haspopup", "") or "").lower(),
        "states": tuple(s.lower() for s in getattr(fd, "states", ()) or ()),
    }


def _matches(when, sig):
    """True when every condition in a fingerprint's 'when' holds for the field.
    Unknown condition keys make the fingerprint fail closed (never match), so a
    malformed shared entry can't misfire."""
    for key, want in when.items():
        want_l = str(want).lower()
        if key == "platform":
            if sig["platform"] != want_l:
                return False
        elif key == "role":
            if sig["role"] != want_l:
                return False
        elif key == "placeholder":
            if sig["placeholder"] != want_l:
                return False
        elif key == "id_contains":
            if want_l not in sig["id"]:
                return False
        elif key == "id_regex":
            try:
                if not re.search(want_l, sig["id"]):
                    return False
            except re.error:
                return False
        elif key == "class_contains":
            if want_l not in sig["dom_class"]:
                return False
        elif key == "haspopup":
            if sig["haspopup"] != want_l:
                return False
        elif key == "has_state":
            if want_l not in sig["states"]:
                return False
        else:
            return False  # unknown key: fail closed
    return True


def match_fingerprint(fd, platform="", db=None):
    """Return the first matching fingerprint's result dict {kind, note, id} for a
    field, or None. Deterministic and offline. The caller uses 'kind' to override
    or confirm the heuristic classification."""
    entries = db if db is not None else _load()
    sig = _signals(fd, platform)
    for entry in entries:
        when = entry.get("when", {})
        if when and _matches(when, sig):
            return {"kind": entry.get("kind", ""),
                    "note": entry.get("note", ""),
                    "id": entry.get("id", "")}
    return None
