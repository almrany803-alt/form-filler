import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addon", "globalPlugins", "jobFormFiller"))
from core import matcher

def key(label):
    return matcher.match_field(matcher.FieldDescriptor(label=label)).key

class Nationality(unittest.TestCase):
    def test_distinct_from_country(self):
        self.assertEqual(key("Nationality"), "nationality")
        self.assertEqual(key("Citizenship"), "nationality")
        self.assertEqual(key("الجنسية"), "nationality")
        self.assertEqual(key("Country"), "country")
        self.assertEqual(key("Country of residence"), "country")
        self.assertEqual(key("الدولة"), "country")
    def test_nationality_is_a_profile_key(self):
        self.assertIn("nationality", matcher.PROFILE_KEYS)

if __name__ == "__main__":
    unittest.main()
