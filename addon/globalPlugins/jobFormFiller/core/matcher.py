# matcher.py - identify which profile field a form field is asking for.
#
# Pure Python, no NVDA imports, fully testable.
# Signal order, strongest first:
#   1. autocomplete token  - author-declared purpose, LANGUAGE-INDEPENDENT.
#   2. label / aria-label  - matched against a MULTILINGUAL lexicon.
#   3. name / id           - developer-meaningful, usually latin.
#   4. placeholder         - a bad but common pattern; only a guess.

from dataclasses import dataclass
import re
import unicodedata

PROFILE_KEYS = (
    "given_name", "family_name", "full_name", "email", "phone",
    "address_line1", "city", "postcode", "country", "nationality",
    "date_of_birth", "linkedin", "work_authorisation",
)

_AUTOCOMPLETE = {
    "email": "email",
    "tel": "phone", "tel-national": "phone",
    "given-name": "given_name",
    "family-name": "family_name",
    "name": "full_name",
    "address-line1": "address_line1", "street-address": "address_line1",
    "address-line2": "address_line2", "address-line3": "address_line3",
    "address-level2": "city",
    "address-level1": "address_level1",
    "honorific-prefix": "name_prefix", "honorific-suffix": "name_suffix",
    "postal-code": "postcode",
    "country": "country", "country-name": "country",
    "url": "linkedin",
}

