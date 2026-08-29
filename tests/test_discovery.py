"""Discovery must capture custom widgets the fingerprint database does not cover,
skip native inputs and already-covered fields, and suggest a stable stub. Pure."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "addon", "globalPlugins", "jobFormFiller"))
from core import discovery  # noqa: E402


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.fields = [
            {"id": "first_name", "role": "editabletext",
             "class": "input input__single-line", "states": ("editable",),
             "label": "First name"},
            {"id": "source--source", "role": "editabletext",
             "placeholder": "Search", "class": "css-1a2b3c",
             "states": ("collapsed",), "label": "How did you hear"},
            {"id": "country", "role": "combobox", "class": "select__input",
             "haspopup": "menu", "states": ("collapsed",), "label": "Country"},
        ]

    def test_native_input_not_captured(self):
        recs = discovery.build_records(self.fields, "workday", lambda s: False)
        self.assertFalse(any(r["label"] == "First name" for r in recs))

    def test_covered_field_not_captured(self):
        # country is "already covered" -> excluded
        recs = discovery.build_records(
            self.fields, "greenhouse", lambda s: s.get("id") == "country")
        self.assertFalse(any(r["label"] == "Country" for r in recs))

    def test_unknown_custom_widget_captured_with_stub(self):
        recs = discovery.build_records(self.fields, "workday",
                                       lambda s: s.get("id") == "country")
        got = [r for r in recs if r["label"] == "How did you hear"]
        self.assertEqual(len(got), 1)
        when = got[0]["suggested_fingerprint"]["when"]
        self.assertEqual(when.get("platform"), "workday")
        self.assertEqual(when.get("id_contains"), "source--source")
        self.assertEqual(got[0]["suggested_fingerprint"]["kind"], "REVIEW")

    def test_hashed_class_not_used_as_signal(self):
        f = [{"id": "", "role": "combobox", "class": "css-1a2b3c",
              "haspopup": "listbox", "label": "x"}]
        recs = discovery.build_records(f, "", lambda s: False)
        self.assertEqual(len(recs), 1)
        self.assertNotIn("class_contains", recs[0]["suggested_fingerprint"]["when"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
