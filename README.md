# Job Form Filler (NVDA add-on)

Fills job application forms from your saved details, in many languages, with
spoken and braille review. It is built for screen reader users: it identifies
each field, fills the ones it is sure of, and tells you plainly what it filled
and what it left for you. It never submits a form.

## What it does

- One key, NVDA+J, opens a menu you can arrow through or drive by access key:
  Fill this field, Fill all fields, Review fields, Profile (edit, switch, create,
  delete versions), Import from CV, Enter your details. Editing your profile
  opens the sections list (Personal information, then Experience, Education, and
  the rest); Enter opens the highlighted item throughout.
- Fills text fields, native dropdowns, radio groups, checkboxes, multi-selects,
  and dates, verifying each against the live accessibility state. Custom
  comboboxes (react-select and similar) are opened by keyboard, the way you do
  it by hand, and their options read from the live page. For a dropdown whose
  options load over the network, it waits on the control's own loading signal
  rather than a fixed delay. When your value is not an exact option it matches
  by known synonyms or a clear single choice, and hands the field back rather
  than risk a wrong pick when several options could fit. Multi-selects are filled
  one value at a time, coping with the chip style that redraws after each pick.
  Values are tidied of stray whitespace before typing (line breaks in a cover
  letter are kept). Date fields that a site builds as a plain text box (SAP UI5 /
  SuccessFactors) are recognised by their format and aria-roledescription. The
  add-on also recognises which ATS a form runs on (Workday, Greenhouse, Lever,
  Ashby, SmartRecruiters, iCIMS, Taleo, SuccessFactors, BambooHR, Workable and
  more) so it can handle each the way it builds its fields.
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
- Sections beyond the personal fields: Experience, Education, Skills,
  Certifications, Languages, and any you add. Each has a type, chosen when you
  create it (Work, Education, Skills, Certification, Languages, or Other), and the
  type decides an entry's fields; an Other section asks the entry type each time.
  You manage them in a shallow drill-down (sections, then entries, then one
  entry's fields), reached through Edit profile. A section you invent
  (Publications, Volunteering) behaves exactly like the built-in ones.
- Repeating Work and Education blocks: when a form has a section you can repeat
  (several jobs or courses, with an "Add another" control, as Workday and some
  Greenhouse forms do), filling the whole form asks which of your saved entries
  to place, most recent first and all ticked. It fills the blocks already there,
  adds more with the form's own "Add another", and matches each field by what it
  is (job title, employer, dates), then tells you how many it placed. It never
  removes blocks you already have and never submits.
- After the main fill, the add-on re-reads the form and fills fields that only
  appear once a question is answered (a Yes/No that opens a sub-form, an
  "other, please specify" box), so a conditional field is not silently
  missed. It never overwrites a field that already has a value.
- Fields about someone else (a referee, a reference, an emergency contact, a
  manager, a parent or guardian, next of kin) are never filled with your own
  name, email or phone; they are left for you, however personal their words
  look.
- Your clipboard is preserved: the add-on pastes to fill, but puts back
  whatever you had copied, so a fill neither destroys your clipboard nor leaves
  your own details sitting on it.
- Importing a CV fills those sections too, not just the personal fields, so you
  start with entries to review and correct instead of a blank slate. The reader
  handles real-world CV layouts: dates in parentheses, on their own line, or at
  the end of a header ("Developer, Globex 2018 to 2021"), and single graduation
  dates.
- When a form splits the phone across a country-code field and a number field,
  the dial code goes in one and the national number in the other, instead of the
  whole international number in both.
- File uploads (your CV, a cover letter) appear in the review as an
  attach-this-yourself reminder, so nothing is silently skipped; the add-on never
  types into a file field.
- Multilingual field recognition by label, HTML name, and aria-label, using a
  keyword lexicon you can extend. 27 languages (English plus the 26 the country
  data uses: Arabic, Spanish, French, German, Italian, Portuguese, Polish, Dutch,
  Chinese, Japanese, Korean, Russian, Turkish, Indonesian, Persian, Urdu, Czech,
  Hungarian, Finnish, Swedish, Croatian, Serbian, Slovak, Estonian, Welsh,
  Breton), matched on whole-word boundaries, and script-aware for Chinese and
  Japanese, which have no spaces between words. The HTML autocomplete attribute
  is language-independent, so well-built forms in any language map with no
  translation at all.
- Country and nationality are chosen from a dropdown of all countries and match
  the page's option in 24 languages (so an Arabic or French form still matches);
  on CV import your country is detected and pre-filled. Date of birth is three
  dropdowns.
- Declines fields it cannot confidently identify, rather than guessing, and
  never submits a form.

The menu key is changeable in NVDA's Input Gestures, under "Job Form Filler".

- Scan this form writes a plain report of every field, and (opt-in, offline) a
  discovery file listing any custom widgets no built-in rule covers yet, each
  with a suggested rule stub, so the add-on can be taught new platforms. It is
  read-only: Scan never fills or submits, and nothing leaves your computer.

## Your data stays yours

Your details are stored on your own device and never sent anywhere. The
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