# Multilingual keyword lexicon: concept -> language -> phrases (stored already
# accent-folded / ascii, so folded labels match). Languages: en es fr de it pt
# pl nl ar. Extend a language by adding words; no code change needed.
LEXICON = {
    "email": {
        "en": ["email", "e-mail", "email address"],
        "es": ["correo electronico", "correo", "correo-e"],
        "fr": ["adresse e-mail", "courriel", "e-mail"],
        "de": ["e-mail-adresse", "e-mail"],
        "it": ["indirizzo email", "email", "posta elettronica"],
        "pt": ["endereco de email", "email", "correio eletronico"],
        "pl": ["adres e-mail", "e-mail", "poczta elektroniczna"],
        "nl": ["e-mailadres", "e-mail"],
        "ar": ["البريد الالكتروني", "بريد الكتروني"],
    },
    "phone": {
        "en": ["phone", "telephone", "mobile", "contact number"],
        "es": ["telefono", "numero de telefono", "movil"],
        "fr": ["telephone", "numero de telephone", "portable"],
        "de": ["telefon", "telefonnummer", "handy"],
        "it": ["telefono", "numero di telefono", "cellulare"],
        "pt": ["telefone", "numero de telefone", "telemovel"],
        "pl": ["telefon", "numer telefonu", "komorka"],
        "nl": ["telefoon", "telefoonnummer", "mobiel"],
        "ar": ["الهاتف", "رقم الهاتف", "جوال"],
    },
    "phone_country_code": {
        # A phone dialling-code field ("Country Phone Code", "+966"). Longer than
        # both "country" and "phone", so it wins; no stored value, so it falls to
        # "needs you" rather than the country name or the phone number.
        "en": ["country phone code", "phone country code", "country code",
               "phone code", "dialing code", "dial code", "calling code"],
    },
    "phone_extension": {
        "en": ["phone extension", "extension"],
    },
    "linkedin": {"en": ["linkedin", "linked in", "profile url"]},
    "postcode": {
        "en": ["postcode", "post code", "zip", "zip code", "postal code"],
        "es": ["codigo postal"], "fr": ["code postal"],
        "de": ["postleitzahl", "plz"], "it": ["codice postale", "cap"],
        "pt": ["codigo postal"], "pl": ["kod pocztowy"], "nl": ["postcode"],
        "ar": ["الرمز البريدي"],
    },
    "address_line1": {
        "en": ["address", "street", "address line 1", "street address",
               "mailing address", "residential address"],
        "es": ["direccion", "calle"], "fr": ["adresse", "rue"],
        "de": ["adresse", "strasse"], "it": ["indirizzo", "via"],
        "pt": ["endereco", "morada", "rua"], "pl": ["adres", "ulica"],
        "nl": ["adres", "straat"], "ar": ["العنوان", "الشارع"],
    },
    "address_line2": {
        # A second address line (apartment, suite, landmark). Longer than
        # "address", so it wins over line 1; not a stored value, so it falls to
        # "needs you" instead of duplicating line 1. Bare "unit" is deliberately
        # left out so it never grabs "Business Unit".
        "en": ["address line 2", "address line two", "apartment", "apt",
               "suite", "flat", "unit number", "landmark"],
        "es": ["complemento", "interior"], "it": ["interno"],
        "pt": ["complemento"], "nl": ["toevoeging"],
    },
    "address_line3": {
        "en": ["address line 3", "address line three"],
    },
    "address_housenumber": {
        # "House number" / "Building number". Longer than "street", so
        # "Street Number" beats the line-1 "street"; no stored value, needs you.
        "en": ["house number", "building number", "street number",
               "house no", "building no"],
        "de": ["hausnummer"], "nl": ["huisnummer"], "es": ["numero exterior"],
    },
    "address_level1": {
        # State / province / region (address-level1). Multilingual for global
        # forms; no stored value yet, so needs you until a profile holds it.
        "en": ["state", "province", "region", "county", "state province"],
        "es": ["provincia", "estado"], "de": ["bundesland"],
        "it": ["provincia", "regione"], "pt": ["estado"],
        "pl": ["wojewodztwo"], "nl": ["provincie"],
        "ar": ["المنطقة", "المحافظة"],
    },
    "address_level3": {
        # District / neighbourhood (address-level3), common in Gulf and Latin
        # American addresses.
        "en": ["district", "neighbourhood", "neighborhood", "suburb"],
        "es": ["barrio", "colonia"], "pt": ["bairro"], "ar": ["الحي"],
    },
    "name_prefix": {
        # Honorific / salutation (Mr, Mrs, Dr). Bare "title" is left out so a
        # "Job Title" field is never swallowed here. No stored value, needs you.
        "en": ["salutation", "honorific", "name prefix", "courtesy title"],
        "es": ["tratamiento"], "fr": ["civilite"], "de": ["anrede"],
        "nl": ["aanhef"],
    },
    "name_suffix": {
        "en": ["name suffix", "suffix"],
    },
    "city": {
        "en": ["city", "town"], "es": ["ciudad", "poblacion"],
        "fr": ["ville"], "de": ["stadt", "ort"], "it": ["citta"],
        "pt": ["cidade"], "pl": ["miasto", "miejscowosc"],
        "nl": ["stad", "plaats", "woonplaats"], "ar": ["المدينة"],
    },
    "country": {
        "en": ["country", "country of residence"], "es": ["pais"],
        "fr": ["pays"], "de": ["land", "staat"],
        "it": ["paese"], "pt": ["pais"],
        "pl": ["kraj", "panstwo"], "nl": ["land"],
        "ar": ["الدولة", "البلد", "بلد الاقامة"],
    },
    "nationality": {
        "en": ["nationality", "citizenship"], "es": ["nacionalidad"],
        "fr": ["nationalite"], "de": ["staatsangehorigkeit", "nationalitat"],
        "it": ["nazionalita"], "pt": ["nacionalidade"],
        "pl": ["narodowosc", "obywatelstwo"], "nl": ["nationaliteit"],
        "ar": ["الجنسية"],
    },
    "date_of_birth": {
        "en": ["date of birth", "birth date", "birthday", "born", "dob"],
        "es": ["fecha de nacimiento"], "fr": ["date de naissance"],
        "de": ["geburtsdatum"], "it": ["data di nascita"],
        "pt": ["data de nascimento"], "pl": ["data urodzenia"],
        "nl": ["geboortedatum"], "ar": ["تاريخ الميلاد", "تاريخ الميلاد"],
    },
    "work_authorisation": {
        "en": ["work authorisation", "work authorization", "right to work",
               "eligible to work", "authorised to work", "authorized to work",
               "visa", "sponsorship"],
        "es": ["autorizacion de trabajo", "permiso de trabajo"],
        "fr": ["autorisation de travail", "droit de travailler"],
        "de": ["arbeitserlaubnis"],
        "it": ["autorizzazione al lavoro", "permesso di lavoro"],
        "pt": ["autorizacao de trabalho", "direito ao trabalho"],
        "pl": ["pozwolenie na prace", "prawo do pracy"],
        "nl": ["werkvergunning", "arbeidsvergunning"],
    },
    "given_name": {
        "en": ["first name", "given name", "given names", "forename",
               "christian name"],
        "es": ["nombre"], "fr": ["prenom"], "de": ["vorname"],
        "it": ["nome"], "pt": ["primeiro nome", "nome proprio"],
        "pl": ["imie"], "nl": ["voornaam"], "ar": ["الاسم الاول"],
    },
    "family_name": {
        "en": ["last name", "surname", "family name", "last names"],
        "es": ["apellido", "apellidos"], "fr": ["nom de famille", "nom"],
        "de": ["nachname", "familienname"], "it": ["cognome"],
        "pt": ["apelido", "sobrenome"], "pl": ["nazwisko"],
        "nl": ["achternaam"], "ar": ["اسم العائلة", "الكنية"],
    },
    "father_name": {
        # The father's-name slot (Arabic-name forms label the middle field this
        # way). Longer than the bare "name", so it wins; not a stored profile
        # value, so the field correctly falls to "needs you" instead of the full
        # name.
        "en": ["father's name", "fathers name", "father name", "middle name"],
        "ar": ["اسم الاب", "اسم الأب"],
    },
    "preferred_name": {
        # "Preferred name" / "I have a preferred name" (often a checkbox). Never
        # the full name; no stored value, so it falls to "needs you".
        "en": ["preferred name"],
    },
    "full_name": {   # last: "name" is the weakest catch-all
        "en": ["full name", "your name", "name"],
        "es": ["nombre completo"], "fr": ["nom complet"],
        "de": ["vollstandiger name"], "it": ["nome completo"],
        "pt": ["nome completo"], "pl": ["imie i nazwisko"],
        "nl": ["volledige naam", "naam"], "ar": ["الاسم الكامل"],
    },
}

