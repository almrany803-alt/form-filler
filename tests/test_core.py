import os, sys, unittest

# Make the core modules and the fixtures importable by bare name.
HERE = os.path.dirname(__file__)
CORE = os.path.join(HERE, "..", "addon", "globalPlugins", "jobFormFiller", "core")
sys.path.insert(0, os.path.abspath(CORE))
sys.path.insert(0, os.path.abspath(HERE))

from matcher import FieldDescriptor as F, match_field
import controls
import announce
import fixtures


class TestMatcherMultilingual(unittest.TestCase):
    def m(self, **kw):
        return match_field(F(**kw))

    def test_english_email(self):
        r = self.m(label="Email address")
        self.assertEqual((r.key, r.confidence), ("email", "strong"))

    def test_french_email(self):
        r = self.m(label="Adresse e-mail")
        self.assertEqual(r.key, "email"); self.assertEqual(r.lang, "fr")

    def test_german_phone(self):
        self.assertEqual(self.m(label="Telefonnummer").key, "phone")

    def test_spanish_surname(self):
        self.assertEqual(self.m(label="Apellidos").key, "family_name")

    def test_arabic_first_name(self):
        r = self.m(label="الاسم الاول")
        self.assertEqual(r.key, "given_name"); self.assertEqual(r.lang, "ar")

    def test_autocomplete_beats_foreign_label(self):
        # French label, but autocomplete declares the purpose in a neutral token.
        r = self.m(label="Pays", autocomplete="country")
        self.assertEqual((r.key, r.source), ("country", "autocomplete"))

    def test_autocomplete_without_label(self):
        self.assertEqual(self.m(autocomplete="given-name").key, "given_name")

    def test_longest_match_first_name(self):
        self.assertEqual(self.m(label="First name").key, "given_name")

    def test_longest_match_surname_not_fullname(self):
        self.assertEqual(self.m(label="Surname").key, "family_name")

    def test_plain_name_is_fullname(self):
        self.assertEqual(self.m(label="Name").key, "full_name")

    def test_placeholder_only_is_guess(self):
        r = self.m(placeholder="First name")
        self.assertEqual((r.key, r.confidence), ("given_name", "guess"))

    def test_name_attribute(self):
        r = self.m(name="user_family_name")
        self.assertEqual((r.key, r.source), ("family_name", "name"))

    # --- teeth: prove it does NOT invent a mapping when it has nothing -------
    def test_unlabelled_falls_through_not_guessed(self):
        r = self.m(id="field_9x")
        self.assertIsNone(r.key)
        self.assertEqual(r.confidence, "none")

    def test_bespoke_question_falls_through(self):
        self.assertIsNone(self.m(label="Why do you want this role?").key)


class TestClassifier(unittest.TestCase):
    def k(self, name):
        return controls.classify_control(fixtures.CHOICE_CONTROLS[name])

    def test_native_select(self):
        self.assertEqual(self.k("native_select"), controls.NATIVE_SELECT)

    def test_aria_combobox(self):
        self.assertEqual(self.k("aria_combobox"), controls.ARIA_COMBOBOX)

    def test_editable_combobox(self):
        self.assertEqual(self.k("editable_combobox"), controls.EDITABLE_COMBOBOX)

    def test_async_combobox(self):
        self.assertEqual(self.k("async_combobox"), controls.ASYNC_COMBOBOX)

    def test_multiselect(self):
        self.assertEqual(self.k("multiselect"), controls.MULTISELECT)

    def test_radio_checkbox_date_text(self):
        self.assertEqual(self.k("radio"), controls.RADIO)
        self.assertEqual(self.k("checkbox"), controls.CHECKBOX)
        self.assertEqual(self.k("datepicker"), controls.DATEPICKER)
        self.assertEqual(self.k("text"), controls.TEXT)

    def test_multiselect_hands_back(self):
        # a multi-select must plan to hand back, never blind-drive.
        self.assertEqual(controls.METHOD_PLAN[controls.MULTISELECT], ["hand_back"])


class TestChooseOption(unittest.TestCase):
    def test_exact_english(self):
        r = controls.choose_option("United Kingdom", fixtures.COUNTRY_OPTIONS_EN, "country")
        self.assertEqual((r.index, r.confidence), (2, "strong"))

    def test_french_form_english_value(self):
        r = controls.choose_option("United Kingdom", fixtures.COUNTRY_OPTIONS_FR, "country")
        self.assertEqual(r.label, "Royaume-Uni"); self.assertEqual(r.confidence, "strong")

    def test_arabic_form_english_value(self):
        r = controls.choose_option("United Kingdom", fixtures.COUNTRY_OPTIONS_AR, "country")
        self.assertEqual(r.label, "المملكة المتحدة"); self.assertEqual(r.confidence, "strong")

    def test_containment_is_guess(self):
        r = controls.choose_option("Bristol", ["Bristol, UK", "London, UK"])
        self.assertEqual(r.confidence, "guess")

    def test_no_match_none(self):
        r = controls.choose_option("Atlantis", fixtures.COUNTRY_OPTIONS_EN, "country")
        self.assertIsNone(r.index); self.assertEqual(r.confidence, "none")


class TestVerifyBack(unittest.TestCase):
    def test_confirmed(self):
        self.assertEqual(controls.verify_selection("Royaume-Uni", "Royaume-Uni"), "confirmed")

    def test_confirmed_by_containment(self):
        self.assertEqual(controls.verify_selection("UK", "United Kingdom (UK)"), "confirmed")

    # --- teeth: the classic silent failure must NOT read as success ---------
    def test_empty_readback_is_unknown_not_confirmed(self):
        self.assertEqual(controls.verify_selection("Royaume-Uni", ""), "unknown")

    def test_wrong_value_is_mismatch_not_confirmed(self):
        self.assertEqual(controls.verify_selection("Royaume-Uni", "France"), "mismatch")


class TestAnnounce(unittest.TestCase):
    def test_summary_with_leftovers(self):
        s = announce.build_summary(
            filled=["email", "phone", "given_name", "family_name", "city",
                    "postcode", "address_line1", "country", "linkedin"],
            guessed=[],
            leftovers=["work authorisation", "salary", "referee email"])
        self.assertEqual(
            s, "Filled 9 of 12. 3 need you: work authorisation, salary, referee email.")

    def test_summary_with_a_guess(self):
        s = announce.build_summary(filled=["email"], guessed=["phone"],
                                   leftovers=["salary"])
        self.assertEqual(s, "Filled 2 of 3. Check 1 guess: phone. 1 need you: salary.")

    def test_summary_nothing_left(self):
        s = announce.build_summary(filled=["email"], guessed=[], leftovers=[])
        self.assertEqual(s, "Filled 1 of 1. Nothing left for you.")

    def test_choice_set_confirmed(self):
        self.assertEqual(announce.choice_set("Country", "Royaume-Uni", "confirmed"),
                         "Country set to Royaume-Uni.")

    def test_choice_set_mismatch_hands_over(self):
        self.assertEqual(announce.choice_set("Country", "Royaume-Uni", "mismatch"),
                         "Country did not take Royaume-Uni. Over to you.")

    def test_hand_back_async(self):
        self.assertEqual(
            announce.hand_back("Country", "async_combobox", "United Kingdom"),
            "Country is a search box. I typed United Kingdom. "
            "Use the up and down arrows to pick from the list, then Enter.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
