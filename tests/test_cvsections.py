import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import cvparse  # noqa: E402


CV = """Jane Doe
jane@example.com
EDUCATION
BSc Computer Science, Test University, London (Sep 2018 to Jun 2021)
First class honours.
Diploma in Design, Some College (Sep 2016 to Jul 2018)
CERTIFICATIONS AND PROFESSIONAL DEVELOPMENT
AWS Certified Cloud Practitioner, 2022
EXPERIENCE
Acme Corp, Software Engineer (Jan 2022 to present)
Built and shipped things.
SKILLS
Python: backend work
Testing
LANGUAGES
English: Native
French: Intermediate
INTERESTS
Hiking and photography
REFERENCES
Available on request.
"""


class TestParseCvSections(unittest.TestCase):
    def setUp(self):
        self.secs = cvparse.parse_cv_sections(CV)

    def test_education_entries(self):
        edu = self.secs["Education"]
        self.assertEqual(len(edu), 2)
        self.assertEqual(edu[0]["qualification"], "BSc Computer Science")
        self.assertEqual(edu[0]["institution"], "Test University")
        self.assertEqual(edu[0]["start_date"], "Sep 2018")
        self.assertEqual(edu[0]["end_date"], "Jun 2021")
        self.assertIn("First class", edu[0].get("description", ""))

    def test_experience_present_is_blank_end(self):
        exp = self.secs["Experience"]
        self.assertEqual(len(exp), 1)
        self.assertEqual(exp[0]["employer"], "Acme Corp")
        self.assertEqual(exp[0]["job_title"], "Software Engineer")
        self.assertEqual(exp[0]["start_date"], "Jan 2022")
        self.assertEqual(exp[0]["end_date"], "")   # "present" -> blank

    def test_skills_and_languages(self):
        self.assertEqual(
            [r["skill"] for r in self.secs["Skills"]], ["Python", "Testing"])
        langs = self.secs["Languages"]
        self.assertEqual(langs[0], {"language": "English", "proficiency": "Native"})
        # Languages must NOT bleed into Interests / References
        self.assertEqual(len(langs), 2)

    def test_boundaries_and_unseeded_sections(self):
        # Certifications recognised despite the long heading; not bled into education
        self.assertIn("Certifications", self.secs)
        self.assertEqual(len(self.secs["Education"]), 2)
        # Interests / References are boundaries, not seeded sections
        self.assertNotIn("Interests", self.secs)
        self.assertNotIn("References", self.secs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
