import os
import sys
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import profile  # noqa: E402


def _store():
    tmp = tempfile.mkdtemp()
    s = profile.ProfileStore(os.path.join(tmp, "p.dat"), profile.NullCrypto())
    s.load()
    s.add_profile("UK", {"given_name": "Mohammed", "email": "a@b.com"})
    return s


class TestSections(unittest.TestCase):
    def test_add_remove_rename_sections(self):
        s = _store()
        s.add_section("Experience")
        s.add_section("Education")
        s.add_section("Experience")          # duplicate -> no-op
        self.assertEqual(s.section_names(), ["Experience", "Education"])
        s.rename_section("Education", "Studies")
        self.assertEqual(s.section_names(), ["Experience", "Studies"])
        s.remove_section("Studies")
        self.assertEqual(s.section_names(), ["Experience"])

    def test_rows_crud_and_autocreate(self):
        s = _store()
        s.add_row("Experience", {"job_title": "Engineer"})
        s.add_row("Experience", {"job_title": "Teacher"})
        self.assertEqual(len(s.section_rows("Experience")), 2)
        s.update_row("Experience", 0, {"job_title": "Senior Engineer"})
        self.assertEqual(s.section_rows("Experience")[0]["job_title"],
                         "Senior Engineer")
        s.remove_row("Experience", 1)
        self.assertEqual(len(s.section_rows("Experience")), 1)
        s.add_row("Certifications", {"name": "AWS"})   # creates section
        self.assertIn("Certifications", s.section_names())

    def test_sections_are_separate_from_flat_fields(self):
        s = _store()
        s.add_section("Experience")
        self.assertEqual(s.get_active(),
                         {"given_name": "Mohammed", "email": "a@b.com"})

    def test_persistence_and_profile_rename_delete(self):
        s = _store()
        s.add_row("Experience", {"job_title": "Engineer"})
        s.save()
        s2 = profile.ProfileStore(s.path, profile.NullCrypto())
        s2.load()
        self.assertEqual(s2.section_names("UK"), ["Experience"])
        s2.rename_profile("UK", "Britain")
        self.assertEqual(s2.section_names("Britain"), ["Experience"])
        s2.delete_profile("Britain")
        self.assertEqual(s2.section_names("Britain"), [])

    def test_old_file_without_sections_key_loads(self):
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "old.dat")
        open(p, "wb").write(json.dumps(
            {"active": "X", "profiles": {"X": {"email": "z@z"}}}).encode())
        s = profile.ProfileStore(p, profile.NullCrypto())
        s.load()
        self.assertEqual(s.section_names("X"), [])
        s.add_section("Skills", "X")
        self.assertEqual(s.section_names("X"), ["Skills"])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestSectionHelpers(unittest.TestCase):
    def test_fields_for_section(self):
        self.assertEqual(profile.fields_for_section("Skills"), ["skill"])
        self.assertEqual(
            profile.fields_for_section("Experience"),
            ["job_title", "employer", "start_date", "end_date", "description"])
        # unknown empty section -> generic default so it is still fillable
        self.assertEqual(profile.fields_for_section("Publications"),
                         ["title", "detail", "start_date", "end_date"])
        # unknown section with a row -> that row's fields
        self.assertEqual(
            profile.fields_for_section("Volunteering", {"role": "M", "org": "L"}),
            ["role", "org"])
        # known section plus a custom field on the row -> template then the extra
        self.assertEqual(
            profile.fields_for_section("Experience", {"job_title": "X",
                                                      "reference": "Y"}),
            ["job_title", "employer", "start_date", "end_date", "description",
             "reference"])


class TestEntrySummary(unittest.TestCase):
    def test_summary_lines(self):
        from core import announce
        self.assertEqual(
            announce.entry_summary({"job_title": "Peer Mentor",
                                    "employer": "Look UK",
                                    "start_date": "Sep 2023", "end_date": ""}),
            "Peer Mentor, Look UK, Sep 2023 to present")
        self.assertEqual(
            announce.entry_summary({"skill": "Accessible Learning Design"}),
            "Accessible Learning Design")
        self.assertEqual(
            announce.entry_summary({"language": "Arabic",
                                    "proficiency": "Native"}),
            "Arabic, Native")
        self.assertEqual(announce.entry_summary({}), "(empty entry)")
        self.assertEqual(announce.entry_summary({"custom": "v"}), "v")
