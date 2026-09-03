"""Date helpers (audit pass 3). The old whole-hint scan read prose letters as
format letters; the segment test matched 'day' inside 'birthday'."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import dates  # noqa: E402


class TestOrderAndSeparator(unittest.TestCase):
    def test_format_token_wins_over_prose(self):
        self.assertEqual(dates.order_from_hint("Date (mm/dd/yyyy)"), "MDY")
        self.assertEqual(dates.order_from_hint("Your date of birth: yyyy-mm-dd"), "YMD")
        self.assertEqual(dates.order_from_hint("DD/MM/YYYY"), "DMY")

    def test_separator_from_token_not_prose(self):
        self.assertEqual(dates.separator_from_hint("e.g. 15/03/1990"), "/")
        self.assertEqual(dates.separator_from_hint("Start date - dd.mm.yyyy"), ".")

    def test_word_fallback_and_none(self):
        self.assertEqual(dates.order_from_hint("Day / Month / Year"), "DMY")
        self.assertEqual(dates.order_from_hint("Enter a date"), "")

    def test_format_date(self):
        self.assertEqual(dates.format_date("1990", "03", "15", "DMY", "/"),
                         "15/03/1990")


class TestSegment(unittest.TestCase):
    def test_birthday_ids_map_to_their_own_segment(self):
        self.assertEqual(dates.segment_from("birthday_day", ""), "day")
        self.assertEqual(dates.segment_from("birthday_month", ""), "month")
        self.assertEqual(dates.segment_from("birthday_year", ""), "year")

    def test_camel_case_and_class(self):
        self.assertEqual(dates.segment_from("dobYear", ""), "year")
        self.assertEqual(dates.segment_from("", "date month"), "month")

    def test_not_a_date_segment(self):
        self.assertIsNone(dates.segment_from("first_name", "input"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
