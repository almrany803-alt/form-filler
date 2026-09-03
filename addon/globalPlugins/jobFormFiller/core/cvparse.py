# cvparse.py - pull profile fields out of CV text, for import-and-review.
#
# Deterministic and conservative: it extracts the reliable things (email,
# phone, LinkedIn, a likely name, and rough section blocks) and NOTHING it is
# unsure of. It never fabricates a field. Whatever it returns is shown to the
# user to correct before saving, so the cost of a miss is small, the cost of a
# confident wrong guess is not - hence "extract only what is clear".
#
# Getting text OUT of a .docx or .pdf is a separate step (extract_text below),
# done with bundled libraries in the real add-on. The parsing logic here works
# on plain text so it is fully testable.

import os
import re
import unicodedata

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_LINKEDIN = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+", re.I)
_PHONE = re.compile(r"(?<!\w)(\+?\d[\d\s().\-]{7,}\d)(?!\w)")

# Section headings per concept per language. Extend a language by adding words.
_HEADINGS = {
    "education": {
        "it": ["istruzione", "formazione"],
        "pt": ["educacao", "formacao", "habilitacoes"],
        "pl": ["wyksztalcenie", "edukacja"],
        "nl": ["opleiding", "onderwijs"],
        "en": ["education", "qualifications", "academic"],
        "fr": ["formation", "education", "diplomes"],
        "de": ["ausbildung", "bildung"],
        "es": ["educacion", "formacion"],
        "ar": ["التعليم", "المؤهلات"],
        "tr": ["eğitim", "öğrenim"], "id": ["pendidikan"], "fa": ["تحصیلات"], "ur": ["تعلیم"],
        "cs": ["vzdělání"], "sk": ["vzdelanie"], "hu": ["tanulmányok", "végzettség"], "fi": ["koulutus"],
        "sv": ["utbildning"], "hr": ["obrazovanje"], "sr": ["образовање"], "et": ["haridus"], "cy": ["addysg"],
    },
    "experience": {
        "it": ["esperienza", "esperienza professionale", "esperienza lavorativa"],
        "pt": ["experiencia", "experiencia profissional"],
        "pl": ["doswiadczenie", "doswiadczenie zawodowe"],
        "nl": ["werkervaring", "ervaring"],
        "en": ["experience", "employment", "work history", "work experience"],
        "fr": ["experience", "experience professionnelle", "emploi"],
        "de": ["berufserfahrung", "erfahrung"],
        "es": ["experiencia", "experiencia laboral"],
        "ar": ["الخبرة", "الخبرات"],
        "tr": ["deneyim", "iş deneyimi", "tecrübe"], "id": ["pengalaman"], "fa": ["تجربه", "سابقه کار"], "ur": ["تجربہ"],
        "cs": ["praxe", "zkušenosti"], "sk": ["prax", "skúsenosti"], "hu": ["tapasztalat"], "fi": ["kokemus", "työkokemus"],
        "sv": ["erfarenhet", "arbetslivserfarenhet"], "hr": ["iskustvo", "radno iskustvo"], "sr": ["искуство"], "et": ["kogemus", "töökogemus"], "cy": ["profiad"],
    },
    "skills": {
        "it": ["competenze"],
        "pt": ["competencias", "habilidades"],
        "pl": ["umiejetnosci"],
        "nl": ["vaardigheden"],
        "en": ["skills", "technical skills", "competencies"],
        "fr": ["competences"],
        "de": ["kenntnisse", "faehigkeiten"],
        "es": ["habilidades", "competencias"],
        "ar": ["المهارات"],
        "tr": ["beceriler", "yetenekler"], "id": ["keterampilan", "keahlian"], "fa": ["مهارت‌ها", "مهارتها"], "ur": ["مہارتیں"],
        "cs": ["dovednosti"], "sk": ["zručnosti"], "hu": ["készségek"], "fi": ["taidot"],
        "sv": ["färdigheter", "kompetenser"], "hr": ["vještine"], "sr": ["вештине"], "et": ["oskused"], "cy": ["sgiliau"],
    },
    "certifications": {
        "en": ["certifications", "certificates", "certification",
               "professional development", "licenses", "accreditations"],
        "fr": ["certifications"],
        "de": ["zertifikate", "zertifizierungen"],
        "es": ["certificaciones"],
        "ar": ["الشهادات"],
    },
    "languages": {
        "en": ["languages"],
        "it": ["lingue"],
        "pt": ["idiomas"],
        "nl": ["talen"],
        "fr": ["langues"],
        "de": ["sprachen"],
        "es": ["idiomas"],
        "ar": ["اللغات"],
    },
    # These are recognised as headings so they end the previous section cleanly,
    # even though they are not seeded into profile sections themselves.
    "projects": {"en": ["projects", "project", "portfolio"], "fr": ["projets"],
                 "de": ["projekte"], "es": ["proyectos"], "ar": ["المشاريع"]},
    "interests": {"en": ["interests", "hobbies", "activities"],
                  "fr": ["interets", "loisirs"], "de": ["interessen", "hobbys"],
                  "es": ["intereses"], "ar": ["الاهتمامات", "الهوايات"]},
    "references": {"en": ["references", "referees"], "fr": ["references"],
                   "de": ["referenzen"], "es": ["referencias"],
                   "ar": ["المراجع"]},
}


