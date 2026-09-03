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


class TestMonthYearHelpers(unittest.TestCase):
    """The career-date parse/format round-trip. Skipped where wx is absent
    (the sandbox); the live NVDA test exercises the real picker."""

    def setUp(self):
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                            "addon", "globalPlugins", "jobFormFiller"))
            import dialogs
            self.d = dialogs
        except Exception:
            self.skipTest("wx not available")

    def test_parse_and_format_roundtrip(self):
        for value, expect in (("Sep 2023", "Sep 2023"),
                              ("September 2023", "Sep 2023"),
                              ("2020", "2020"), ("present", None),
                              ("current", None), ("", "")):
            present, m, y = self.d._parse_monthyear(value)
            out = "present" if present else self.d._format_monthyear(m, y)
            if expect is None:
                self.assertTrue(present, value)
            else:
                self.assertEqual(out, expect, value)


class TestApplyImport(unittest.TestCase):
    """The replace-on-import logic. Skipped where wx is absent (sandbox); the
    live NVDA test exercises the real preview dialog end to end."""

    def setUp(self):
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                            "addon", "globalPlugins", "jobFormFiller"))
            import dialogs
            from core import profile
        except Exception:
            self.skipTest("wx not available")
        import tempfile
        self.d = dialogs
        self.profile = profile
        self.store = profile.ProfileStore(
            os.path.join(tempfile.mkdtemp(), "p.dat"), profile.NullCrypto())
        self.store.load()
        self.store.add_profile("Me", {"given_name": "Old", "email": "old@x.com"})
        self.store.set_active("Me")
        self.store.add_row("Experience", {"job_title": "Old job"})
        self.store.add_row("Experience", {"job_title": "Older job"})

    def test_replaces_chosen_keeps_declined(self):
        fields = {"given_name": "New", "phone": "123"}
        sections = {"Experience": [{"job_title": "A"}, {"job_title": "B"}],
                    "Education": [{"qualification": "Deg"}]}
        added = self.d._apply_import(self.store, fields, sections,
                                     take_personal=True,
                                     take_sections={"Experience"})
        p = self.store.get_active()
        self.assertEqual(p["given_name"], "New")          # replaced
        self.assertEqual(p["email"], "old@x.com")         # CV didn't touch it
        self.assertEqual([r["job_title"] for r in
                          self.store.section_rows("Experience", "Me")], ["A", "B"])
        self.assertEqual(self.store.section_rows("Education", "Me"), [])  # not chosen
        self.assertEqual(added, 2)

    def test_declining_changes_nothing(self):
        added = self.d._apply_import(
            self.store, {"given_name": "New"}, {"Experience": [{"job_title": "A"}]},
            take_personal=False, take_sections=set())
        self.assertEqual(self.store.get_active()["given_name"], "Old")
        self.assertEqual(len(self.store.section_rows("Experience", "Me")), 2)
        self.assertEqual(added, 0)


class TestSectionTypes(unittest.TestCase):
    """Section types decide an entry's fields; pure, no wx."""

    def setUp(self):
        import os, sys, tempfile
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                        "addon", "globalPlugins", "jobFormFiller"))
        from core import profile
        self.p = profile
        self.store = profile.ProfileStore(
            os.path.join(tempfile.mkdtemp(), "p.dat"), profile.NullCrypto())
        self.store.load()
        self.store.add_profile("Me", {})
        self.store.set_active("Me")

    def test_explicit_and_inferred_types(self):
        self.store.add_section("My jobs", "Work")
        self.store.add_section("Education")               # inferred
        self.store.add_row("Experience", {"job_title": "x"})  # auto-created
        self.assertEqual(self.store.section_type("My jobs"), "Work")
        self.assertEqual(self.store.section_type("Education"), "Education")
        self.assertEqual(self.store.section_type("Experience"), "Work")
        self.assertEqual(self.p.infer_section_type("Certifications"), "Certification")
        self.assertEqual(self.p.infer_section_type("Publications"), "Other")

    def test_fields_for_type(self):
        self.assertIn("job_title", self.p.fields_for_type("Work"))
        self.assertIn("qualification", self.p.fields_for_type("Education"))
        self.assertEqual(self.p.fields_for_type("Other"),
                         ["title", "detail", "start_date", "end_date"])
        # a row's own keys are preserved on top of the type
        self.assertIn("custom", self.p.fields_for_type("Skills", {"custom": "v"}))


class TestAuditPass4Dialogs(unittest.TestCase):
    """Audit pass 4: impossible dates are rejected; month abbreviations match
    only at a word start. Skipped where wx is absent (sandbox); runs in CI."""

    def setUp(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                        "addon", "globalPlugins", "jobFormFiller"))
        try:
            import dialogs
            self.d = dialogs
        except Exception:
            self.skipTest("wx not available")

    def test_impossible_date_is_empty(self):
        years = ["Year", "2000", "1999"]
        self.assertEqual(self.d._dob_iso(31, 2, 1, years), "")     # 31 Feb
        self.assertEqual(self.d._dob_iso(29, 2, 1, years), "2000-02-29")  # leap
        self.assertEqual(self.d._dob_iso(29, 2, 2, years), "")     # 1999 not leap

    def test_month_abbrev_at_word_start_only(self):
        self.assertEqual(self.d._parse_monthyear("Summary 2020"), (False, 0, 2020))
        self.assertEqual(self.d._parse_monthyear("Mar 2020"), (False, 3, 2020))
