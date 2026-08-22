"""CV import mapping, tested the way it will be used: real-shaped CVs in several
languages, parsed and mapped to the My-details fields. Names are modelled on CV
structures, not real people."""
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
CORE = os.path.join(HERE, "..", "addon", "globalPlugins", "jobFormFiller", "core")
sys.path.insert(0, os.path.abspath(CORE))

import cvparse  # noqa: E402


EN_CV = """John Smith
john.smith@example.com
+44 7700 900123
linkedin.com/in/johnsmith

EXPERIENCE
Software Engineer, Acme Ltd

EDUCATION
BSc Computing, University of Bristol
"""

AR_CV = """محمد العمراني
mohammed.alomrani@example.com
+966 50 123 4567

الخبرة
مهندس برمجيات

التعليم
بكالوريوس علوم حاسب
"""

ES_CV = """María García López
maria.garcia@example.com
+34 600 123 456

EXPERIENCIA
Ingeniera de software
"""

PL_CV = """Paweł Kowalski
pawel.kowalski@example.com
+48 512 345 678

DOŚWIADCZENIE
Programista
"""


class TestCvImportMapping(unittest.TestCase):
    def _fields(self, text):
        return cvparse.cv_to_fields(cvparse.parse_cv_text(text))

    def test_english(self):
        f = self._fields(EN_CV)
        self.assertEqual(f["given_name"], "John")
        self.assertEqual(f["family_name"], "Smith")
        self.assertEqual(f["email"], "john.smith@example.com")
        self.assertTrue(f["phone"].replace(" ", "").endswith("900123"))
        self.assertIn("linkedin.com/in/johnsmith", f["linkedin"])

    def test_arabic(self):
        f = self._fields(AR_CV)
        self.assertEqual(f["given_name"], "محمد")
        self.assertEqual(f["family_name"], "العمراني")
        self.assertEqual(f["email"], "mohammed.alomrani@example.com")

    def test_spanish_multipart_surname(self):
        f = self._fields(ES_CV)
        self.assertEqual(f["given_name"], "María")
        self.assertEqual(f["family_name"], "García López")  # two-part surname kept

    def test_polish_diacritics(self):
        f = self._fields(PL_CV)
        self.assertEqual(f["given_name"], "Paweł")
        self.assertEqual(f["family_name"], "Kowalski")

    def test_empty_and_junk_do_not_crash(self):
        for t in ("", "   ", "no structure here at all", "@@@@\n\n\n"):
            self.assertIsInstance(cvparse.cv_to_fields(cvparse.parse_cv_text(t)), dict)

    def test_single_name_only_given(self):
        f = cvparse.cv_to_fields({"full_name": "Cher"})
        self.assertEqual(f["given_name"], "Cher")
        self.assertNotIn("family_name", f)


if __name__ == "__main__":
    unittest.main(verbosity=2)
