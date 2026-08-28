"""choose_option must prefer exact and synonym matches, and hand back rather
than risk the wrong option when a value is contained in several (the Workday
'saved a wrong hidden id' trap). Pure logic."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import controls  # noqa: E402


class TestChooseOption(unittest.TestCase):
    def test_exact_wins_even_with_a_longer_containing_option(self):
        m = controls.choose_option("California",
                                   ["California", "Lower California Sur"])
        self.assertEqual(m.label, "California")
        self.assertEqual(m.confidence, "strong")

    def test_ambiguous_containment_hands_back(self):
        m = controls.choose_option("Calif",
                                   ["Baja California", "Lower California Sur"])
        self.assertIsNone(m.index)
        self.assertEqual(m.confidence, "none")

    def test_prefix_resolves_ambiguity(self):
        m = controls.choose_option("Calif",
                                   ["California", "Lower California Sur"])
        self.assertEqual(m.label, "California")

    def test_single_containment_is_a_helpful_guess(self):
        m = controls.choose_option("Bachelor",
                                   ["Bachelor of Science", "Master of Arts"])
        self.assertEqual(m.label, "Bachelor of Science")
        self.assertEqual(m.confidence, "guess")

    def test_no_match_hands_back(self):
        m = controls.choose_option("PhD", ["Bachelor of Science", "Master"])
        self.assertIsNone(m.index)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestNormalizeValueAndVerify(unittest.TestCase):
    def test_normalize_value(self):
        from core import matcher
        self.assertEqual(matcher.normalize_value("  John   Smith  "), "John Smith")
        self.assertEqual(matcher.normalize_value("+44 7700 900000"), "+44 7700 900000")
        self.assertEqual(matcher.normalize_value("line1\nline2"), "line1 line2")
        self.assertEqual(matcher.normalize_value("a\u200bb\tc"), "ab c")

    def test_verify_selection_permissive_on_containment(self):
        # verify stays permissive: an abbreviation reads back as its full value
        self.assertEqual(
            controls.verify_selection("UK", "United Kingdom (UK)"), "confirmed")
        self.assertEqual(
            controls.verify_selection("California", "California, United States"),
            "confirmed")
        self.assertEqual(
            controls.verify_selection("California", "California"), "confirmed")
        # a genuinely different read-back is a mismatch
        self.assertEqual(
            controls.verify_selection("California", "Texas"), "mismatch")
