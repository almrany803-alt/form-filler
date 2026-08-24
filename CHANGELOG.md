# Changelog

All notable changes to Job Form Filler. Newest first.

## 0.9.18

### More fields fill themselves; unlabelled fields get real names
- Segmented dates (day/month/year dropdowns) are recognised in general, not just
  for birth dates. A date of birth fills straight from the profile; any other
  segmented date offers the picker with a proper name.
- Country dropdowns with no label (select2 and similar show only their current
  value) are recognised by their options and filled from the profile, instead of
  making you pick from ~200 countries.
- Fields with no accessible label now get a real name derived from their id or
  class (e.g. "Birthdate day"), so the review and Fill no longer say "an
  unlabelled field" everywhere.

## 0.9.17

### React-select fill now actually commits (Country, Location, demographics)
- The live Monzo log showed Country announcing "set to Saudi Arabia +966" while
  the field stayed blank: the fill typed the search text, "confirmed" on that
  typed text, and never selected. Fixed: the async-combobox fill presses Enter to
  select react-select's highlighted filtered match, and verifies the commit by
  the menu collapsing (react-select does not expose the chosen value to the
  accessibility tree at all, so a value read-back is impossible; the menu-collapse
  signal is the reliable one). A dead duplicate async branch was removed.
- Proven on a REAL react-select fixture whose own onChange value is read as the
  ground truth, so "typed but never selected" fails the test loudly. The add-on
  now speaks "Country set to United Kingdom" and the selection genuinely commits.

## 0.9.16

### Fill this field now completes any field (no more "over to you")
- Pressing Fill on a field the add-on cannot fill from your profile now opens
  the right accessible editor on the spot, instead of handing it back:
  Yes/No for a checkbox, an options chooser for a dropdown, the choices for a
  radio group, a date picker, or a type box for text. Proven on the live Monzo
  consent checkbox: Fill now opens a Yes/No chooser where it used to say
  "over to you".
- One shared editor (`dialogs.edit_field`) now backs both the review list and
  the Fill command, replacing the review's five duplicated per-kind editors.

### React-select and custom dropdowns
- Custom comboboxes (react-select: Country and demographic questions) are opened
  by a keyboard Down on the focused field, the way a user does by hand, and
  their options are read from the live page (via aria-controls, a focus walk, or
  a bounded document search for the portalled menu). No mouse is used anywhere.
- Editable/react-select writeback now commits: it types the value to filter the
  menu, then presses Enter to select the match, and verifies the value stuck.
  Previously it pasted without selecting, so the choice reverted on blur.

### SuccessFactors / STC fixes (from real page markup)
- Country false-confirm fixed. The native `<select>` could read a chosen option
  back transiently while the field stayed on "- Select -", and the old check
  confirmed that as success ("set to Saudi Arabia" over an empty, required
  field). The native-select fill now reads the value after it settles, never
  confirms a placeholder, and re-commits by keyboard if it did not stick.
- SAP UI5 date recognition. The Birth Date is a plain text input whose only date
  signals are aria-roledescription "Date Input" and a MM/DD/YYYY placeholder;
  these are now recognised as a date (locale-aware: MM/DD/YYYY, DD/MM/YYYY,
  JJ/MM/AAAA, TT.MM.JJJJ, YYYY-MM-DD).

### Fixes found on live Greenhouse / Lever forms
- Whole-form summary counted buttons, links and dropdown toggles as fields,
  reading a wall of names aloud. It now counts only real fillable fields,
  dedupes, and caps the spoken list.
- A single "Full name" field was left empty. `full_name` is now synthesised from
  the given and family names across all fill paths.
- The review offered a text editor for a file-upload row (Resume/CV) and
  misaligned every row. File uploads and buttons are now excluded from the
  review, so its rows line up with the real fields.

### Code quality
- Removed a stray `@script` decorator that was orphaned onto the `_value_for`
  helper (the whole-form fill command carried the wrong description).
- Removed the five duplicated review editors in favour of one shared function.

### Testing
- Added an applicant-style live harness that inspects the page source, lands on
  each field type the way a user tabs onto it, presses the add-on command, and
  judges only by what NVDA speaks.
- Absolute safety rule: the add-on never moves or clicks the mouse. Every control
  is opened by keyboard, and only after confirming the field holds focus. (An
  earlier experiment that synthesised screen clicks was removed entirely after it
  could land on other windows on a real desktop.)