_STROKE = str.maketrans({"ł": "l", "Ł": "l", "ø": "o", "Ø": "o",
                         "đ": "d", "Đ": "d", "ð": "d", "þ": "th"})


def _fold(s: str) -> str:
    s = (s or "").translate(_STROKE)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _heading_key(line: str):
    """Return the section key if this line is a recognised heading, else None.
    A heading word may sit anywhere in a short heading line (as a whole word),
    so 'Teaching and Volunteer Experience' is recognised as experience, not just
    a line that begins with 'Experience'."""
    low = _fold(line.strip())
    if not low or len(low) >= 55:
        return None
    padded = " " + low + " "
    for key, langs in _HEADINGS.items():
        for words in langs.values():
            for w in words:
                fw = _fold(w)
                if low == fw or (" " + fw + " ") in padded:
                    return key
    return None


def _is_cjk_char(ch) -> bool:
    o = ord(ch)
    return (0x3040 <= o <= 0x30FF or 0x3400 <= o <= 0x4DBF
            or 0x4E00 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF)


_CV_TITLES = {
    "curriculum vitae", "cv", "resume", "résumé", "resumé", "personal profile",
    "personal details", "personal information", "contact details",
    "contact information", "profile", "summary", "personal statement",
    "about me", "candidate profile",
}


def _is_cv_title(line: str) -> bool:
    """A document heading like 'Curriculum Vitae' or 'Personal Profile', which
    must never be mistaken for the person's name."""
    t = re.sub(r"[^\w\s]", "", (line or "")).strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t in _CV_TITLES


def _looks_like_name(line: str) -> bool:
    line = line.strip()
    if not line or any(ch.isdigit() for ch in line) or "@" in line:
        return False
    # Chinese and Japanese names have no spaces: a short run of Han/Kana
    # characters at the top of a CV is a name (this is the first line only).
    if 1 <= len(line) <= 6 and all(_is_cjk_char(ch) for ch in line):
        return True
    words = line.split()
    if not (2 <= len(words) <= 4):
        return False
    # each word begins with a letter (works for Latin, Arabic, Cyrillic scripts)
    return all(w[:1].isalpha() for w in words)


