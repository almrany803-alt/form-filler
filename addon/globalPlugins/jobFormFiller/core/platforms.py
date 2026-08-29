"""Deterministic ATS platform detection, from the page URL first and DOM markers
as a fallback. Pure and offline, so it is unit-testable and shared by the
fingerprint database and the per-platform fill strategies.

The URL host is the strongest signal (Workday and Taleo hide their markup from
NVDA); the markup fallback lets a saved or embedded page still be recognised.
Returns a short platform name, or '' when nothing matches.
"""

# Host substrings -> platform. Checked in order; each is specific enough not to
# collide with the others.
_URL_MARKERS = [
    ("myworkdayjobs", "workday"),
    (".workday.", "workday"),
    ("job-boards.greenhouse", "greenhouse"),
    ("boards.greenhouse", "greenhouse"),
    ("greenhouse.io", "greenhouse"),
    ("lever.co", "lever"),
    ("ashbyhq.com", "ashby"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("icims.com", "icims"),
    ("taleo.net", "taleo"),
    ("successfactors", "successfactors"),
    ("sapsf.", "successfactors"),
    ("bamboohr.com", "bamboohr"),
    ("workable.com", "workable"),
    ("jobvite.com", "jobvite"),
    ("recruitee.com", "recruitee"),
]


def detect(url="", dom_class="", field_id=""):
    """Best-effort platform name from the page URL, then DOM markers."""
    u = (url or "").lower()
    for marker, name in _URL_MARKERS:
        if marker in u:
            return name

    cls = (dom_class or "").lower()
    idn = (field_id or "").lower()
    hay = cls + " " + idn

    # Greenhouse react-select uses a "select__..." class prefix.
    if "select__" in cls or "greenhouse" in hay:
        return "greenhouse"
    # SuccessFactors is SAP UI5.
    if "ui5" in cls or "sapm" in cls or idn[:2] == "sf" or "fbclc" in idn:
        return "successfactors"
    if "ashby" in hay:
        return "ashby"
    if "smartrecruiters" in hay:
        return "smartrecruiters"
    # Workday markup is hashed, but its field ids use a distinctive name--name
    # pattern (source--source, country--country, phoneNumber--countryPhoneCode).
    if "--" in idn or "wd-" in cls or "workday" in hay:
        return "workday"
    if "select2" in cls:
        return "select2"
    if "taleo" in hay:
        return "taleo"
    if "icims" in hay:
        return "icims"
    if "bamboohr" in hay:
        return "bamboohr"
    if "workable" in hay:
        return "workable"
    return ""
