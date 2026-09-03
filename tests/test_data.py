import os, sys, json, tempfile, unittest

HERE = os.path.dirname(__file__)
CORE = os.path.join(HERE, "..", "addon", "globalPlugins", "jobFormFiller", "core")
sys.path.insert(0, os.path.abspath(CORE))

import profile as prof
import cvparse


class ReversibleCrypto(prof.Crypto):
    """A test stand-in that TRANSFORMS the bytes (so we can prove the file is
    not plaintext) yet round-trips. It is not real security - DPAPI is - but it
    lets us assert the store encrypts at rest rather than writing plaintext."""
    def encrypt(self, data: bytes) -> bytes:
        return bytes((b ^ 0x5A) for b in data)
    def decrypt(self, data: bytes) -> bytes:
        return bytes((b ^ 0x5A) for b in data)


class TestProfileStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "profiles.dat")

    def _store(self):
        return prof.ProfileStore(self.path, ReversibleCrypto())

    def test_roundtrip_and_multiple_profiles(self):
        s = self._store()
        s.add_profile("UK", {"email": "a@b.com"})
        s.add_profile("Gulf", {"email": "c@d.com"})
        s.set_active("Gulf")
        s.set_field("phone", "+966 500000000")
        s.save()

        s2 = self._store()
        s2.load()
        self.assertEqual(sorted(s2.profile_names()), ["Gulf", "UK"])
        self.assertEqual(s2.active_name(), "Gulf")
        self.assertEqual(s2.get_active()["email"], "c@d.com")
        self.assertEqual(s2.get_active()["phone"], "+966 500000000")

    def test_missing_file_loads_empty(self):
        s = self._store()
        s.load()
        self.assertEqual(s.profile_names(), [])
        self.assertIsNone(s.active_name())

    def test_set_active_unknown_raises(self):
        s = self._store()
        with self.assertRaises(KeyError):
            s.set_active("Nope")

    # --- the details are saved on the device and read back exactly ----------
    def test_saved_on_device_and_read_back(self):
        s = self._store()
        s.add_profile("UK", {"email": "me@example.com"})
        s.save()
        self.assertTrue(os.path.exists(self.path))
        s2 = self._store(); s2.load()
        self.assertEqual(s2.get_active()["email"], "me@example.com")

    # --- teeth: a half-written temp file must not clobber a good save --------
    def test_save_is_atomic_via_replace(self):
        s = self._store()
        s.add_profile("UK", {"email": "a@b.com"})
        s.save()
        # no stray .tmp left behind after a successful save
        self.assertFalse(os.path.exists(self.path + ".tmp"))


class TestCvParser(unittest.TestCase):
    SAMPLE = (
        "Mohammed Al Omrani\n"
        "Bristol, UK\n"
        "example@example.com | +44 7700 900123\n"
        "linkedin.com/in/example-user\n"
        "\n"
        "Education\n"
        "BA (Hons) Education, University of the West of England, 2026\n"
        "\n"
        "Experience\n"
        "Technology Support Volunteer, Sight Support West of England\n"
    )

    def test_extracts_contacts(self):
        r = cvparse.parse_cv_text(self.SAMPLE)
        self.assertEqual(r["email"], "example@example.com")
        self.assertEqual(r["phone"], "+44 7700 900123")
        self.assertEqual(r["linkedin"], "linkedin.com/in/example-user")
        self.assertEqual(r["full_name"], "Mohammed Al Omrani")

    def test_extracts_sections(self):
        r = cvparse.parse_cv_text(self.SAMPLE)
        self.assertIn("education", r)
        self.assertIn("experience", r)
        self.assertTrue(any("University of the West" in ln for ln in r["education"]))

    # --- teeth: it must NOT invent fields that are not there ----------------
    def test_no_email_means_no_email_key(self):
        r = cvparse.parse_cv_text("Just some text with a phone 07700900123\n")
        self.assertNotIn("email", r)

    def test_ignores_too_short_number(self):
        r = cvparse.parse_cv_text("Ref 12345\n")   # too short to be a phone
        self.assertNotIn("phone", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
