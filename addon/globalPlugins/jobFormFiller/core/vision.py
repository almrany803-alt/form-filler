"""Vision provider abstraction for Job Form Filler (Phase 1: identify only).

This is an OPTIONAL, opt-in module. When the add-on's instant, keyboard-first
checks can't identify a control, and only if the user has turned vision on in
settings, the add-on may send just that one control's pixels to a vision model
and get back a structured reading of what the control is. The model only ever
ADVISES: its reading can correct a classification so the right editor is offered,
but it never fills or clicks on its own, and the outcome is still judged by what
NVDA reads. Nothing here runs unless the user enables it.

Design, modelled on AI Content Describer's provider pattern (GPL v2, same licence
as this add-on):
  - A BaseVisionProvider with thin subclasses per backend.
  - Dependency-free: urllib only, so nothing needs bundling into the add-on.
  - The free, no-key Pollinations backend is the default, so vision works the
    moment it's enabled with no signup. A local Ollama backend is available for
    users who want everything to stay on their machine.

Only pure logic lives here (payload building, response parsing). Screen capture
and NVDA wiring live in the add-on layer, so this file stays importable and
testable on its own, without NVDA.
"""

import json
import base64
import urllib.request
import urllib.error


# The fixed question we ask about a single, tightly-cropped control. Kept here so
# the same wording is used across every backend and is easy to audit.
IDENTIFY_PROMPT = (
    "You are assisting a blind screen-reader user filling a web form who cannot "
    "see this control. The image is a single form field, cropped tight. Reply in "
    "STRICT JSON only, no prose, with these keys: "
    '"kind" (one of: text, dropdown, combobox, button, checkbox, radio, date), '
    '"label" (the visible label, or ""), '
    '"current_value" (what it shows now, or ""), '
    '"expandable" (true if it opens a list, menu, or calendar), '
    '"keyboard_hint" (the single key most likely to open it: Enter, Down, Space, '
    'or type), '
    '"confidence" (high, medium, or low).'
)

# The control kinds a reading may claim, mapped to the add-on's own vocabulary by
# the caller. Anything outside this set is treated as "unknown" and ignored.
KNOWN_KINDS = ("text", "dropdown", "combobox", "button", "checkbox", "radio",
               "date")


def parse_reading(text):
    """Extract the JSON reading from a model's text reply, tolerant of code
    fences and stray prose around it. Returns a normalised dict, or None if no
    usable JSON object is present. Never raises."""
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        raw = json.loads(text[start:end + 1])
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind", "")).strip().lower()
    if kind not in KNOWN_KINDS:
        kind = ""
    exp = raw.get("expandable", False)
    if isinstance(exp, str):
        exp = exp.strip().lower() in ("true", "yes", "1")
    return {
        "kind": kind,
        "label": str(raw.get("label", "")).strip(),
        "current_value": str(raw.get("current_value", "")).strip(),
        "expandable": bool(exp),
        "keyboard_hint": str(raw.get("keyboard_hint", "")).strip(),
        "confidence": str(raw.get("confidence", "")).strip().lower(),
    }


# Map a vision reading's kind onto the add-on's own control vocabulary, so a
# reading can be compared with classify_control's verdict (to spot a disagreement)
# and, from Phase 2 on, act on it. A kind vision doesn't recognise maps to "",
# which the caller treats as "no opinion" and ignores.
_KIND_MAP = {
    "text": "text",
    "dropdown": "async_combobox",
    "combobox": "async_combobox",
    "date": "datepicker",
    "checkbox": "checkbox",
    "radio": "radio",
    "button": "button",
}


def to_addon_kind(vision_kind):
    """Translate a vision reading's kind into the add-on's control kind, or "" if
    there's no clear equivalent."""
    return _KIND_MAP.get((vision_kind or "").strip().lower(), "")


def disagrees(addon_kind, vision_kind):
    """True when vision confidently sees a different KIND of control than the
    add-on's own classification did, i.e. a gap in our free heuristics worth
    logging. Only fires when vision maps to a known kind and the two differ; a
    blank or matching reading is not a disagreement."""
    mapped = to_addon_kind(vision_kind)
    if not mapped:
        return False
    a = (addon_kind or "").strip().lower()
    # our combobox family all mean "a dropdown", so don't count internal variants
    combo = ("async_combobox", "editable_combobox", "aria_combobox",
             "native_select", "multiselect")
    if mapped == "async_combobox" and a in combo:
        return False
    if mapped == "datepicker" and a in ("datepicker",):
        return False
    return mapped != a