def parse_cv_text(text: str) -> dict:
    result = {}
    lines = [ln.rstrip() for ln in (text or "").splitlines()]

    m = _EMAIL.search(text or "")
    if m:
        result["email"] = m.group(0)

    m = _LINKEDIN.search(text or "")
    if m:
        result["linkedin"] = m.group(0)

    # phone: take the first match that has enough digits to be a real number.
    for m in _PHONE.finditer(text or ""):
        digits = re.sub(r"\D", "", m.group(1))
        if 9 <= len(digits) <= 15:
            result["phone"] = m.group(1).strip()
            break

    # name: the first non-empty line that looks like a name, skipping document
    # titles. Many CVs open with "Curriculum Vitae" or "Personal Profile", two
    # capitalised words that pass the name test, and the old code stopped at
    # the first non-empty line, so the title was imported as the person's name.
    seen = 0
    for ln in lines:
        if not ln.strip():
            continue
        if _is_cv_title(ln):
            continue
        seen += 1
        if _looks_like_name(ln):
            result["full_name"] = ln.strip()
        break

    # sections: collect lines under a recognised heading until the next heading.
    sections = {}
    current = None
    for ln in lines:
        matched = _heading_key(ln)
        if matched:
            current = matched
            sections.setdefault(current, [])
            continue
        if current and ln.strip():
            sections[current].append(ln.strip())
    for key, body in sections.items():
        if body:
            result[key] = body

    return result


_SECTION_NAMES = {
    "education": "Education", "experience": "Experience", "skills": "Skills",
    "certifications": "Certifications", "languages": "Languages",
}

_YEARISH = re.compile(r"(?:19|20)\d\d|present|current|ongoing|now", re.I)


def _dates(line):
    """From an entry header, pull (start, end, span) where span marks where the
    date range sits, so it can be stripped from the title text. Only a
    parenthesised group that actually looks like a date range counts, so
    '(Honours)' or '(2:1)' are left alone."""
    for m in re.finditer(r"\(([^)]*)\)", line):
        inner = m.group(1)
        if not _YEARISH.search(inner):
            continue
        parts = re.split(r"\s*(?:\bto\b|\buntil\b|[-\u2013\u2014])\s*",
                         inner, maxsplit=1, flags=re.I)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip(), m.span()
    return "", "", None


_BARE_DATE = (r"(?:[A-Za-z]{3,9}\.?\s+)?(?:19|20)\d\d"
              r"|\d{1,2}/(?:19|20)\d\d|(?:19|20)\d\d")
_BARE_RANGE = re.compile(
    r"^\s*(" + _BARE_DATE + r")\s*(?:to|until|[-\u2013\u2014])\s*"
    r"(present|current|ongoing|now|" + _BARE_DATE + r")\s*$", re.I)


def _bare_dates(line):
    """If the whole line is just a date range ('March 2021 - Present',
    '2019-2022'), return (start, end); else None. Catches the very common CV
    style where dates sit on their own line, not in parentheses."""
    m = _BARE_RANGE.match(line.strip())
    if not m:
        return None
    start = m.group(1).strip()
    end = m.group(2).strip()
    if re.search(r"present|current|ongoing|now", end, re.I):
        end = ""
    return start, end


def _is_bullet(line):
    return line.lstrip()[:1] in ("-", "\u2022", "*", "\u00b7")


_SINGLE_DATE = re.compile(
    r"(?:graduated|completed|class of|awarded|expected)?\s*"
    r"((?:[A-Za-z]{3,9}\.?\s+)?(?:19|20)\d\d)", re.I)


def _single_date(line):
    """A single graduation-style date from a short line ('Graduated May 2016',
    '2016', 'May 2016 | GPA 3.8'), or None. A '| GPA ...' style tail is dropped
    first. Kept to short lines so it does not fire on long descriptive bullets.
    Ranges are handled elsewhere."""
    s = line.strip().split("|")[0].strip()
    if not s or len(s.split()) > 6 or _bare_dates(s) is not None:
        return None
    m = _SINGLE_DATE.search(s)
    return m.group(1).strip() if m else None


def _looks_like_entry_header(line):
    """A structured header line (has a comma or an en-dash/hyphen separator) that
    is not a full sentence, so a lone date on the next line makes it an entry
    without mistaking a descriptive sentence for a header."""
    s = line.strip()
    return bool(s) and not s.endswith(".") and (
        "," in s or re.search(r"\s[\u2013\u2014-]\s", s) is not None)


