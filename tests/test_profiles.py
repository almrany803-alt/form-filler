"""The foundation for 'several profiles, each a version': multiple named
profiles coexist, the active one selects which details are used, and everything
round-trips through save and load."""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
CORE = os.path.join(HERE, "..", "addon", "globalPlugins", "jobFormFiller", "core")
sys.path.insert(0, os.path.abspath(CORE))

import profile  # noqa: E402


class TestMultiProfile(unittest.TestCase):
    def _store(self):
        path = os.path.join(tempfile.mkdtemp(), "p.dat")
        return profile.ProfileStore(path, profile.NullCrypto())

    def test_two_versions_coexist_and_switch(self):
        s = self._store()
        s.add_profile("English", {"given_name": "John", "email": "john@x.com"})
        s.add_profile("Arabic", {"given_name": "محمد", "email": "m@x.com"})
        self.assertEqual(set(s.profile_names()), {"English", "Arabic"})
        # first added becomes active
        self.assertEqual(s.active_name(), "English")
        self.assertEqual(s.get_active()["given_name"], "John")
        s.set_active("Arabic")
        self.assertEqual(s.get_active()["given_name"], "محمد")
        # each keeps its own fields
        self.assertEqual(s.get_profile("English")["given_name"], "John")
        self.assertEqual(s.get_profile("Arabic")["given_name"], "محمد")

    def test_round_trips_both_versions(self):
        s = self._store()
        s.add_profile("English", {"given_name": "John"})
        s.add_profile("Arabic", {"given_name": "محمد"})
        s.set_active("Arabic")
        s.save()
        # reload from disk into a fresh store
        s2 = profile.ProfileStore(s._path if hasattr(s, "_path") else s.path,
                                  profile.NullCrypto())
        s2.load()
        self.assertEqual(set(s2.profile_names()), {"English", "Arabic"})
        self.assertEqual(s2.active_name(), "Arabic")
        self.assertEqual(s2.get_profile("English")["given_name"], "John")
        self.assertEqual(s2.get_profile("Arabic")["given_name"], "محمد")

    def test_edit_one_leaves_the_other(self):
        s = self._store()
        s.add_profile("English", {"given_name": "John"})
        s.add_profile("Arabic", {"given_name": "محمد"})
        s.set_field("given_name", "Jonathan", profile="English")
        self.assertEqual(s.get_profile("English")["given_name"], "Jonathan")
        self.assertEqual(s.get_profile("Arabic")["given_name"], "محمد")

    def test_rename_keeps_active(self):
        s = self._store()
        s.add_profile("English", {"given_name": "John"})
        s.set_active("English")
        s.rename_profile("English", "English (engineering)")
        self.assertIn("English (engineering)", s.profile_names())
        self.assertNotIn("English", s.profile_names())
        self.assertEqual(s.active_name(), "English (engineering)")


    def test_delete_repoints_active(self):
        s = self._store()
        s.add_profile("English", {"given_name": "John"})
        s.add_profile("Arabic", {"given_name": "محمد"})
        s.set_active("English")
        s.delete_profile("English")
        self.assertNotIn("English", s.profile_names())
        self.assertEqual(s.active_name(), "Arabic")
        s.delete_profile("Arabic")
        self.assertEqual(s.profile_names(), [])
        self.assertIsNone(s.active_name())


if __name__ == "__main__":
    unittest.main(verbosity=2)
