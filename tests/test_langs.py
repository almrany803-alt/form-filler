import os, sys, unittest

HERE = os.path.dirname(__file__)
CORE = os.path.join(HERE, "..", "addon", "globalPlugins", "jobFormFiller", "core")
sys.path.insert(0, os.path.abspath(CORE))

from matcher import FieldDescriptor as F, match_field, _norm
import cvparse


def key(label):
    return match_field(F(label=label)).key


class TestLanguageLabels(unittest.TestCase):
    CASES = {
        # Spanish
        "Apellidos": "family_name", "Teléfono": "phone", "Dirección": "address_line1",
        "Código postal": "postcode", "País": "country",
        "Nombre": "given_name", "Nombre completo": "full_name",
        # Italian
        "Cognome": "family_name", "Cellulare": "phone", "Città": "city",
        "Nome completo": "full_name",
        # Portuguese
        "Apelido": "family_name", "Telemóvel": "phone", "Morada": "address_line1",
        # Polish
        "Imię": "given_name", "Nazwisko": "family_name",
        "Imię i nazwisko": "full_name", "Kod pocztowy": "postcode",
        "Miejscowość": "city", "Telefon": "phone",
        # Dutch
        "Voornaam": "given_name", "Achternaam": "family_name",
        "Woonplaats": "city", "Telefoonnummer": "phone",
        "Volledige naam": "full_name",
    }

    def test_all_language_labels(self):
        wrong = {lbl: (key(lbl), want) for lbl, want in self.CASES.items()
                 if key(lbl) != want}
        self.assertEqual(wrong, {}, f"mismatches: {wrong}")

    # --- teeth: full-name phrases must beat the bare first-name word --------
    def test_longest_match_across_languages(self):
        self.assertEqual(key("Imię i nazwisko"), "full_name")   # not given_name
        self.assertEqual(key("Nome completo"), "full_name")     # not given_name

    # --- folding: stroke and accented letters normalise to ascii -----------
    def test_folding(self):
        self.assertEqual(_norm("Łódź"), "lodz")
        self.assertEqual(_norm("Città"), "citta")
        self.assertEqual(_norm("Dirección"), "direccion")


class TestLanguageHeadings(unittest.TestCase):
    def test_polish_sections(self):
        cv = ("Jan Kowalski\n"
              "Wykształcenie\n"
              "Uniwersytet Warszawski, 2025\n"
              "Doświadczenie zawodowe\n"
              "Programista, ACME Sp. z o.o.\n")
        r = cvparse.parse_cv_text(cv)
        self.assertIn("education", r)
        self.assertIn("experience", r)

    def test_spanish_sections(self):
        cv = ("Educación\n"
              "Grado en Informática, 2025\n"
              "Experiencia laboral\n"
              "Desarrollador, ACME S.L.\n")
        r = cvparse.parse_cv_text(cv)
        self.assertIn("education", r)
        self.assertIn("experience", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
