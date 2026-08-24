"""Tests for the field fingerprint database, checked against the REAL Workday
field signals captured in the user's live logs. This is the proof that the
database approach is testable in CI: deterministic signals in, known kind out."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "addon", "globalPlugins", "jobFormFiller"))

from core import fingerprints  # noqa: E402


class FakeFD:
    """A stand-in field descriptor with just the signals the database reads."""
    def __init__(self, id="", role="", placeholder="", dom_class="",
                 haspopup="", states=()):
        self.id = id
        self.role = role
        self.placeholder = placeholder
        self.dom_class = dom_class
        self.haspopup = haspopup
        self.states = states


class TestRealWorkdaySignals(unittest.TestCase):
    """Signals taken verbatim from the JFF logs on the live Workday form."""

    def test_how_did_you_hear_source_is_a_dropdown(self):
        # JFF read: id='source--source' role='editabletext' placeholder='Search'
        fd = FakeFD(id="source--source", role="editabletext",
                    placeholder="Search")
        r = fingerprints.match_fingerprint(fd, platform="workday")
        self.assertIsNotNone(r)
        self.assertEqual(r["kind"], "async_combobox")

    def test_country_button_is_a_button_dropdown(self):
        # JFF raw: id='country--country' tag=button haspopup=listbox
        fd = FakeFD(id="country--country", role="button", haspopup="listbox")
        r = fingerprints.match_fingerprint(fd, platform="workday")
        self.assertIsNotNone(r)
        self.assertEqual(r["kind"], "button_dropdown")

    def test_preferred_name_checkbox_is_boolean_not_a_name(self):
        # id='name--preferredCheck' type=checkbox (was mis-matched to full_name)
        fd = FakeFD(id="name--preferredCheck", role="checkbox")
        r = fingerprints.match_fingerprint(fd, platform="workday")
        self.assertIsNotNone(r)
        self.assertEqual(r["kind"], "checkbox")

    def test_country_phone_code_search_prompt_is_a_dropdown(self):
        # id='phoneNumber--countryPhoneCode' role=input placeholder='Search'
        fd = FakeFD(id="phoneNumber--countryPhoneCode", role="editabletext",
                    placeholder="Search")
        r = fingerprints.match_fingerprint(fd, platform="workday")
        self.assertIsNotNone(r)
        self.assertEqual(r["kind"], "async_combobox")


class TestNoFalsePositives(unittest.TestCase):
    def test_plain_text_field_not_matched(self):
        fd = FakeFD(id="input-5", role="editabletext", placeholder="First name")
        self.assertIsNone(fingerprints.match_fingerprint(fd, platform="workday"))

    def test_search_prompt_only_on_workday(self):
        # same signals but a different platform: our seed doesn't claim it
        fd = FakeFD(id="x", role="editabletext", placeholder="Search")
        self.assertIsNone(fingerprints.match_fingerprint(fd, platform="greenhouse"))

    def test_no_platform_no_match(self):
        fd = FakeFD(id="source--source", role="editabletext",
                    placeholder="Search")
        self.assertIsNone(fingerprints.match_fingerprint(fd, platform=""))


class TestDatabaseIntegrity(unittest.TestCase):
    def test_database_loads(self):
        self.assertGreaterEqual(len(fingerprints._load()), 4)

    def test_unknown_condition_fails_closed(self):
        db = [{"id": "bad", "when": {"nonsense_key": "x"}, "kind": "text"}]
        fd = FakeFD(id="anything")
        self.assertIsNone(
            fingerprints.match_fingerprint(fd, platform="workday", db=db))


if __name__ == "__main__":
    unittest.main()
