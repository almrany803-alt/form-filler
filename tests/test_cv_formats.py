"""Word and PDF import, tested on real fixture files across languages, using the
stdlib .docx reader and the bundled pure-Python pypdf (the same code paths the
add-on uses on the user's machine)."""
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
CORE = os.path.join(HERE, "..", "addon", "globalPlugins", "jobFormFiller", "core")
CVS = os.path.join(HERE, "..", "betatest", "cvs")
sys.path.insert(0, os.path.abspath(CORE))

import cvparse  # noqa: E402


class TestCvFormats(unittest.TestCase):
    def _fields(self, filename):
        text = cvparse.extract_text(os.path.join(CVS, filename))
        return cvparse.cv_to_fields(cvparse.parse_cv_text(text))

    def test_word_english(self):
        f = self._fields("cv_en.docx")
        self.assertEqual(f["given_name"], "Jane")
        self.assertEqual(f["family_name"], "Doe")
        self.assertEqual(f["email"], "jane.doe@example.co.uk")

    def test_word_arabic(self):
        f = self._fields("cv_ar.docx")
        self.assertEqual(f["given_name"], "سارة")
        self.assertEqual(f["family_name"], "الأحمد")
        self.assertEqual(f["email"], "sara.alahmad@example.com")

    def test_pdf_english(self):
        f = self._fields("cv_en.pdf")
        self.assertEqual(f["given_name"], "Michael")
        self.assertEqual(f["family_name"], "Brown")
        self.assertEqual(f["email"], "michael.brown@example.com")

    def test_pdf_spanish(self):
        f = self._fields("cv_es.pdf")
        self.assertEqual(f["given_name"], "Maria")
        self.assertEqual(f["family_name"], "Garcia Lopez")

    def test_unsupported_format_raises_cleanly(self):
        with self.assertRaises(Exception):
            cvparse.extract_text("resume.rtf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
