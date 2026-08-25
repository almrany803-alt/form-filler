# announce.py - build exactly what the user hears and reads in braille.
# Pure and deterministic (the "test what the user HEARS" rule from Zul).

_HUMAN = {
    "given_name": "first name", "family_name": "last name",
    "full_name": "full name", "email": "email", "phone": "phone",
    "address_line1": "address", "city": "city", "postcode": "postcode",
    "country": "country", "nationality": "nationality",
    "date_of_birth": "date of birth",
    "linkedin": "LinkedIn",
    "work_authorisation": "work authorisation",
}


def human(k: str) -> str:
    return _HUMAN.get(k, k)


def entry_summary(row) -> str:
    """A one-line summary of a section entry for the entries list, for example
    'Technology Support Volunteer, Sight Support West of England, Mar 2024 to
    Jun 2026'. Rows are free-form, so this favours the common fields (a title,
    then an organisation, then dates) and falls back to whatever values the row
    holds, so a user-invented section still reads sensibly."""
    if not row:
        return "(empty entry)"
    parts = []
    for k in ("job_title", "qualification", "skill", "language", "name",
              "title"):
        if row.get(k):
            parts.append(str(row[k]).strip())
            break
    for k in ("employer", "institution", "issuer", "field_of_study",
              "proficiency"):
        if row.get(k):
            parts.append(str(row[k]).strip())
            break
    start = str(row.get("start_date") or "").strip()
    end = str(row.get("end_date") or "").strip()
    if start or end:
        parts.append("{a} to {b}".format(a=start or "?", b=end or "present"))
    elif row.get("date"):
        parts.append(str(row["date"]).strip())
    if parts:
        return ", ".join(p for p in parts if p)
    vals = [str(v).strip() for v in row.values() if str(v).strip()]
    return ", ".join(vals[:3]) if vals else "(empty entry)"


def build_summary(filled, guessed, leftovers, cap=6):
    """filled/guessed: profile keys. leftovers: human labels we could not fill.
    Non-fillable controls (buttons, toggles) are filtered out before this, so
    leftovers should be real fields. We dedupe and cap the spoken list so a busy
    form does not read a wall of names; the review list holds the full set."""
    leftovers = list(dict.fromkeys(leftovers))
    total = len(filled) + len(guessed) + len(leftovers)
    done = len(filled) + len(guessed)
    parts = [f"Filled {done} of {total}."]
    if guessed:
        names = ", ".join(human(g) for g in guessed)
        word = "guess" if len(guessed) == 1 else "guesses"
        parts.append(f"Check {len(guessed)} {word}: {names}.")
    if leftovers:
        shown = [human(x) for x in leftovers[:cap]]
        extra = len(leftovers) - len(shown)
        tail = f", and {extra} more" if extra > 0 else ""
        parts.append(f"{len(leftovers)} need you: {', '.join(shown)}{tail}.")
    else:
        parts.append("Nothing left for you.")
    return " ".join(parts)


def choice_set(field_label: str, option_label: str, verify: str) -> str:
    """Message after trying to set a dropdown, keyed on the verify-back result."""
    if verify == "confirmed":
        return f"{field_label} set to {option_label}."
    if verify == "mismatch":
        return f"{field_label} did not take {option_label}. Over to you."
    return f"{field_label}: could not confirm {option_label}. Please check it."


def hand_back(field_label: str, kind: str, typed: str = "") -> str:
    """Honest message when we deliberately do not automate a control."""
    if kind == "async_combobox":
        return (f"{field_label} is a search box. I typed {typed}. "
                "Use the up and down arrows to pick from the list, then Enter.")
    if kind == "multiselect":
        return (f"{field_label} is a multi-select. Put your cursor on it and "
                "press fill this field, or choose the options yourself.")
    if kind == "datepicker":
        return (f"{field_label}: put your cursor on it and press fill this "
                "field to set the date.")
    return f"{field_label}: please set this one yourself."


# --- form audit (post CV-attach) ---------------------------------------------

_AUDIT_ORDER = {"duplicate": 0, "empty": 1, "extra_count": 2,
                "half_filled": 3, "mismatch": 4}


def audit_summary(report) -> str:
    """One spoken line summarising what the application's parser did to the form."""
    if report.ok:
        return "Form check: all good. Nothing duplicated or added."
    items = sorted(report.anomalies, key=lambda a: _AUDIT_ORDER.get(a.kind, 9))
    n = len(items)
    head = f"Form check: {n} thing to look at." if n == 1 else \
           f"Form check: {n} things to look at."
    return head + " " + " ".join(a.detail for a in items)
