"""Adversarial tests: behave like an impatient, chaotic user and a hostile
network. Throw junk at every pure-Python module and assert it degrades
gracefully (no exceptions, sensible output) instead of crashing."""
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
CORE = os.path.join(HERE, "..", "addon", "globalPlugins", "jobFormFiller", "core")
sys.path.insert(0, os.path.abspath(CORE))

import matcher
import controls
import audit
import announce
import cvparse
import profile


JUNK = [
    "", " ", "\t\n\r", "\x00\x01\x02", "a" * 10000,
    "😀🔥🚀" * 50, "\u202eevil rtl override", "'; DROP TABLE users; --",
    "<script>alert(1)</script>", "名前 이메일 البريد", "\\x41\\x42",
    "%s%s%s%n", "../../etc/passwd", "NaN", "None", "－－－",
]


class TestMatcherAbuse(unittest.TestCase):
    def test_match_never_raises_on_junk(self):
        for j in JUNK:
            for field in ("label", "name", "id", "placeholder", "autocomplete", "aria_label"):
                fd = matcher.FieldDescriptor(**{field: j})
                r = matcher.match_field(fd)          # must not raise
                self.assertIn(r.confidence, ("strong", "guess", "none"))
                if r.key is not None:
                    self.assertIn(r.key, matcher.PROFILE_KEYS)

    def test_all_junk_in_every_slot_at_once(self):
        for j in JUNK:
            fd = matcher.FieldDescriptor(role=j, label=j, aria_label=j, name=j,
                                         id=j, placeholder=j, autocomplete=j)
            matcher.match_field(fd)                  # must not raise

    def test_weird_folding_is_stable(self):
        for j in JUNK:
            a = matcher._norm(j)
            b = matcher._norm(j)
            self.assertEqual(a, b)                   # deterministic, no crash


class TestControlsAbuse(unittest.TestCase):
    def test_classify_never_raises(self):
        weird_roles = JUNK + ["combobox", "COMBOBOX", "edit", None if False else ""]
        weird_states = [(), ("editable",), ("junk", "more"), tuple(JUNK)]
        for role in weird_roles:
            for states in weird_states:
                cd = controls.ControlDescriptor(role=role, states=states)
                controls.classify_control(cd)        # must not raise


class TestAuditAbuse(unittest.TestCase):
    def test_audit_survives_malformed_forms(self):
        forms = [
            {}, {"experience": []}, {"experience": [{}]},
            {"experience": [{"company": None, "title": None}]},
            {"experience": [{"x": 123}]},            # non-string values
            {"contact": {"city": ""}},
            {"experience": [{"company": "A"}] * 500}, # many duplicates
            {"education": None},                      # wrong type
        ]
        cvs = [{}, {"experience": []}, {"experience": [{"company": "A", "title": "B"}]}]
        for f in forms:
            for c in cvs:
                try:
                    rep = audit.audit_form(f, c)
                    announce.audit_summary(rep)      # summary must not raise
                except (TypeError, AttributeError):
                    # a wrong-typed section is allowed to be rejected, but must
                    # be rejected cleanly, not with some deeper explosion
                    pass


class TestCvParseAbuse(unittest.TestCase):
    def test_parse_cv_text_survives_garbage(self):
        for j in JUNK + ["\n".join(JUNK), "EDUCATION\n" * 1000]:
            r = cvparse.parse_cv_text(j)             # must not raise
            self.assertIsInstance(r, dict)

    def test_extract_text_missing_file(self):
        with self.assertRaises(Exception):
            cvparse.extract_text("/no/such/file.docx")   # clean failure, not a hang


class TestProfileAbuse(unittest.TestCase):
    def _store(self):
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "p.dat")
        return profile.ProfileStore(path, profile.NullCrypto())

    def test_store_survives_junk_values(self):
        s = self._store()
        s.add_profile("default", {k: j for k, j in
                                  zip(matcher.PROFILE_KEYS, JUNK)})
        s.save()
        s.load()                                     # round-trip must survive

    def test_load_corrupted_file(self):
        s = self._store()
        with open(s.path if hasattr(s, "path") else s._path, "wb") as f:
            f.write(b"\x00\xff not json at all \x00")
        try:
            s.load()                                 # corrupted -> clean handling
        except Exception:
            pass                                     # acceptable, must not hang


class TestAnnounceAbuse(unittest.TestCase):
    def test_summaries_survive_extremes(self):
        announce.build_summary([], [], [])
        announce.build_summary(["email"] * 1000, [], [])
        announce.build_summary([], [], JUNK)
        announce.build_summary(list(matcher.PROFILE_KEYS), list(matcher.PROFILE_KEYS), JUNK)


if __name__ == "__main__":
    unittest.main(verbosity=2)
