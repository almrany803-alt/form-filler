import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                "addon", "globalPlugins", "jobFormFiller", "core"))
import controls  # noqa: E402


class UI5DateRecognition(unittest.TestCase):
    """SAP UI5 / SuccessFactors renders its date field as a plain text input;
    the only date signals are aria-roledescription 'Date Input' and a format
    placeholder. The add-on must still recognise it as a date (STC Birth Date)."""

    def _cd(self, **kw):
        return controls.ControlDescriptor(role="textbox", **kw)

    def test_roledescription_date_input(self):
        cd = self._cd(placeholder="MM/DD/YYYY", roledescription="Date Input")
        self.assertEqual(controls.classify_control(cd), controls.DATEPICKER)

    def test_placeholder_alone_is_enough(self):
        cd = self._cd(placeholder="DD/MM/YYYY")
        self.assertEqual(controls.classify_control(cd), controls.DATEPICKER)

    def test_locale_placeholders(self):
        for ph in ("MM/DD/YYYY", "DD/MM/YYYY", "JJ/MM/AAAA",
                   "TT.MM.JJJJ", "YYYY-MM-DD", "DD-MM-YYYY"):
            cd = self._cd(placeholder=ph)
            self.assertEqual(controls.classify_control(cd),
                             controls.DATEPICKER, ph)

    def test_plain_text_is_not_a_date(self):
        for ph in ("Enter your city", "you@example.com", "Full name",
                   "Search", "+44 7700 900000", ""):
            cd = self._cd(placeholder=ph)
            self.assertNotEqual(controls.classify_control(cd),
                                controls.DATEPICKER, ph)