_STRICT_MONTH = (r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
                 r"[a-z]*\.?")
_STRICT_DATE = (r"(?:" + _STRICT_MONTH + r"\s+)?(?:19|20)\d\d"
                r"|\d{1,2}/(?:19|20)\d\d|(?:19|20)\d\d")
_TRAILING_RANGE = re.compile(
    r"[\s,]+(" + _STRICT_DATE + r")\s*(?:to|until|[-\u2013\u2014])\s*"
    r"(present|current|ongoing|now|" + _STRICT_DATE + r")\s*$", re.I)


def _trailing_dates(line):
    """A header with a date range at the END and no parentheses, like
    'Developer, Globex 2018 to 2021' or 'Analyst, Acme Jan 2019 - Present'.
    Returns (header_without_dates, start, end), or None. Only accepts a header
    that still looks structured (has a comma or an en-dash) once the dates are
    removed, so a sentence that merely mentions a range is not mistaken for one."""
    m = _TRAILING_RANGE.search(line)
    if not m:
        return None
    header = line[:m.start()].strip().strip(",").strip()
    if not _looks_like_entry_header(header):
        return None
    end = m.group(2).strip()
    if re.search(r"present|current|ongoing|now", end, re.I):
        end = ""
    return header, m.group(1).strip(), end


def _split_header(header, key):
    """Split an entry header into fields, best effort. A 'Title - Company' style
    (en-dash or hyphen) is very common and puts the role or qualification first;
    a plain comma list we take with employer or institution first. The user
    reviews and corrects either way."""
    row = {}
    dash = re.split(r"\s+[\u2013\u2014-]\s+", header, maxsplit=1)
    if len(dash) == 2:
        left = dash[0].strip()
        right = dash[1].split(",")[0].strip()   # drop a trailing ", Location"
        if key == "education":
            row["qualification"], row["institution"] = left, right
        else:
            row["job_title"], row["employer"] = left, right
        return row
    parts = [p.strip() for p in header.split(",") if p.strip()]
    if not parts:
        return row
    if key == "education":
        row["qualification"] = parts[0]
        if len(parts) > 1:
            row["institution"] = parts[1]
    else:
        row["employer"] = parts[0]
        if len(parts) > 1:
            row["job_title"] = parts[1]
    return row


def _dated_entries(body, key):
    """Split a section body into entries. Handles dates in parentheses on the
    header line AND the common style where the header is one line and the date
    range is the next. Other lines become the current entry's description."""
    rows = []
    cur = None
    i = 0
    n = len(body)
    while i < n:
        ln = body[i]
        start, end, span = _dates(ln)
        if span is not None:
            header = (ln[:span[0]] + ln[span[1]:]).strip().strip(",").strip()
            cur = _split_header(header, key)
            cur["start_date"] = start
            cur["end_date"] = "" if re.search(
                r"present|current|ongoing|now", end, re.I) else end
            rows.append(cur)
            i += 1
            continue
        if not _is_bullet(ln):
            td = _trailing_dates(ln)
            if td is not None:
                header, s, e = td
                cur = _split_header(header, key)
                cur["start_date"], cur["end_date"] = s, e
                rows.append(cur)
                i += 1
                continue
        if (i + 1 < n and not _is_bullet(ln) and _bare_dates(ln) is None
                and _bare_dates(body[i + 1]) is not None):
            s, e = _bare_dates(body[i + 1])
            cur = _split_header(ln.strip(), key)
            cur["start_date"], cur["end_date"] = s, e
            rows.append(cur)
            i += 2
            continue
        if (i + 1 < n and _looks_like_entry_header(ln)
                and _bare_dates(body[i + 1]) is None
                and _single_date(body[i + 1]) is not None):
            cur = _split_header(ln.strip(), key)
            cur["end_date"] = _single_date(body[i + 1])   # graduation/single date
            rows.append(cur)
            i += 2
            continue
        if cur is not None:
            extra = cur.get("description", "")
            text = ln.lstrip("-\u2022*\u00b7 \t").strip()
            cur["description"] = (extra + " " + text).strip() if extra else text
        i += 1
    return rows