def _post_json(url, payload, headers, timeout):
    """POST JSON and return the parsed JSON response. urllib only; the caller
    handles URLError/timeout so failures fall back to today's behaviour."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class BaseVisionProvider:
    """A vision backend. Subclasses supply the URL, headers, request payload, and
    how to pull the text answer out of the response. Everything else, encoding the
    image and parsing the reading, is shared."""

    name = "base"
    needs_api_key = False
    default_model = ""

    def __init__(self, api_key="", base_url="", model=""):
        self.api_key = api_key or ""
        self.base_url = base_url or ""
        self.model = model or self.default_model

    def is_available(self):
        """True when this backend is usable as configured (a key is present if one
        is required). The settings UI uses this to only offer configured
        backends."""
        return (not self.needs_api_key) or bool(self.api_key)

    def _url(self):
        raise NotImplementedError

    def _headers(self):
        return {"Content-Type": "application/json"}

    def _payload(self, image_b64, prompt):
        raise NotImplementedError

    def _extract(self, response):
        raise NotImplementedError

    def identify(self, image_bytes, prompt=IDENTIFY_PROMPT, timeout=20):
        """Send one control image and return its reading dict, or None on any
        failure. Read-only: this asks a question, it changes nothing."""
        b64 = base64.b64encode(image_bytes).decode("ascii")
        response = _post_json(self._url(), self._payload(b64, prompt),
                              self._headers(), timeout)
        return parse_reading(self._extract(response))


class GoogleGemini(BaseVisionProvider):
    """Google Gemini. The recommended free backend now: a free key from
    aistudio.google.com (no credit card), generous limits, vision-capable. Uses
    Gemini's own contents/parts request shape, not the OpenAI one."""

    name = "gemini"
    needs_api_key = True
    default_model = "gemini-2.0-flash"

    def _url(self):
        base = self.base_url or "https://generativelanguage.googleapis.com"
        return ("%s/v1beta/models/%s:generateContent?key=%s"
                % (base.rstrip("/"), self.model, self.api_key))

    def _payload(self, image_b64, prompt):
        return {"contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": image_b64}},
        ]}]}

    def _extract(self, response):
        return response["candidates"][0]["content"]["parts"][0]["text"]


class PollinationsProvider(BaseVisionProvider):
    """Pollinations, OpenAI-compatible. Since April 2026 it requires a token
    (register at auth.pollinations.ai), so it now needs a key like the others.
    Kept as an option, no longer the zero-setup default."""

    name = "pollinations"
    needs_api_key = True
    default_model = "openai"

    def _url(self):
        return (self.base_url or "https://text.pollinations.ai") + "/openai"

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = "Bearer " + self.api_key
        return h

    def _payload(self, image_b64, prompt):
        return {
            "model": self.model,
            "max_tokens": 300,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": "data:image/png;base64," + image_b64}},
            ]}],
        }

    def _extract(self, response):
        return response["choices"][0]["message"]["content"]


class OllamaProvider(BaseVisionProvider):
    """Local and private: talks to Ollama on the user's own machine, so nothing
    leaves the computer. For users who have the hardware to run it."""

    name = "ollama"
    needs_api_key = False
    default_model = "moondream"

    def __init__(self, api_key="", base_url="", model=""):
        super().__init__(api_key, base_url or "http://localhost:11434", model)

    def _url(self):
        return (self.base_url or "http://localhost:11434") + "/api/generate"

    def _payload(self, image_b64, prompt):
        return {"model": self.model, "prompt": prompt, "images": [image_b64],
                "stream": False}

    def _extract(self, response):
        return response.get("response", "")


class OpenAICompatibleProvider(BaseVisionProvider):
    """A generic OpenAI-compatible backend for a user who brings their own key and
    base URL (their own proxy, a paid model, LiteLLM, and so on)."""

    name = "openai_compatible"
    needs_api_key = True
    default_model = "gpt-4o-mini"

    def _url(self):
        base = self.base_url or "https://api.openai.com/v1"
        return base.rstrip("/") + "/chat/completions"

    def _headers(self):
        return {"Content-Type": "application/json",
                "Authorization": "Bearer " + self.api_key}

    def _payload(self, image_b64, prompt):
        return {
            "model": self.model,
            "max_tokens": 300,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": "data:image/png;base64," + image_b64}},
            ]}],
        }

    def _extract(self, response):
        return response["choices"][0]["message"]["content"]


PROVIDERS = {cls.name: cls for cls in (
    GoogleGemini, OllamaProvider, PollinationsProvider,
    OpenAICompatibleProvider)}


def get_provider(name, api_key="", base_url="", model=""):
    """Build a provider by name, defaulting to the free Pollinations backend when
    the name is unknown or empty."""
    cls = PROVIDERS.get(name, GoogleGemini)
    return cls(api_key=api_key, base_url=base_url, model=model)
