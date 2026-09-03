"""Pure date helpers for the fill: reading a day/month/year order and separator
from a field's format hint, formatting an ISO date, and recognising which
segment of a split date control a field is. No NVDA dependency, so it is
unit-tested; the plugin delegates here.

Lesson recorded: these lived untested in the plugin, and the whole-hint scan
read 'Date (mm/dd/yyyy)' as day-first from the D in 'Date', while the
digit-set verify cannot see a day/month swap. Keep them here, tested.
"""
import re

_DATE_FMT_RE = re.compile(r"([dmy]{1,4})([/.\-])([dmy]{1,4})\2([dmy]{1,4})", re.I)


def format_token(text):
    """The format pattern inside a hint (the 'mm/dd/yyyy' in 'Date (mm/dd/yyyy)'),
    or None. Prose around it must not contribute letters or separators."""
    return _DATE_FMT_RE.search(text or "")


def order_from_hint(text):
    """'DMY', 'MDY', 'YMD' from a format token, else from whole words day/month/
    year in order of appearance, else ''."""
    m = format_token(text)
    if m:
        order = "".join(g[0].upper() for g in (m.group(1), m.group(3), m.group(4)))
        return order if set(order) == {"D", "M", "Y"} else ""
    order = ""
    for w in re.findall(r"\b(day|month|year)\b", (text or "").lower()):
        u = w[0].upper()
        if u not in order:
            order += u
    return order if set(order) == {"D", "M", "Y"} else ""


def separator_from_hint(text, default="/"):
    """The separator of the format token, never a stray one from prose."""
    m = format_token(text)
    return m.group(2) if m else default


def format_date(y, m, d, order, sep):
    part = {"Y": y, "M": m, "D": d}
    return sep.join(part[o] for o in order)


def digits(s):
    return "".join(c for c in (s or "") if c.isdigit())


def segment_from(field_id, dom_class):
    """'day'/'month'/'year' if the id/class marks one segment of a split date
    control, else None. Whole tokens only (split on punctuation and camelCase):
    'birthday_month' is the month segment even though 'birthday' contains 'day'."""
    raw = " ".join([(field_id or ""), (dom_class or "")])
    hay = raw.lower()
    if "date" not in hay and not any(w in hay for w in ("birth", "dob", "bday")):
        return None
    tokens = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw).lower()
    tokens = set(re.split(r"[^a-z0-9]+", tokens))
    for seg in ("day", "month", "year"):
        if seg in tokens:
            return seg
    return None
