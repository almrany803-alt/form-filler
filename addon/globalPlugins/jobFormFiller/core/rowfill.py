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


def plan_section_fill(rows, block_fields, blocks_present=1):
    """Decide how to spread stored rows across a form's repeating blocks.

    rows          : the stored rows for the section (list of dicts).
    block_fields  : the row-field keys one form block exposes, e.g.
                    ['job_title', 'employer', 'start_date', 'end_date'].
    blocks_present: how many blocks the form already shows (at least 1).

    Returns (adds, fills):
      adds  = how many 'Add another' clicks are needed so there is one block per
              row (0 if the form already has enough).
      fills = [(block_index, {field: value}), ...] - for each row, the values
              that go in that block, limited to fields the block actually has
              and the row actually provides. Rows with nothing to place are
              skipped, so an empty stored row never consumes a block.
    """
    rows = rows or []
    block_fields = list(block_fields or [])
    placeable = []
    for row in rows:
        vals = {f: row[f] for f in block_fields if str(row.get(f, "")).strip()}
        if vals:
            placeable.append(vals)
    adds = max(0, len(placeable) - max(1, blocks_present))
    fills = list(enumerate(placeable))
    return adds, fills
