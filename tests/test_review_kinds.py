"""The review editor makes an inaccessible control accessible in its own idiom.
These lock the pure mapping from a classified control to the accessible editor
the review dialog offers, so a combobox stays a chooser and never silently
flattens into a text box. Option reading and group dedup need real NVDA objects
and are covered by the real-NVDA review test; here we prove the mapping."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "addon", "globalPlugins", "jobFormFiller"))

from core import controls  # noqa: E402


class EditorKindMapping(unittest.TestCase):
    def test_checkbox_is_yes_no(self):
        self.assertEqual(controls.editor_kind(controls.CHECKBOX),
                         controls.EDITOR_YESNO)

    def test_choosers_are_single(self):
        for k in (controls.RADIO, controls.NATIVE_SELECT, controls.ARIA_COMBOBOX):
            self.assertEqual(controls.editor_kind(k), controls.EDITOR_SINGLE,
                             "%s should offer an accessible chooser" % k)

    def test_editable_combobox_stays_editable(self):
        self.assertEqual(controls.editor_kind(controls.EDITABLE_COMBOBOX),
                         controls.EDITOR_EDITABLE)

    def test_multiselect_is_multi(self):
        self.assertEqual(controls.editor_kind(controls.MULTISELECT),
                         controls.EDITOR_MULTI)

    def test_async_is_a_typed_box(self):
        # Its options load over the network and NVDA reports them empty to us,
        # so we cannot mirror them: type and hand back to the live list.
        self.assertEqual(controls.editor_kind(controls.ASYNC_COMBOBOX),
                         controls.EDITOR_TEXT)

    def test_plain_text_is_a_typed_box(self):
        self.assertEqual(controls.editor_kind(controls.TEXT),
                         controls.EDITOR_TEXT)

    def test_datepicker_is_three_dropdowns(self):
        self.assertEqual(controls.editor_kind(controls.DATEPICKER),
                         controls.EDITOR_DATE)

    def test_date_wins_by_key_even_on_a_text_field(self):
        # A date of birth typed into a plain text field is still a date.
        self.assertEqual(
            controls.editor_kind(controls.TEXT, key="date_of_birth"),
            controls.EDITOR_DATE)

    def test_date_wins_by_input_type(self):
        self.assertEqual(
            controls.editor_kind(controls.TEXT, input_type="date"),
            controls.EDITOR_DATE)

    def test_date_precedence_over_checkbox_shape(self):
        # Ordering guard: date is checked before any other kind.
        self.assertEqual(
            controls.editor_kind(controls.CHECKBOX, key="date_of_birth"),
            controls.EDITOR_DATE)


if __name__ == "__main__":
    unittest.main()
