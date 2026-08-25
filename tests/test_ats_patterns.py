"""Field identification against the real field patterns the major ATS use:
Greenhouse (bracketed names + autocomplete), Workday (generic ids, identity in
aria-label), Taleo/iCIMS (camelCase names, often no label). CamelCase names were
mislabelled as full_name until the normaliser learned to split them."""
import os
import sys
import unittest

CORE = os.path.join(os.path.dirname(__file__), "..", "addon",
                    "globalPlugins", "jobFormFiller", "core")
sys.path.insert(0, os.path.abspath(CORE))

import matcher  # noqa: E402
FD = matcher.FieldDescriptor


class TestAtsPatterns(unittest.TestCase):
    def k(self, **kw):
        return matcher.match_field(FD(**kw)).key

    def test_greenhouse_label_plus_autocomplete(self):
        self.assertEqual(self.k(label="First Name",
                                name="job_application[first_name]",
                                autocomplete="given-name"), "given_name")
        self.assertEqual(self.k(label="Email",
                                name="job_application[email]"), "email")
        self.assertEqual(self.k(label="Phone",
                                name="job_application[phone]"), "phone")

    def test_workday_identity_in_aria_label_only(self):
        self.assertEqual(self.k(aria_label="First Name", name="input-15"),
                         "given_name")
        self.assertEqual(self.k(aria_label="City", name="input-42"), "city")
        self.assertEqual(self.k(aria_label="Country", name="input-7",
                                role="combobox"), "country")

    def test_taleo_icims_camelcase_names(self):
        self.assertEqual(self.k(name="firstName"), "given_name")
        self.assertEqual(self.k(name="lastName"), "family_name")
        self.assertEqual(self.k(name="givenName"), "given_name")
        self.assertEqual(self.k(name="familyName"), "family_name")
        self.assertEqual(self.k(name="phoneNumber"), "phone")
        self.assertEqual(self.k(name="emailAddress"), "email")

    def test_snake_and_bracket_names(self):
        self.assertEqual(self.k(name="first_name"), "given_name")
        self.assertEqual(self.k(name="job_application[last_name]"),
                         "family_name")

    def test_localised_labels_on_ats_fields(self):
        self.assertEqual(self.k(label="Nombre",
                                name="job_application[first_name]"),
                         "given_name")
        self.assertEqual(self.k(label="Vorname", name="input-3"), "given_name")
        self.assertEqual(self.k(label="البريد الإلكتروني"), "email")

    def test_name_slots_do_not_grab_full_name(self):
        # Father's-name and preferred-name fields must NOT match "full_name" off
        # the bare word "name"; they resolve to their own concepts, which hold no
        # profile value and so fall to "needs you" instead of the full name.
        self.assertEqual(self.k(label="Arabic Father's Name"), "father_name")
        self.assertEqual(self.k(label="Father's Name - Latin Script"),
                         "father_name")
        self.assertEqual(self.k(label="Middle Name"), "father_name")
        self.assertEqual(self.k(label="I have a preferred name"),
                         "preferred_name")
        self.assertNotIn("father_name", matcher.PROFILE_KEYS)
        self.assertNotIn("preferred_name", matcher.PROFILE_KEYS)
        # the correctly-filling name fields are unchanged
        self.assertEqual(self.k(label="Arabic Given Name(s)"), "given_name")
        self.assertEqual(self.k(label="Arabic Family Name"), "family_name")
        self.assertEqual(self.k(label="Full Name"), "full_name")

    def test_phone_code_and_extension_do_not_grab_country_or_phone(self):
        # A dial-code field must NOT match "country" (it was filling "Saudi
        # Arabia" on a live form and breaking the save), and an extension must NOT
        # match "phone". Both resolve to their own concepts with no stored value,
        # so they fall to "needs you".
        self.assertEqual(self.k(label="Country Code"), "phone_country_code")
        self.assertEqual(self.k(label="Country / Territory Phone Code"),
                         "phone_country_code")
        self.assertEqual(self.k(label="Phone Extension"), "phone_extension")
        self.assertNotIn("phone_country_code", matcher.PROFILE_KEYS)
        self.assertNotIn("phone_extension", matcher.PROFILE_KEYS)
        # the real country and phone fields still fill correctly
        self.assertEqual(self.k(label="Country"), "country")
        self.assertEqual(self.k(label="Country of Residence"), "country")
        self.assertEqual(self.k(label="Phone Number"), "phone")


if __name__ == "__main__":
    unittest.main(verbosity=2)
