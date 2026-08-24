#!/usr/bin/env python3
"""
LOCAL vision spike for Job Form Filler. Nothing leaves your machine.

Tests two things at once: whether a local vision model can correctly identify a
web form control from a screenshot (accuracy, independent of your hardware), and
how long it takes on YOUR machine (speed). On integrated graphics expect it to be
slow; the point is to see the accuracy and the real timing before we commit.

Get going:
  1. Install Ollama (one installer, Windows/Mac/Linux): https://ollama.com/download
  2. In a terminal, pull a small vision model:
       ollama pull moondream          (~1.7 GB, lightest, try this first)
     If moondream's read is too vague, try a stronger, slower one:
       ollama pull qwen2.5vl:3b       (bigger, more accurate on UI)
  3. Screenshot the control that stumps the add-on (Win+Shift+S), save widget.png
  4. python vision_spike_local.py widget.png
     or:  python vision_spike_local.py widget.png qwen2.5vl:3b

Read-only: it fills nothing and clicks nothing.
"""
import sys
import os
import time
import json
import base64
import urllib.request
import urllib.error

PROMPT = (
    "You are assisting a blind screen-reader user who is filling a web form and "
    "cannot see this control. The image is a single form field, cropped tight. "
    "Reply in STRICT JSON only, no prose, with these keys: "
    '"kind" (one of text, dropdown, combobox, button, checkbox, radio, date), '
    '"label" (the visible label, or ""), '
    '"current_value" (what it shows now, or ""), '
    '"expandable" (true if it opens a list, menu, or calendar), '
    '"keyboard_hint" (the single key most likely to open it: Enter, Down, Space, '
    'or type-to-filter), '
    '"confidence" (high, medium, or low).'
)

OLLAMA = "http://localhost:11434/api/generate"


def main():
    if len(sys.argv) < 2:
        print("usage: python vision_spike_local.py <screenshot.png> [model]")
        return
    img_path = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "moondream"
    if not os.path.exists(img_path):
        print("no such file:", img_path)
        return
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    payload = json.dumps({
        "model": model,
        "prompt": PROMPT,
        "images": [b64],
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA, data=payload,
        headers={"Content-Type": "application/json"})
    print("Asking local model %r ... (first run loads the model into memory, "
          "so be patient)" % model)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print("\nCould not reach Ollama at localhost:11434.")
        print("Install it from https://ollama.com/download, then run:")
        print("    ollama pull %s" % model)
        print("Detail:", e)
        return
    dt = time.time() - t0
    print("\n=== what the LOCAL vision model sees (%.1f seconds on your machine) ==="
          % dt)
    print(out.get("response", out))
    print("\n(Local and read-only: nothing left your machine, nothing was filled "
          "or clicked.)")


if __name__ == "__main__":
    main()
