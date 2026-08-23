# Job Form Filler (NVDA add-on)

Fills job application forms from your saved details, in many languages, with
spoken and braille review. It is built for screen reader users: it identifies
each field, fills the ones it is sure of, and tells you plainly what it filled
and what it left for you. It never submits a form.

## What it does

- One key, NVDA+J, opens a menu you can arrow through or drive by access key:
  Fill this field, Fill all fields, Review fields, Profile (switch, create,
  delete versions), Import from CV, Enter your details.
- Fills text fields, native dropdowns (locale aware), radio groups, and
  checkboxes, verifying each against the live accessibility state. Custom
  comboboxes, multi-select, dates, and async search boxes are in progress.
- Review fields: an accessible list over the current form where you can set and
  fix any field, including controls the site built badly.
- Multilingual field recognition (English, Spanish, French, German, Italian,
  Portuguese, Polish, Dutch, Arabic), by label, HTML name, and aria-label, then
  a keyword lexicon you can extend. An optional nationality field for Saudi forms.
- Declines fields it cannot confidently identify, rather than guessing, and
  never submits a form.

The menu key is changeable in NVDA's Input Gestures, under "Job Form Filler".

## Your data stays yours

Your details are stored encrypted on your own machine (Windows DPAPI). Nothing
leaves your computer. Optional AI features (for the messy fields and open-ended
questions) are off by default and, when on, use your own API key; only then does
any text leave the machine, and only for the fields you choose.

## Install

Download the latest `jobFormFiller-*.nvda-addon` from the Releases page, press
Enter on it, and let NVDA restart. Requires NVDA 2024.1 or newer. Tested on
NVDA 2026.1.

## Develop and test

The logic ("the brain") is pure Python and fully testable without NVDA:

```
python -m unittest discover -s tests -p "test_*.py"
```

Build the installable add-on:

```
python build.py        # produces jobFormFiller-<version>.nvda-addon
```

Real-NVDA, real-browser tests (run on Windows or a Windows CI runner) live in
`betatest/`, driven on real NVDA and real Chrome in GitHub Windows CI.

## Licence

GPL v2. See LICENSE.
