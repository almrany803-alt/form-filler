"""Deterministic ATS platform detection, from the page URL first and DOM markers
as a fallback. Pure and offline, so it is unit-testable and shared by the
fingerprint database and the per-platform fill strategies.

The URL host is the strongest signal (Workday and Taleo hide their markup from
NVDA); the markup fallback lets a saved or embedded page still be recognised.
Returns a short platform name, or '' when nothing matches.
"""

# Host suffixes -> platform, matched against the parsed HOST only, at a label
# boundary (the host equals the suffix or ends with "." + suffix). Never a raw
# substring test on the whole URL: that misread "clever.co" as Lever and a page
# whose query string merely mentioned greenhouse.io as Greenhouse.
_HOST_SUFFIXES = [
    ("myworkdayjobs.com", "workday"),
    ("workday.com", "workday"),
    ("greenhouse.io", "greenhouse"),
    ("lever.co", "lever"),
    ("ashbyhq.com", "ashby"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("icims.com", "icims"),
    ("taleo.net", "taleo"),
    ("bamboohr.com", "bamboohr"),
    ("workable.com", "workable"),
    ("jobvite.com", "jobvite"),
    ("recruitee.com", "recruitee"),
]
# Whole host labels -> platform, for vendors that use several TLDs
# (successfactors.com and .eu; sapsf) or appear as a label (myworkdayjobs).
_HOST_LABELS = [
    ("myworkdayjobs", "workday"),
    ("workday", "workday"),
    ("successfactors", "successfactors"),
    ("sapsf", "successfactors"),
]


def _host(url):
    """The lower-cased hostname of a URL, or '' if it cannot be parsed."""
    from urllib.parse import urlparse
    u = (url or "").strip()
    if not u:
        return ""
    if "://" not in u:
        u = "https://" + u
    try:
        return (urlparse(u).hostname or "").lower()
    except Exception:
        return ""


def detect(url="", dom_class="", field_id=""):
    """Best-effort platform name from the page host, then DOM markers."""
    host = _host(url)
    if host:
        for suffix, name in _HOST_SUFFIXES:
            if host == suffix or host.endswith("." + suffix):
                return name
        labels = host.split(".")
        for label, name in _HOST_LABELS:
            if label in labels:
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
