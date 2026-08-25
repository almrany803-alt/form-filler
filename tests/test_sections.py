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
