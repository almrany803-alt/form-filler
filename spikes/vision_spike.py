#!/usr/bin/env python3
"""
Vision spike for Job Form Filler.

Purpose: prove, cheaply and BEFORE writing any add-on code, that a vision model
can identify a web form control from a screenshot. This is the one assumption the
whole "operate widgets end to end" idea rests on. Read-only: it fills nothing and
clicks nothing.

Get going (about 10 minutes):
  1. Free Gemini key (no credit card): https://aistudio.google.com/apikey
  2. pip install google-genai
  3. Windows:  set GEMINI_API_KEY=your_key_here
     mac/linux: export GEMINI_API_KEY=your_key_here
  4. Screenshot the control that stumps the add-on. On the live Workday form,
     focus the "How Did You Hear About Us?" box or Country, then snip just that
     control (Windows: Win+Shift+S) and save it as widget.png.
  5. python vision_spike.py widget.png

It prints the model's read of the control: what kind it is, its label, the value
it shows, whether it expands, and the likely key to open it. That tells us whether
vision solves the classification-and-operation gap the accessibility tree can't.
"""
import os
import sys

PROMPT = (
    "You are assisting a blind screen-reader user who is filling a web form and "
    "cannot see this control. The image is a single form field, cropped tight. "
    "Reply in STRICT JSON only, no prose, with these keys:\n"
    '  "kind": one of text, dropdown, combobox, button, checkbox, radio, date\n'
    '  "label": the field\'s visible label, or "" if none is shown\n'
    '  "current_value": what the field currently shows, or "" if empty\n'
    '  "expandable": true if it opens a list, menu, or calendar\n'
    '  "keyboard_hint": the single key most likely to open or operate it '
    "(for example Enter, Down, Space, or type-to-filter)\n"
    '  "confidence": high, medium, or low'
)


def main():
    if len(sys.argv) < 2:
        print("usage: python vision_spike.py <screenshot.png>")
        return
    img_path = sys.argv[1]
    if not os.path.exists(img_path):
        print("no such file:", img_path)
        return
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("Set GEMINI_API_KEY first "
              "(free key: https://aistudio.google.com/apikey)")
        return
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Run:  pip install google-genai")
        return

    with open(img_path, "rb") as f:
        data = f.read()

    client = genai.Client(api_key=key)
    resp = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[PROMPT,
                  types.Part.from_bytes(data=data, mime_type="image/png")],
    )
    print("\n=== what the vision model sees ===")
    print(resp.text)
    print("\n(Read-only: nothing was filled or clicked.)")


if __name__ == "__main__":
    main()
