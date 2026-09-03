"""Regression tests for the defects found in the line-by-line audit (0.9.74).
Each test names the defect it guards so a future change can't silently reopen it."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import controls, matcher, platforms, fingerprints  # noqa: E402


class TestOptionMatchingWordBoundary(unittest.TestCase):
    """Defect 1: 'No' matched inside 'Not applicable' / 'Prefer not to say'."""

    def test_short_value_does_not_match_inside_a_longer_word(self):
        for opts in (["Yes", "Prefer not to say"], ["Yes", "Not applicable"]):
            m = controls.choose_option("No", opts)
            self.assertIsNone(m.index, opts)
        self.assertIsNone(controls.choose_option("Nothing", ["No"]).index)

    def test_legitimate_matches_still_work(self):
        self.assertEqual(controls.choose_option("No", ["Yes", "No"]).label, "No")
        self.assertEqual(controls.choose_option(
            "Calif", ["California", "Lower California Sur"]).label, "California")
        self.assertEqual(controls.choose_option(
            "Bachelor", ["Bachelor of Science", "Master"]).label,
            "Bachelor of Science")

    def test_verify_does_not_false_confirm_midword(self):
        self.assertEqual(controls.verify_selection("No", "Not applicable"),
                         "mismatch")
        self.assertEqual(controls.verify_selection("UK", "United Kingdom (UK)"),
                         "confirmed")


class TestThirdPartyFieldsNotFilled(unittest.TestCase):
    """Defect 6: a referee's or emergency contact's name/email/phone matched as
    the user's own and would have been filled with their details."""

    def test_third_party_labels_hand_back(self):
        FD = matcher.FieldDescriptor
        for label in ["Name of referee", "Emergency contact name",
                      "Manager's email", "Referee phone number",
                      "Parent or guardian name", "Their email address",
                      "Next of kin phone"]:
            self.assertIsNone(matcher.match_field(FD(label=label)).key, label)

    def test_users_own_fields_still_match(self):
        FD = matcher.FieldDescriptor
        self.assertEqual(matcher.match_field(FD(label="Contact email")).key,
                         "email")
        self.assertEqual(matcher.match_field(FD(label="Your name")).key,
                         "full_name")
        self.assertEqual(matcher.match_field(FD(label="Mobile number")).key,
                         "phone")


class TestPlatformDetectionOnHost(unittest.TestCase):
    """Defect 5: raw substring on the whole URL misread clever.co as Lever and
    a query-string mention of greenhouse.io as Greenhouse."""

    def test_no_false_positives(self):
        self.assertEqual(platforms.detect("https://clever.co/jobs"), "")
        self.assertEqual(platforms.detect(
            "https://acme.com/careers?ref=greenhouse.io"), "")
        self.assertEqual(platforms.detect(
            "https://www.taleo.net.example.com/"), "")

    def test_real_hosts_detected(self):
        self.assertEqual(platforms.detect("https://jobs.lever.co/acme/x"), "lever")
        self.assertEqual(platforms.detect("boards.greenhouse.io/x"), "greenhouse")
        self.assertEqual(platforms.detect(
            "https://performancemanager.successfactors.eu/x"), "successfactors")


class TestFingerprintRegexNotLowercased(unittest.TestCase):
    """Defect 4: lowercasing the regex pattern turned \\D into \\d."""

    def test_uppercase_escape_class_survives(self):
        class FD:
            id = "abc--"; role = "editabletext"; placeholder = ""
            dom_class = ""; haspopup = ""; states = ()
        db = [{"when": {"id_regex": r"\D+--"}, "kind": "async_combobox"}]
        self.assertIsNotNone(fingerprints.match_fingerprint(FD(), "", db))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestPass1EmptyValueGuard(unittest.TestCase):
    """Pass 1: a blank value must never match a blank placeholder option."""

    def test_empty_or_whitespace_value_never_matches(self):
        for v in ("", "   ", "--"):
            m = controls.choose_option(v, ["--", "Yes", "No"])
            self.assertIsNone(m.index, repr(v))


class TestPass5And6(unittest.TestCase):
    """Passes 5-6: CV title lines are not names; location fields with a
    different referent (birth, study, the job's location) hand back;
    '00' is the international phone prefix."""

    def test_cv_title_not_taken_as_name(self):
        from core import cvparse
        self.assertEqual(cvparse.parse_cv_text(
            "Curriculum Vitae\nJohn Smith\nj@x.com").get("full_name"), "John Smith")
        self.assertEqual(cvparse.parse_cv_text(
            "PERSONAL PROFILE\n\nAmy Lee").get("full_name"), "Amy Lee")

    def test_different_referent_hands_back(self):
        FD = matcher.FieldDescriptor
        for l in ["Country of birth", "City of birth", "Country of study",
                  "Which city are you applying for", "Previous address"]:
            self.assertIsNone(matcher.match_field(FD(label=l)).key, l)
        for l in ["Country", "Country of residence", "Current city", "Town"]:
            self.assertIsNotNone(matcher.match_field(FD(label=l)).key, l)

    def test_00_international_prefix(self):
        from core import countries
        self.assertEqual(countries.phone_parts("00 44 7700 900000"),
                         ("+44", "7700900000"))
        self.assertEqual(countries.phone_parts("07700 900000"),
                         ("", "07700900000"))
