# rowfill.py - the pure planning for filling REPEATING section blocks (several
# jobs, several courses) onto a form. The NVDA side detects the blocks and the
# "Add another" control and does the typing; this module decides,
# deterministically, which stored row fills which block and how many blocks to
# add. Kept pure so it is fully testable without NVDA.

import re
import unicodedata


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[_\-\[\](){}./\\:]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Form-field label -> stored-row field key. Used ONLY inside a section block, so
# short words like "title", "from" and "to" are safe here (we already know we
# are inside Experience or Education), unlike the personal-field matcher where
# they would be ambiguous.
_ROW_LEXICON = {
    "job_title": ["job title", "position", "title", "role", "job"],
    "employer": ["employer", "company", "company name", "organisation",
                 "organization", "employer name", "workplace"],
    "institution": ["institution", "school", "university", "college",
                    "institution name", "school name"],
    "qualification": ["qualification", "degree", "diploma", "certificate",
                      "award"],
    "field_of_study": ["field of study", "major", "subject", "course",
                       "programme", "program", "discipline"],
    "start_date": ["start date", "from", "start", "date from", "started"],
    "end_date": ["end date", "to", "end", "date to", "until", "ended",
                 "finished"],
    "description": ["description", "responsibilities", "duties", "details",
                    "summary", "achievements"],
    "skill": ["skill", "skills"],
    "grade": ["grade", "result", "classification", "gpa"],
}


def row_concept(label):
    """Which stored-row field a form field is, inside a section block, or None.
    Whole-word matched and longest-wins, so 'job title' beats 'title' and
    'start date' beats 'start'."""
    t = " " + _norm(label) + " "
    best = None
    for key, phrases in _ROW_LEXICON.items():
        for p in phrases:
            p = _norm(p)
            if (" " + p + " ") in t and (best is None or len(p) > best[1]):
                best = (key, len(p))
    return best[0] if best else None


def _year_of(s):
    m = re.search(r"(?:19|20)\d\d", str(s or ""))
    return int(m.group(0)) if m else 0


def _recency_key(row):
    """Sort key so the most recent entry comes first: an ongoing role (a start
    date but an empty or 'present' end) is newest, then by end year, then by
    start year. Undated rows keep their original order (stable sort)."""
    end = str(row.get("end_date", "")).strip().lower()
    has_start = bool(str(row.get("start_date", "")).strip())
    ongoing = has_start and end in ("", "present", "current", "ongoing", "now")
    end_year = 9999 if ongoing else _year_of(row.get("end_date"))
    return (end_year, _year_of(row.get("start_date")))


def detect_blocks(keys):
    """From the row-concept keys read down a form's section, work out one
    block's fields and how many blocks are already present. If the keys repeat
    (title, employer, from, to, title, employer, from, to) that repeating unit
    is the block; otherwise there is one block of the distinct keys in order."""
    keys = [k for k in keys if k]
    if not keys:
        return [], 0
    first = keys[0]
    block_len = len(keys)
    for i in range(1, len(keys)):
        if keys[i] == first:
            block_len = i
            break
    block_fields = keys[:block_len]
    blocks = len(keys) // block_len if block_len else 1
    return block_fields, max(1, blocks)


def order_recent_first(rows):
    """Return the rows most recent first, for showing in the checklist and for
    placing the newest job in the first block. Stable for undated rows."""
    return sorted(rows or [], key=_recency_key, reverse=True)


def plan_section_fill(rows, block_fields, blocks_present=1, max_blocks=None):
    """Decide how to spread stored rows across a form's repeating blocks.

    rows          : the stored rows for the section, in the order to place them
                    (already filtered to the user's choice and ordered).
    block_fields  : the row-field keys one form block exposes, e.g.
                    ['job_title', 'employer', 'start_date', 'end_date'].
    blocks_present: how many blocks the form already shows (at least 1); these
                    are filled first before any 'Add another'.
    max_blocks    : the most blocks the form allows, or None for no limit.

    Returns (adds, fills, leftover):
      adds     = how many 'Add another' clicks are needed (0 if enough already).
      fills    = [(block_index, {field: value}), ...] - the values for each block,
                 limited to fields the block has and the row provides. Rows with
                 nothing to place are skipped, so an empty row never takes a block.
      leftover = how many chosen rows did not fit because of max_blocks.
    """
    rows = rows or []
    block_fields = list(block_fields or [])
    placeable = []
    for row in rows:
        vals = {f: row[f] for f in block_fields if str(row.get(f, "")).strip()}
        if vals:
            placeable.append(vals)
    total = len(placeable)
    if max_blocks is not None and max_blocks >= 0:
        placeable = placeable[:max_blocks]
    adds = max(0, len(placeable) - max(1, blocks_present))
    fills = list(enumerate(placeable))
    leftover = total - len(placeable)
    return adds, fills, leftover
