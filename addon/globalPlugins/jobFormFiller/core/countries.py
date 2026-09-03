# countries.py - one bundled dataset of every country, so country and
# nationality become an accessible dropdown you pick from, and the addon can
# still match the page's option, and detect a CV's country, whatever language
# it is written in.
#
# The data (countries.json) is built from the mledoze/countries dataset: for
# each country its canonical English name, ISO code, phone calling code(s),
# whether it is independent, and every name it goes by, official, common,
# native, demonyms, and translations across two dozen languages. That is why a
# form that lists السعودية, Arabie Saoudite or 沙特阿拉伯 still matches "Saudi
# Arabia", and why the demonym "Saudi" resolves too: they are all one country.
#
# Matching is script-aware, because scripts differ:
#   - Latin, Cyrillic, Arabic and Korean put spaces between words, so we match a
#     name as a whole word. Short foreign names (مصر, cin) are allowed; short
#     ASCII strings are not, so a two-letter code like "in" cannot match the
#     word "in" in a sentence.
#   - Chinese and Japanese do not use spaces, so for those we match by substring.
# Names are compared accent-folded, so Turkiye matches Turkiye either spelling.
#
# Pure Python and deterministic. No network at run time; the list is bundled.

import json
import os
import re
import unicodedata

_DATA = None            # list of {name, cca2, independent, aliases[], codes[]}
_NAMES = None           # sorted canonical English names, for the dropdown
_ALIAS_TO_NAME = None   # folded alias -> canonical name (first wins)
_FOLDED = None          # canonical name -> set of folded aliases (for matching)
_DETECT = None          # list of (folded_alias, name, is_cjk) for CV detection


def _light(s) -> str:
    """Lowercase, punctuation to space, whitespace collapsed. Accents and the
    script are KEPT, so we can still tell which script a name is in."""
    s = unicodedata.normalize("NFC", str(s or ""))
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return " ".join(s.lower().split())


def _fold(s) -> str:
    """_light plus accent-stripping, for equality that ignores diacritics, so
    an accented and a plain spelling are the same. Non-Latin scripts pass
    through unchanged."""
    s = unicodedata.normalize("NFKD", _light(s))
    return "".join(c for c in s if not unicodedata.combining(c))


def _is_cjk(s) -> bool:
    """True if the text is Chinese or Japanese, which do not delimit words with
    spaces. Korean Hangul is deliberately excluded: it does use spaces."""
    for ch in s:
        o = ord(ch)
        if (0x3040 <= o <= 0x30FF or 0x3400 <= o <= 0x4DBF
                or 0x4E00 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF):
            return True
    return False


def _load():
    global _DATA, _NAMES, _ALIAS_TO_NAME, _FOLDED, _DETECT
    if _DATA is not None:
        return
    path = os.path.join(os.path.dirname(__file__), "countries.json")
    try:
        with open(path, encoding="utf-8") as fh:
            _DATA = json.load(fh)
    except Exception:
        _DATA = []
    _NAMES = sorted(c["name"] for c in _DATA)
    _ALIAS_TO_NAME = {}
    _FOLDED = {}
    _DETECT = []
    for c in _DATA:
        name = c["name"]
        folded = set()
        for a in c["aliases"] + [_light(name)]:
            fa = _fold(a)
            if not fa:
                continue
            folded.add(fa)
            _ALIAS_TO_NAME.setdefault(fa, name)
            # a name is usable for CV detection if it is long enough not to be a
            # stray code: two chars for a script with word boundaries or for
            # spaceless CJK, four for a plain ASCII string like "usa" vs "us".
            cjk = _is_cjk(a)
            ok = len(a) >= (2 if (cjk or not a.isascii()) else 4)
            if ok:
                _DETECT.append((fa, name, cjk))
        _FOLDED[name] = folded


def country_names() -> list:
    """The canonical English country names, sorted, for the profile dropdown."""
    _load()
    return list(_NAMES)


