# Job Form Filler (NVDA add-on)

Fills job application forms from your saved details, in many languages, with
spoken and braille review. It is built for screen reader users: it identifies
each field, fills the ones it is sure of, and tells you plainly what it filled
and what it left for you. It never submits a form.

## What it does

- One key, NVDA+J, opens a menu you can arrow through or drive by access key:
  Fill this field, Fill all fields, Review fields, Profile (switch, create,
  delete versions), Import from CV, Enter your details.
- Fills text fields, native dropdowns, radio groups, checkboxes, multi-selects,
  and dates, verifying each against the live accessibility state. Custom
  comboboxes (react-select and similar) are opened by keyboard, the way you do
  it by hand, and their options read from the live page. Date fields that a site
  builds as a plain text box (SAP UI5 / SuccessFactors) are recognised by their
  format and aria-roledescription.
- Fill this field (NVDA+J then F) always gives you a way to complete the field.
  When the add-on knows the answer it fills it; when it does not, it opens the
  right accessible editor on the spot instead of handing it back: Yes/No for a
  checkbox, an options chooser for a dropdown, the choices for a radio group, a
  picker for a date, or a type box for text. So the review is no longer the only
  way to set a field.
- Review fields: an accessible list over the current form where you can set and
  fix any field through the right accessible control, a chooser you arrow
  through for a dropdown or radio group, Yes/No for a checkbox, a multi-check
  list, or three dropdowns for a date, even on controls the site built badly.
  The review and Fill share one editor, so both behave identically.
- Recognises the common application fields, sourced from the same field
  dictionary browsers use: name parts (including father's and preferred name,
  name prefix and suffix), email, phone (with separate dial code and extension),
  address lines 1 to 3, house number, city, state or province, district,
  postcode, country, nationality, organisation, date of birth, and passport
  fields (number, name, issuing country, issue and expiry dates).
- Multilingual field recognition by label, HTML name, and aria-label, using a
  keyword lexicon you can extend. Thirteen languages so far (English, Arabic,
  Spanish, French, German, Italian, Portuguese, Polish, Dutch, Chinese,
  Japanese, Korean, Russian), matched on whole-word boundaries, and script-aware
  for Chinese and Japanese, which have no spaces between words. The set is
  growing to match the 24-language country data. The HTML autocomplete attribute
  is language-independent, so well-built forms in any language map with no
  translation at all.
- Country and nationality are chosen from a dropdown of all countries and match
  the page's option in 24 languages (so an Arabic or French form still matches);
  on CV import your country is detected and pre-filled. Date of birth is three
  dropdowns.
- Declines fields it cannot confidently identify, rather than guessing, and
  never submits a form.

The menu key is changeable in NVDA's Input Gestures, under "Job Form Filler".

## Your data stays yours

Your details are stored encrypted on your own machine (Windows DPAPI). The
add-on is fully deterministic: no AI, no network, no API keys. Nothing you enter
ever leaves your computer. (Field matching is a dictionary-and-rules job, the
same approach browsers and the main job-autofill tools use; the only thing "AI
autofill" tools use a model for is writing answers to open-ended custom
questions, which you write far better yourself.)

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

## Country data

The country list and its translations come from the open mledoze/countries
project (https://github.com/mledoze/countries), reused with attribution under
its ODbL 1.0 data licence.

## Licence

GPL v2. See LICENSE.
