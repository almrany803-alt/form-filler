"""The country dataset is what lets country and nationality become an
accessible dropdown you pick from, while still matching a page's option in any
language. These lock the behaviour that matters on real Gulf and European forms:
the Arabic option matches, the demonym resolves, and a +966 phone means Saudi
Arabia. If any of these break, the nationality bug from the logs comes back."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "addon", "globalPlugins", "jobFormFiller"))

from core import countries  # noqa: E402


class Dataset(unittest.TestCase):
    def test_list_is_complete_and_sorted(self):
        names = countries.country_names()
        self.assertGreater(len(names), 190)          # ~250 territories
        self.assertEqual(names, sorted(names))
        self.assertIn("Saudi Arabia", names)
        self.assertIn("United Kingdom", names)


class CanonicalResolution(unittest.TestCase):
    def test_demonym_resolves(self):
        # the exact bug from the log: "Saudi" is a demonym, not a country name.
        self.assertEqual(countries.canonical("Saudi"), "Saudi Arabia")

    def test_arabic_name_resolves(self):
        self.assertEqual(countries.canonical("السعودية"), "Saudi Arabia")

    def test_french_name_resolves(self):
        self.assertEqual(countries.canonical("Royaume-Uni"), "United Kingdom")

    def test_non_country_is_empty(self):
        self.assertEqual(countries.canonical("not a country"), "")


class OptionMatching(unittest.TestCase):
    def test_matches_arabic_option_from_english_country(self):
        # profile country "Saudi Arabia", the page lists Arabic options.
        opts = ["إختار", "مصر", "السعودية", "الإمارات العربية المتحدة"]
        idx, label, conf = countries.match_country("Saudi Arabia", opts)
        self.assertEqual(label, "السعودية")
        self.assertEqual(conf, "strong")

    def test_matches_arabic_option_from_demonym(self):
        # profile nationality "Saudi" (a demonym) against Arabic country options.
        opts = ["إختار", "السعودية", "الكويت"]
        idx, label, conf = countries.match_country("Saudi", opts)
        self.assertEqual(label, "السعودية")
        self.assertEqual(conf, "strong")

    def test_matches_french_option(self):
        opts = ["France", "Royaume-Uni", "Allemagne"]
        idx, label, conf = countries.match_country("United Kingdom", opts)
        self.assertEqual(label, "Royaume-Uni")

    def test_no_false_oman_in_romania(self):
        # the containment trap: Oman must not match inside Romania.
        idx, label, conf = countries.match_country("Oman", ["Romania", "Poland"])
        self.assertIsNone(idx)

    def test_hands_back_when_nothing_fits(self):
        idx, label, conf = countries.match_country("Saudi Arabia", ["Foo", "Bar"])
        self.assertIsNone(idx)
        self.assertEqual(conf, "none")


class PhoneAndDetection(unittest.TestCase):
    def test_saudi_phone(self):
        self.assertEqual(countries.country_from_phone("+966 56 927 7208"),
                         "Saudi Arabia")

    def test_uk_phone(self):
        self.assertEqual(countries.country_from_phone("+44 7735 829412"),
                         "United Kingdom")

    def test_local_phone_no_code_is_empty(self):
        # a bare UK local number carries no country code, so it cannot be known.
        self.assertEqual(countries.country_from_phone("07735829412"), "")

    def test_detect_prefers_phone_code(self):
        # a CV that mentions the UK heavily but has a +966 phone is Saudi.
        text = "Studied in the United Kingdom, University of the West of England."
        self.assertEqual(countries.detect_country(text, phone="+966569277208"),
                         "Saudi Arabia")

    def test_detect_from_text_when_no_phone_code(self):
        text = "Address: Bristol, United Kingdom. Phone: 07735829412"
        self.assertEqual(countries.detect_country(text), "United Kingdom")

    def test_detect_empty_on_no_country(self):
        self.assertEqual(countries.detect_country("just some words here"), "")


if __name__ == "__main__":
    unittest.main()


class AllLanguagesDetect(unittest.TestCase):
    """Lock that a CV stating its country by full name is detected across every
    script the dataset carries: Latin, Cyrillic, Arabic, CJK and Korean. These
    are the realistic case, a CV written in the applicant's own language."""

    CASES = [
        ("السعودية", "Saudi Arabia"),        # Arabic
        ("مصر", "Egypt"),                     # Arabic, short name
        ("中国", "China"),                     # Chinese, no spaces
        ("日本", "Japan"),                     # Japanese, no spaces
        ("德国", "Germany"),                   # Chinese
        ("Россия", "Russia"),                 # Cyrillic
        ("Deutschland", "Germany"),           # German
        ("Allemagne", "Germany"),             # French
        ("España", "Spain"),                  # Spanish, accented
        ("Polska", "Poland"),                 # Polish
        ("ایران", "Iran"),                    # Persian
        ("대한민국", "South Korea"),            # Korean
    ]

    def test_each_language_full_name_detects(self):
        for local, want in self.CASES:
            text = "Address: some city, %s. Contact below." % local
            got = countries.detect_country(text)
            self.assertEqual(got, want,
                             "%r should detect as %s, got %r" % (local, want, got))


class ChooseOptionIntegration(unittest.TestCase):
    """Lock the fix at the integration point: the fill path's option chooser
    resolves country and nationality through the dataset, so the exact bug from
    the log, nationality 'Saudi' against Arabic options, cannot come back."""

    def setUp(self):
        from core import controls
        self.controls = controls

    def test_nationality_saudi_matches_arabic(self):
        opts = ["إختار", "السعودية", "الكويت"]
        pick = self.controls.choose_option("Saudi", opts, concept="nationality")
        self.assertEqual(pick.label, "السعودية")
        self.assertEqual(pick.confidence, "strong")

    def test_country_matches_french(self):
        opts = ["France", "Royaume-Uni", "Allemagne"]
        pick = self.controls.choose_option(
            "United Kingdom", opts, concept="country")
        self.assertEqual(pick.label, "Royaume-Uni")

    def test_plain_field_unaffected_by_country_path(self):
        pick = self.controls.choose_option(
            "Yes", ["Yes", "No"], concept="work_authorisation")
        self.assertEqual(pick.label, "Yes")


class TestPhoneParts(unittest.TestCase):
    def test_splits_international_numbers(self):
        self.assertEqual(countries.phone_parts("+966569277208"),
                         ("+966", "569277208"))
        self.assertEqual(countries.phone_parts("+44 1234 567890"),
                         ("+44", "1234567890"))
        # North American numbers collapse to +1, area code stays in the number
        self.assertEqual(countries.phone_parts("+1 (201) 555-1234"),
                         ("+1", "2015551234"))

    def test_does_not_guess_a_code_onto_a_plain_number(self):
        # No leading '+': never invent a country code (569... is not Chile)
        self.assertEqual(countries.phone_parts("569277208"), ("", "569277208"))
        self.assertEqual(countries.phone_parts("0569277208"), ("", "0569277208"))
        self.assertEqual(countries.phone_parts(""), ("", ""))
