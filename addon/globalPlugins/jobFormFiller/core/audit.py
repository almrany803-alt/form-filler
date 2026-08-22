# audit.py - check what the application's own CV parser did to the form.
#
# Many application forms auto-fill from an attached CV. That is helpful, but the
# parsers duplicate entries, add blank rows, invent extra entries, mis-map
# fields, or half-fill a row. A sighted applicant catches this at a glance; a
# screen reader user tabbing linearly can miss it. This module compares the
# form's state against the user's own CV and reports the anomalies.
#
# Pure Python and deterministic. The NVDA layer reads the actual entries off the
# form and hands them here as plain dicts; this module only judges.

from dataclasses import dataclass, field
import unicodedata


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


# readable name for a section, for announcements
_SECTION_HUMAN = {"experience": "work", "education": "education"}
# fields that make an entry meaningful, per section
_REQUIRED = {
    "experience": ("company", "title"),
    "education": ("institution",),
}
# order to look for a representative label of an entry
_LABEL_FIELDS = ("company", "institution", "organisation", "employer",
                 "title", "degree", "name")


@dataclass
class Anomaly:
    kind: str           # duplicate, empty, extra_count, half_filled, mismatch
    section: str
    detail: str         # the human phrase spoken to the user
    indices: tuple = ()


@dataclass
class AuditReport:
    anomalies: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.anomalies


def _entry_is_empty(entry: dict) -> bool:
    return all(not str(v).strip() for v in entry.values())


def _signature(entry: dict):
    """Order-independent signature of the non-empty, normalised fields."""
    return tuple(sorted((k, _norm(v)) for k, v in entry.items() if str(v).strip()))


def _entry_label(entry: dict) -> str:
    for f in _LABEL_FIELDS:
        if entry.get(f) and str(entry[f]).strip():
            return str(entry[f]).strip()
    for v in entry.values():
        if str(v).strip():
            return str(v).strip()
    return "entry"


def _sec(section: str) -> str:
    return _SECTION_HUMAN.get(section, section)


def audit_section(section, form_entries, cv_entries, required=None):
    """Compare one repeating section (experience/education) to the CV's."""
    required = required or _REQUIRED.get(section, ())
    anomalies = []

    # empties: blank rows the parser added
    empties = [i for i, e in enumerate(form_entries) if _entry_is_empty(e)]
    for i in empties:
        anomalies.append(Anomaly("empty", section,
                                 f"An empty {_sec(section)} entry was added.", (i,)))

    non_empty = [(i, e) for i, e in enumerate(form_entries) if not _entry_is_empty(e)]

    # duplicates: same signature appearing more than once
    seen = {}
    for i, e in non_empty:
        seen.setdefault(_signature(e), []).append(i)
    for sig, idxs in seen.items():
        if len(idxs) > 1:
            label = _entry_label(form_entries[idxs[0]])
            n = len(idxs)
            word = "Two" if n == 2 else str(n)
            anomalies.append(Anomaly(
                "duplicate", section,
                f"{word} identical {_sec(section)} entries: {label}.", tuple(idxs)))

    # extra distinct entries: more unique real entries than the CV has
    unique_count = len(seen)
    extra = unique_count - len(cv_entries)
    if extra > 0:
        anomalies.append(Anomaly(
            "extra_count", section,
            f"{extra} more {_sec(section)} "
            f"{'entry' if extra == 1 else 'entries'} than your CV: check the extras."))

    # half-filled: a real entry missing a required field
    for i, e in non_empty:
        missing = [f for f in required if not str(e.get(f, "")).strip()]
        if missing and len(missing) < len(required or (1,)) + 1 and len(missing) != len(e):
            # has something, but is missing a required field
            if any(str(v).strip() for v in e.values()):
                anomalies.append(Anomaly(
                    "half_filled", section,
                    f"{_sec(section).capitalize()} entry {_entry_label(e)} "
                    f"is missing {', '.join(missing)}.", (i,)))

    return anomalies


def audit_contact(form_contact: dict, cv_contact: dict):
    """Flag simple fields the parser set to something other than your CV."""
    anomalies = []
    for key, cv_val in cv_contact.items():
        form_val = form_contact.get(key, "")
        if str(form_val).strip() and _norm(form_val) != _norm(cv_val):
            anomalies.append(Anomaly(
                "mismatch", "contact",
                f"The form has your {key} as {form_val}, your CV says {cv_val}.",
                ()))
    return anomalies


def audit_form(form: dict, cv: dict) -> AuditReport:
    """form and cv are dicts like:
        {"contact": {...}, "experience": [ {...}, ... ], "education": [ ... ]}
    Returns an AuditReport of everything worth the user's attention."""
    report = AuditReport()
    report.anomalies += audit_contact(form.get("contact", {}), cv.get("contact", {}))
    for section in ("experience", "education"):
        report.anomalies += audit_section(
            section, form.get(section, []), cv.get(section, []))
    return report
