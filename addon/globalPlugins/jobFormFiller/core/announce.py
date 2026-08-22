# announce.py - build exactly what the user hears and reads in braille.
# Pure and deterministic (the "test what the user HEARS" rule from Zul).

_HUMAN = {
    "given_name": "first name", "family_name": "last name",
    "full_name": "full name", "email": "email", "phone": "phone",
    "address_line1": "address", "city": "city", "postcode": "postcode",
    "country": "country", "linkedin": "LinkedIn",
    "work_authorisation": "work authorisation",
}


def human(k: str) -> str:
    return _HUMAN.get(k, k)


def build_summary(filled, guessed, leftovers):
    """filled/guessed: profile keys. leftovers: human labels we could not fill."""
    total = len(filled) + len(guessed) + len(leftovers)
    done = len(filled) + len(guessed)
    parts = [f"Filled {done} of {total}."]
    if guessed:
        names = ", ".join(human(g) for g in guessed)
        word = "guess" if len(guessed) == 1 else "guesses"
        parts.append(f"Check {len(guessed)} {word}: {names}.")
    if leftovers:
        names = ", ".join(human(x) for x in leftovers)
        parts.append(f"{len(leftovers)} need you: {names}.")
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
                "Please pick from the list.")
    if kind == "multiselect":
        return f"{field_label} is a multi-select. Please choose the options yourself."
    if kind == "datepicker":
        return f"{field_label} is a date picker. Please enter the date yourself."
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