def _pair_entries(body, left, right):
    """Lines of the form 'Left: Right' (Skill: description, Language: level)."""
    rows = []
    for ln in body:
        if ":" in ln:
            a, b = ln.split(":", 1)
            row = {left: a.strip()}
            if b.strip():
                row[right] = b.strip()
            rows.append(row)
        elif ln.strip():
            rows.append({left: ln.strip()})
    return rows


def parse_cv_sections(text: str) -> dict:
    """Turn a CV into section entries (rows) for the profile's sections, keyed by
    the section name shown in the UI. Best effort: dates are pulled reliably; the
    title/organisation split is a sensible guess the user reviews and corrects,
    never committed silently. Returns {section_name: [row, ...]}."""
    lines = [ln.rstrip() for ln in (text or "").splitlines()]
    blocks = {}
    current = None
    for ln in lines:
        k = _heading_key(ln)
        if k:
            current = k
            blocks.setdefault(k, [])
            continue
        if current and ln.strip():
            blocks[current].append(ln.strip())

    out = {}
    for key, body in blocks.items():
        name = _SECTION_NAMES.get(key)
        if not name or not body:
            continue
        if key in ("education", "experience"):
            rows = _dated_entries(body, key)
        elif key == "skills":
            rows = _pair_entries(body, "skill", "description")
        elif key == "languages":
            rows = _pair_entries(body, "language", "proficiency")
        elif key == "certifications":
            rows = [{"name": ln} for ln in body if ln.strip()]
        else:
            rows = []
        if rows:
            out[name] = rows
    return out


def cv_to_fields(parsed: dict) -> dict:
    """Map a parsed CV (the parse_cv_text output) to the My-details field keys,
    for review in the dialog. Only the fields a CV reliably yields are mapped;
    the rest (address, city, ...) stay blank for the user to fill. The name is
    split on whitespace, which works across scripts (Latin, Arabic, and so on)."""
    out = {}
    for key in ("email", "phone", "linkedin"):
        value = parsed.get(key)
        if value:
            out[key] = value
    name = (parsed.get("full_name") or "").strip()
    if name:
        parts = name.split()
        out["given_name"] = parts[0]
        if len(parts) > 1:
            out["family_name"] = " ".join(parts[1:])
    return out


def extract_text(path: str) -> str:
    """Get plain text out of a CV file. Text, Word and PDF are what CVs actually
    come in. .docx is read with the standard library (a docx is just a zip of
    XML, so no lxml is needed); .pdf is read with the bundled PyMuPDF (compiled, self-contained).
    Image-only (scanned) PDFs yield little or no text and are the OCR case,
    handled by the fallback rung, not here."""
    ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""
    if ext in ("txt", "md"):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    if ext == "docx":
        return _docx_text(path)
    if ext == "pdf":
        return _pdf_text(path)
    raise NotImplementedError(f"unsupported CV format: .{ext}")


def _pdf_text(path: str) -> str:
    """Read a .pdf with PyMuPDF, a self-contained compiled library that fits
    NVDA's Python (unlike pure-Python readers that need stdlib NVDA omits). The
    Windows build is bundled in the add-on's lib folder; a system copy is used
    in development."""
    try:
        import pymupdf
    except Exception:
        import sys
        lib = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
        if lib not in sys.path:
            sys.path.insert(0, lib)
        import pymupdf
    doc = pymupdf.open(path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _docx_text(path: str) -> str:
    """Read a .docx using only the standard library. A .docx is a zip archive;
    the body text lives in word/document.xml as <w:t> runs inside <w:p> paras.
    Iterating paragraphs in document order also picks up table cells in place."""
    import zipfile
    from xml.etree import ElementTree as ET
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    lines = []
    for para in root.iter(W + "p"):
        lines.append("".join(node.text or "" for node in para.iter(W + "t")))
    return "\n".join(lines)

