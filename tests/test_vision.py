"""Tests for the Phase 1 vision provider logic (no NVDA, no network)."""

import os
import sys
import json
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "addon", "globalPlugins", "jobFormFiller"))

from core import vision  # noqa: E402


class TestParseReading(unittest.TestCase):
    def test_plain_json(self):
        r = vision.parse_reading(
            '{"kind":"dropdown","label":"Country","current_value":"United '
            'Kingdom","expandable":true,"keyboard_hint":"Down",'
            '"confidence":"high"}')
        self.assertEqual(r["kind"], "dropdown")
        self.assertEqual(r["label"], "Country")
        self.assertEqual(r["current_value"], "United Kingdom")
        self.assertTrue(r["expandable"])
        self.assertEqual(r["confidence"], "high")

    def test_code_fenced_json(self):
        r = vision.parse_reading(
            'Here you go:\n```json\n{"kind":"date","expandable":true}\n```')
        self.assertIsNotNone(r)
        self.assertEqual(r["kind"], "date")

    def test_prose_around_json(self):
        r = vision.parse_reading(
            'The control appears to be {"kind":"checkbox"} based on the image.')
        self.assertEqual(r["kind"], "checkbox")

    def test_unknown_kind_becomes_blank(self):
        r = vision.parse_reading('{"kind":"slider"}')
        self.assertEqual(r["kind"], "")

    def test_expandable_as_string(self):
        r = vision.parse_reading('{"kind":"combobox","expandable":"true"}')
        self.assertTrue(r["expandable"])

    def test_no_json_returns_none(self):
        self.assertIsNone(vision.parse_reading("I cannot tell what this is."))
        self.assertIsNone(vision.parse_reading(""))
        self.assertIsNone(vision.parse_reading(None))

    def test_malformed_json_returns_none(self):
        self.assertIsNone(vision.parse_reading('{"kind": dropdown'))

    def test_kind_normalised_lowercase(self):
        r = vision.parse_reading('{"kind":"DropDown"}')
        self.assertEqual(r["kind"], "dropdown")


class TestProviders(unittest.TestCase):
    def test_gemini_needs_key_and_builds_url(self):
        p = vision.get_provider("gemini", api_key="AIza-test")
        self.assertTrue(p.needs_api_key)
        self.assertTrue(p.is_available())
        self.assertIn("generativelanguage.googleapis.com", p._url())
        self.assertIn("key=AIza-test", p._url())

    def test_gemini_payload_has_inline_image(self):
        p = vision.get_provider("gemini", api_key="k")
        payload = p._payload("B64", vision.IDENTIFY_PROMPT)
        parts = payload["contents"][0]["parts"]
        self.assertEqual(parts[1]["inline_data"]["mime_type"], "image/png")

    def test_pollinations_now_needs_a_token(self):
        p = vision.get_provider("pollinations")
        self.assertTrue(p.needs_api_key)
        self.assertFalse(p.is_available())

    def test_pollinations_payload_shape(self):
        p = vision.PollinationsProvider()
        payload = p._payload("BASE64DATA", vision.IDENTIFY_PROMPT)
        # OpenAI-compatible: a user message with text + an image_url data URI
        content = payload["messages"][0]["content"]
        kinds = [c["type"] for c in content]
        self.assertIn("text", kinds)
        self.assertIn("image_url", kinds)
        url = [c for c in content if c["type"] == "image_url"][0]
        self.assertTrue(url["image_url"]["url"].startswith(
            "data:image/png;base64,"))

    def test_ollama_targets_localhost(self):
        p = vision.get_provider("ollama")
        self.assertIn("localhost:11434", p._url())
        payload = p._payload("BASE64DATA", "prompt")
        self.assertEqual(payload["images"], ["BASE64DATA"])
        self.assertFalse(payload["stream"])

    def test_openai_compatible_needs_key(self):
        p = vision.get_provider("openai_compatible")
        self.assertTrue(p.needs_api_key)
        self.assertFalse(p.is_available())  # no key yet
        p2 = vision.get_provider("openai_compatible", api_key="sk-test")
        self.assertTrue(p2.is_available())
        self.assertIn("Authorization", p2._headers())

    def test_unknown_provider_defaults_to_gemini(self):
        p = vision.get_provider("nonesuch")
        self.assertEqual(p.name, "gemini")

    def test_payloads_are_json_serialisable(self):
        for name in ("gemini", "pollinations", "ollama", "openai_compatible"):
            p = vision.get_provider(name, api_key="k")
            json.dumps(p._payload("B64", "prompt"))  # must not raise


if __name__ == "__main__":
    unittest.main()


class TestKindMappingAndDisagreement(unittest.TestCase):
    def test_vision_kinds_map_to_addon_kinds(self):
        self.assertEqual(vision.to_addon_kind("dropdown"), "async_combobox")
        self.assertEqual(vision.to_addon_kind("combobox"), "async_combobox")
        self.assertEqual(vision.to_addon_kind("date"), "datepicker")
        self.assertEqual(vision.to_addon_kind("checkbox"), "checkbox")
        self.assertEqual(vision.to_addon_kind("text"), "text")
        self.assertEqual(vision.to_addon_kind("slider"), "")

    def test_disagreement_when_we_said_text_but_its_a_dropdown(self):
        # the exact Workday case: we classified text, vision sees a dropdown
        self.assertTrue(vision.disagrees("text", "dropdown"))

    def test_no_disagreement_across_combobox_variants(self):
        # our internal combobox variants all mean "dropdown"; not a disagreement
        self.assertFalse(vision.disagrees("native_select", "dropdown"))
        self.assertFalse(vision.disagrees("async_combobox", "combobox"))

    def test_no_disagreement_when_kinds_match(self):
        self.assertFalse(vision.disagrees("checkbox", "checkbox"))
        self.assertFalse(vision.disagrees("datepicker", "date"))

    def test_no_disagreement_when_vision_has_no_clear_kind(self):
        self.assertFalse(vision.disagrees("text", "slider"))
        self.assertFalse(vision.disagrees("text", ""))


class TestMistralGroqPresets(unittest.TestCase):
    def test_mistral_preset(self):
        p = vision.get_provider("mistral", api_key="k")
        self.assertTrue(p.needs_api_key)
        self.assertIn("api.mistral.ai", p._url())
        self.assertIn("Authorization", p._headers())

    def test_groq_preset(self):
        p = vision.get_provider("groq", api_key="k")
        self.assertTrue(p.needs_api_key)
        self.assertIn("api.groq.com", p._url())

    def test_both_send_openai_image_payload(self):
        for name in ("mistral", "groq"):
            p = vision.get_provider(name, api_key="k")
            content = p._payload("B64", "prompt")["messages"][0]["content"]
            kinds = [c["type"] for c in content]
            self.assertIn("image_url", kinds)