# latin letters that do NOT decompose under NFKD, mapped by hand.
_STROKE = str.maketrans({"ł": "l", "Ł": "l", "ø": "o", "Ø": "o",
                         "đ": "d", "Đ": "d", "ð": "d", "þ": "th", "ı": "i"})


@dataclass
class FieldDescriptor:
    role: str = "edit"
    label: str = ""
    aria_label: str = ""
    name: str = ""
    id: str = ""
    placeholder: str = ""
    autocomplete: str = ""
    input_type: str = ""
    roledescription: str = ""
    dom_class: str = ""
    haspopup: str = ""
    required: bool = False
    states: tuple = ()


@dataclass
class MatchResult:
    key: str | None
    confidence: str
    source: str = ""
    lang: str = ""


def _fold(s: str) -> str:
    s = (s or "").translate(_STROKE)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm(s: str) -> str:
    s = _fold(s)
    # Split camelCase / PascalCase so "firstName" reads as "first name"; many
    # ATS (Taleo, iCIMS) name fields that way, and without this "name" would
    # substring-match "firstname" and mislabel it as a full-name field.
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = s.lower()
    for ch in "_-[](){}./\\:":
        s = s.replace(ch, " ")
    return " ".join(s.split())


def _lexicon_hit(text: str):
    t = _norm(text)
    if not t:
        return None
    # Whole-word match, not substring: _norm has already reduced the text to
    # single-space-separated tokens, so wrapping both sides in spaces means a
    # phrase only matches on word boundaries. This stops short phrases matching
    # inside longer words, e.g. "state" no longer hits inside "real estate",
    # and "name" no longer hits inside "username". Longest phrase still wins,
    # so specific labels beat generic ones.
    padded = " " + t + " "
    best = None
    for key, langs in LEXICON.items():
        for lang, phrases in langs.items():
            for phrase in phrases:
                p = _norm(phrase)
                if not p:
                    continue
                # (a) phrase as consecutive whole words, or (b) the phrase with
                # its spaces removed as a single whole token. (b) catches the
                # no-separator attribute forms ATS use ("firstname", "emailaddress")
                # without reopening substring matches: "username" still won't hit
                # "name" because "name" is not a whole token of "username".
                joined = p.replace(" ", "")
                if (" " + p + " ") in padded or (" " + joined + " ") in padded:
                    if best is None or len(p) > best[2]:
                        best = (key, lang, len(p))
    return best


def match_field(fd: FieldDescriptor) -> MatchResult:
    ac = (fd.autocomplete or "").strip().lower()
    if ac in _AUTOCOMPLETE:
        return MatchResult(_AUTOCOMPLETE[ac], "strong", "autocomplete", "*")
    for text, src in ((fd.label, "label"), (fd.aria_label, "aria-label")):
        hit = _lexicon_hit(text)
        if hit:
            return MatchResult(hit[0], "strong", src, hit[1])
    for text, src in ((fd.name, "name"), (fd.id, "id")):
        hit = _lexicon_hit(text)
        if hit:
            return MatchResult(hit[0], "strong", src, hit[1])
    hit = _lexicon_hit(fd.placeholder)
    if hit:
        return MatchResult(hit[0], "guess", "placeholder", hit[1])
    return MatchResult(None, "none", "", "")