def canonical(value: str) -> str:
    """Resolve any form of a country, a translation, a demonym, an alt spelling,
    to its canonical English name. Empty string if it is not a country."""
    _load()
    return _ALIAS_TO_NAME.get(_fold(value), "")


def match_country(value: str, options: list):
    """Given the user's country (any form) and the page's option labels (any
    language), return (index, label, confidence). 'strong' for an exact match,
    'guess' for whole-word containment, (None, '', 'none') when nothing fits so
    the caller can hand the list back for the user to pick."""
    _load()
    name = canonical(value)
    aliases = _FOLDED.get(name, {_fold(value)})
    fold_opts = [_fold(o) for o in options]

    for i, o in enumerate(fold_opts):
        if o in aliases:
            return i, options[i], "strong"
    for i, o in enumerate(fold_opts):
        if not o:
            continue
        po = " " + o + " "
        for a in aliases:
            if len(a) < 4:
                continue
            pa = " " + a + " "
            if pa in po or po in pa:
                return i, options[i], "guess"
    return None, "", "none"


def country_from_phone(phone: str) -> str:
    """The country whose calling code is the longest prefix of this phone
    number, or ''. A +966 number is Saudi Arabia, a +44 number is the UK. Where
    a code is shared (the UK and the Crown Dependencies both use +44), the
    independent country wins."""
    _load()
    digits = "+" + re.sub(r"\D", "", str(phone or ""))
    if digits == "+":
        return ""
    best_name, best_len, best_indep = "", 0, False
    for c in _DATA:
        indep = bool(c.get("independent"))
        for code in c.get("codes", []):
            if digits.startswith(code) and (
                    len(code) > best_len
                    or (len(code) == best_len and indep and not best_indep)):
                best_name, best_len, best_indep = c["name"], len(code), indep
    return best_name


_ROOTS = None


def _root_codes():
    """Set of root dial codes, with the North-American +1XXX area codes
    collapsed to a single '+1', built once."""
    global _ROOTS
    if _ROOTS is None:
        _load()
        r = set()
        for c in _DATA:
            for code in c.get("codes", []):
                r.add("+1" if code.startswith("+1") and len(code) > 2 else code)
        _ROOTS = r
    return _ROOTS


def phone_parts(phone: str):
    """Split a phone into (dial_code, national_number), e.g. '+966569277208' ->
    ('+966', '569277208'). Only splits an EXPLICITLY international number (one
    that starts with '+'); a plain national number is returned as ('', digits)
    untouched, so we never guess a country code onto a number that did not have
    one. Uses the bundled calling codes, collapsing the North American +1XXX
    area codes to '+1' so an area code is never mistaken for the dial code."""
    raw = str(phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return "", ""
    # "00" is the international prefix in the UK and most of Europe: "00 44
    # 7700 900000" is the same number as "+44 7700 900000". Treat it as such.
    if not raw.startswith("+") and digits.startswith("00") and len(digits) > 4:
        raw = "+" + digits[2:]
        digits = digits[2:]
    if not raw.startswith("+"):
        return "", digits
    plus = "+" + digits
    best = ""
    for code in _root_codes():
        if plus.startswith(code) and len(code) > len(best):
            best = code
    if not best:
        return "", digits
    return best, plus[len(best):]


def detect_country(text: str, phone: str = "") -> str:
    """Best guess at the country a CV states, in any of the supported languages.
    A phone calling code is the most reliable signal, so try that first;
    otherwise look for an explicit country name in the text, matching by whole
    word for spaced scripts and by substring for Chinese and Japanese. Returns a
    canonical English name, or ''. A best guess the user confirms, not a fact."""
    _load()
    if phone:
        by_phone = country_from_phone(phone)
        if by_phone:
            return by_phone
    fold_text = _fold(text)
    padded = " " + fold_text + " "
    best_name, best_len = "", 0
    for fa, name, cjk in _DETECT:
        hit = (fa in fold_text) if cjk else ((" " + fa + " ") in padded)
        if hit and len(fa) > best_len:
            best_name, best_len = name, len(fa)
    return best_name
