import os, sys, unittest

HERE = os.path.dirname(__file__)
CORE = os.path.join(HERE, "..", "addon", "globalPlugins", "jobFormFiller", "core")
sys.path.insert(0, os.path.abspath(CORE))

import audit
import announce


def exp(company, title, start="", end=""):
    return {"company": company, "title": title, "start": start, "end": end}


class TestAudit(unittest.TestCase):

    def test_clean_form_is_ok(self):
        cv = {"experience": [exp("ACME", "Developer")],
              "education": [{"institution": "UWE"}]}
        form = {"experience": [exp("ACME", "Developer")],
                "education": [{"institution": "UWE"}]}
        r = audit.audit_form(form, cv)
        self.assertTrue(r.ok)
        self.assertEqual(announce.audit_summary(r),
                         "Form check: all good. Nothing duplicated or added.")

    def test_detects_duplicate(self):
        cv = {"experience": [exp("ACME", "Developer")]}
        form = {"experience": [exp("ACME", "Developer"), exp("ACME", "Developer")]}
        r = audit.audit_form(form, cv)
        kinds = [a.kind for a in r.anomalies]
        self.assertIn("duplicate", kinds)
        # the duplicate explains the surplus, so no separate extra_count
        self.assertNotIn("extra_count", kinds)

    def test_detects_empty_row(self):
        cv = {"education": [{"institution": "UWE"}]}
        form = {"education": [{"institution": "UWE"}, {"institution": "", "degree": ""}]}
        r = audit.audit_form(form, cv)
        self.assertIn("empty", [a.kind for a in r.anomalies])

    def test_detects_extra_distinct_entry(self):
        cv = {"experience": [exp("ACME", "Developer")]}
        form = {"experience": [exp("ACME", "Developer"), exp("Globex", "Analyst")]}
        r = audit.audit_form(form, cv)
        self.assertIn("extra_count", [a.kind for a in r.anomalies])

    def test_detects_half_filled(self):
        cv = {"experience": [exp("ACME", "Developer")]}
        form = {"experience": [exp("", "Developer")]}     # title but no company
        r = audit.audit_form(form, cv)
        self.assertIn("half_filled", [a.kind for a in r.anomalies])

    def test_detects_contact_mismatch(self):
        cv = {"contact": {"city": "Bristol"}}
        form = {"contact": {"city": "United Kingdom"}}
        r = audit.audit_form(form, cv)
        self.assertIn("mismatch", [a.kind for a in r.anomalies])

    # --- teeth: must NOT flag a genuine second, different job as a duplicate --
    def test_similar_but_different_is_not_duplicate(self):
        cv = {"experience": [exp("ACME", "Developer"), exp("ACME", "Senior Developer")]}
        form = {"experience": [exp("ACME", "Developer"), exp("ACME", "Senior Developer")]}
        r = audit.audit_form(form, cv)
        self.assertNotIn("duplicate", [a.kind for a in r.anomalies])
        self.assertTrue(r.ok)

    # --- teeth: MUST catch a duplicate hidden by whitespace/case -------------
    def test_whitespace_case_duplicate_is_caught(self):
        cv = {"experience": [exp("ACME", "Developer")]}
        form = {"experience": [exp("ACME", "Developer"), exp("  acme ", "DEVELOPER")]}
        r = audit.audit_form(form, cv)
        self.assertIn("duplicate", [a.kind for a in r.anomalies])

    def test_spoken_summary_is_exact(self):
        cv = {"contact": {"city": "Bristol"},
              "experience": [exp("ACME", "Developer")]}
        form = {"contact": {"city": "United Kingdom"},
                "experience": [exp("ACME", "Developer"), exp("ACME", "Developer")]}
        r = audit.audit_form(form, cv)
        self.assertEqual(
            announce.audit_summary(r),
            "Form check: 2 things to look at. "
            "Two identical work entries: ACME. "
            "The form has your city as United Kingdom, your CV says Bristol.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
