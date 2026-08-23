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
    "address-level2": "city",
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
    "linkedin": {"en": ["linkedin", "linked in", "profile url"]},
    "postcode": {
        "en": ["postcode", "post code", "zip", "zip code", "postal code"],
        "es": ["codigo postal"], "fr": ["code postal"],
        "de": ["postleitzahl", "plz"], "it": ["codice postale", "cap"],
        "pt": ["codigo postal"], "pl": ["kod pocztowy"], "nl": ["postcode"],
        "ar": ["الرمز البريدي"],
    },
    "address_line1": {
        "en": ["address", "street", "address line 1"],
        "es": ["direccion", "calle"], "fr": ["adresse", "rue"],
        "de": ["adresse", "strasse"], "it": ["indirizzo", "via"],
        "pt": ["endereco", "morada", "rua"], "pl": ["adres", "ulica"],
        "nl": ["adres", "straat"], "ar": ["العنوان", "الشارع"],
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
        "en": ["first name", "given name", "forename"],
        "es": ["nombre"], "fr": ["prenom"], "de": ["vorname"],
        "it": ["nome"], "pt": ["primeiro nome", "nome proprio"],
        "pl": ["imie"], "nl": ["voornaam"], "ar": ["الاسم الاول"],
    },
    "family_name": {
        "en": ["last name", "surname", "family name"],
        "es": ["apellido", "apellidos"], "fr": ["nom de famille", "nom"],
        "de": ["nachname", "familienname"], "it": ["cognome"],
        "pt": ["apelido", "sobrenome"], "pl": ["nazwisko"],
        "nl": ["achternaam"], "ar": ["اسم العائلة", "الكنية"],
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
    best = None
    for key, langs in LEXICON.items():
        for lang, phrases in langs.items():
            for phrase in phrases:
                p = _norm(phrase)
                if p and p in t:
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
