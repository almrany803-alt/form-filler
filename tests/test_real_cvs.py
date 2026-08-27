"""Parser tests over real and realistic CVs in different structural formats.

One fixture (sarah_mitchell) is a real sample resume grabbed online; the others
model other common real structures (parenthetical year ranges, en-dash headers,
different section headings). Testing these directly drove the parser's support
for dates that sit on their own line, which real CVs use constantly and the
first version missed. Pure logic, so it runs in the fast suite.
"""

import glob
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import cvparse  # noqa: E402

_DIR = os.path.join(os.path.dirname(__file__), "..", "betatest", "cv_samples")


def _parse(name):
    text = open(os.path.join(_DIR, name), encoding="utf-8").read()
    return (cvparse.cv_to_fields(cvparse.parse_cv_text(text)),
            cvparse.parse_cv_sections(text))


class TestRealCVs(unittest.TestCase):
    def test_every_fixture_gives_email_and_dated_experience(self):
        files = glob.glob(os.path.join(_DIR, "*.txt"))
        self.assertTrue(files, "no CV fixtures found")
        for path in files:
            name = os.path.basename(path)
            fields, secs = _parse(name)
            self.assertIn("email", fields, name)
            exp = secs.get("Experience", [])
            self.assertGreaterEqual(len(exp), 2, "%s: too few experience" % name)
            for r in exp:
                self.assertTrue(r.get("start_date"),
                                "%s: an experience entry has no start date: %r"
                                % (name, r))

    def test_sarah_separate_line_endash_dates(self):
        fields, secs = _parse("sarah_mitchell.txt")
        self.assertEqual((fields.get("given_name"), fields.get("family_name")),
                         ("Sarah", "Mitchell"))
        self.assertEqual(len(secs["Experience"]), 3)
        first = secs["Experience"][0]
        self.assertEqual(first["job_title"], "Senior Product Manager")
        self.assertEqual(first["employer"], "Streamline Inc.")
        self.assertEqual(first["start_date"], "March 2021")
        self.assertEqual(first["end_date"], "")   # "Present"
        # single graduation date (no range)
        self.assertEqual(len(secs["Education"]), 1)
        self.assertEqual(secs["Education"][0]["institution"], "University of Texas")
        self.assertEqual(secs["Education"][0]["end_date"], "May 2016")

    def test_david_mm_yyyy_dates_and_multiple_headings(self):
        _, secs = _parse("david_okoro.txt")
        # "Professional Experience" and "Career History" both feed Experience
        self.assertEqual(len(secs["Experience"]), 3)
        self.assertEqual(secs["Experience"][0]["start_date"], "09/2019")
        self.assertEqual(secs["Experience"][0]["end_date"], "06/2022")
        self.assertEqual(secs["Education"][0]["end_date"], "2015")

    def test_lena_mixed_formats_in_one_cv(self):
        _, secs = _parse("lena_fischer.txt")
        # one entry parenthetical, one separate-line, both must parse
        self.assertEqual(len(secs["Experience"]), 2)
        self.assertEqual(secs["Experience"][0]["end_date"], "")   # Present
        self.assertEqual(secs["Experience"][1]["start_date"], "2017")
        self.assertEqual(len(secs["Languages"]), 2)

    def test_marcus_parenthetical_year_ranges(self):
        _, secs = _parse("marcus_reid.txt")
        self.assertEqual(len(secs["Experience"]), 2)
        self.assertEqual(len(secs["Education"]), 1)
        self.assertEqual(secs["Experience"][0]["start_date"], "2019")

    def test_aisha_endash_headers_and_languages(self):
        _, secs = _parse("aisha_khan.txt")
        self.assertEqual(len(secs["Experience"]), 2)
        self.assertEqual(secs["Experience"][0]["job_title"], "Marketing Manager")
        self.assertEqual(secs["Experience"][0]["employer"], "BrightWave")
        self.assertEqual(len(secs["Languages"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
