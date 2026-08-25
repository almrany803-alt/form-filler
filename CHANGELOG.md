# Changelog

All notable changes to Job Form Filler. Newest first.

## 0.9.33

### Read a combobox's real options via ARIA (aria-controls + aria-activedescendant)
- The option reader now also reads aria-activedescendant, the option the widget
  itself highlights, and falls back to it when the aria-controls listbox reads
  empty (which is what a type-to-filter prompt like Workday's shows until you
  type). This offers the widget's own highlighted option instead of a stray
  document match (the cause of the "Saudi Arabia" leak on "How did you hear").
- Added diagnostics (aria-controls target count, the highlighted option) so a live
  log shows exactly what a given prompt exposes. Read-only: no keys, no mouse.
## 0.9.32

### Choose the vision model (so local Ollama models are actually usable)
- The Vision settings dialog now has a Model field and an Ollama host field. This
  is what lets you run a specific local model: set the backend to Ollama and the
  model to llava or qwen2.5vl:3b, no key, fully offline. It also lets cloud users
  pin a specific model. Blank means the backend's default.
## 0.9.32

### Choose the vision model (so local Ollama models can be tested)
- Vision settings now has a Model field and an Ollama host field. For local Ollama
  you can set the model (for example llava or qwen2.5vl:3b) instead of being stuck
  on the default, and point at a non-default host if needed. Blank means the
  backend's own default and localhost:11434. This is what lets you compare local
  open-source vision models, which need no API key, entirely on your machine.
## 0.9.31

### Vision errors now explain themselves
- When a vision call fails, the add-on now captures the provider's actual response
  body (which says why, for example a tier that doesn't allow image input) instead
  of only the HTTP status, and it speaks a short "check your key and backend"
  message instead of failing silently. This is diagnostic only; nothing about the
  fill path or the deterministic layer changes.
## 0.9.30

### Two privacy-first free vision backends: Mistral and Groq
- Added Mistral (Pixtral) and Groq as free, no-card vision backends alongside
  Gemini. Both are OpenAI-compatible and, unlike Gemini's free tier, do not train
  on your inputs, which matters when the image is a form field. Gemini stays the
  quality option; Mistral is the cleanest privacy story; Groq is fast and private.
  Pick per how sensitive the form is in Vision (AI) settings.
## 0.9.29

### Vision backend fix: Gemini (free key) replaces the now-paywalled Pollinations
- Pollinations began requiring authentication in April 2026, so its no-key
  endpoint returned 403. Google Gemini is now the recommended free backend: a free
  key from aistudio.google.com (no credit card), generous limits, vision-capable.
  Ollama (local) and an own-key OpenAI-compatible option remain; Pollinations stays
  as a token-based choice.
- The deterministic layer is confirmed working on live Workday: the fingerprint
  database classifies "How did you hear" and the phone country-code prompt, and the
  country-code prompt fills and commits, with no AI involved.
## 0.9.28

### Phase 1: optional AI vision fallback (opt-in, read-only, off by default)
- When a field can't be identified or filled from the profile, and only if the
  user turns vision on, the add-on now looks at just that one control's pixels and
  says what it is ("this looks like a dropdown showing United Kingdom"). It folds
  into the existing Fill path as a last-resort fallback, no new fill command: it
  runs only at a genuine dead-end, never before a successful fill, and only when
  enabled.
- It advises and records; it never fills or clicks. Where vision reads a different
  KIND than our own classification, the structural signals (never any personal
  data or field value) are written to a local disagreement log, the raw material
  for improving the free heuristics and the fingerprint database.
- Backends: Pollinations (free, no key, default), Ollama (local, private), or your
  own OpenAI-compatible key. One "Vision (AI) settings..." menu item toggles it,
  picks the backend, and offers a "share with developer" button, nothing is ever
  sent without that deliberate press.
- Dependency-free: a pure-Python PNG encoder and a GDI capture, no bundled
  imaging library; the provider layer is modelled on AI Content Describer.
## 0.9.27

### Field fingerprint database, wired in (database-first classification)
- Classification now consults a shared, offline field fingerprint database before
  the heuristics: a known widget (keyed on platform plus its stable signals) is
  classified deterministically, with no guessing and no AI. Seeded from real
  Workday signals, so "How Did You Hear About Us?", the country button, the
  country-code prompt, and the preferred-name checkbox are recognised from the
  database. Logged as "JFF fingerprint: ..." so a log shows which layer decided.
- The database is a plain JSON file (field_fingerprints.json) that can be updated
  and shared on its own. Falls through to the existing heuristics when nothing
  matches, so behaviour is unchanged for everything else. Still verified by
  behaviour downstream; the database picks which method to try, nothing more.
## 0.9.26

### "How did you hear" combobox, and findable scans
- Workday search prompts expose neither aria-haspopup nor a collapsed state to
  NVDA, but their placeholder is "Search". An editable field with a Search
  placeholder is now recognised as a type-to-filter combobox, so "How Did You
  Hear About Us?" opens a chooser you can pick from instead of a text box.
- The scan now saves a timestamped file to Documents\jobFormFiller (falling back
  to the NVDA config folder), keeps the last 20, and announces the full folder in
  the message, so it's findable and holds more than one.
## 0.9.25

### "How Did You Hear About Us?" and similar prompts now open as choosers
- Workday's search prompts hide aria-haspopup from NVDA, so the add-on saw them
  as plain text and offered a type box. But NVDA still reports the field as
  collapsed ("Minimized"), so the add-on now recognises an editable field that can
  expand as a type-to-filter combobox, reads its options, and lets you pick.
  Plain text fields and dropdown-trigger buttons are unaffected.
## 0.9.24

### Real labels, no more button mis-classification (found via a live Workday scan)
- Fields now show their real accessible label ("How Did You Hear About Us?") in
  the review and scan, instead of a name derived from the id ("Source source").
  _humanize_field was ignoring the label the descriptor already captured.
- Buttons are no longer treated as type-to-filter comboboxes. The previous change
  over-reached and turned page buttons and Workday's country button (a button that
  opens a dropdown) into "comboboxes"; only real text inputs with a popup are now
  routed that way.
- Workday is detected from its name--name field id pattern (source--source,
  country--country) when the URL isn't decisive, so the scan reports the platform
  on the live page.

### Known, not yet fixed
- Workday's country is a button that opens a list, so it can't be filled by typing
  yet; it needs the button activated first. Next up.
## 0.9.23

### Workday "prompt" dropdowns recognised (country, How did you hear, and more)
- Workday builds its dropdowns as "prompts" that NVDA exposes as plain text
  inputs, so the add-on was about to type values like "Saudi Arabia" into the
  country field as dead text that never commits, and it left the "How Did You
  Hear About Us?" box as an unfillable type box. Any field that declares a popup
  (aria-haspopup = listbox / menu / grid / tree) is now treated as a
  type-to-filter combobox: it types, presses Enter, verifies the commit, and
  offers the options chooser when there's nothing saved. This repairs country,
  source, and the other Workday prompts together.

## 0.9.22

### Real Workday form fixes (found via a live scan)
- Platform detection now uses the page URL first (myworkdayjobs.com, taleo.net,
  and so on). Workday hides its markup markers (data-automation-id) from NVDA and
  uses hashed CSS classes, so markup detection failed on real Workday forms; the
  URL is reliable.
- A checkbox is never auto-filled from a non-boolean value. Workday's
  "I have a preferred name" checkbox (id name--preferredCheck) was matching the
  full-name field and getting toggled; now free text like a name leaves a checkbox
  untouched, and the scan reports it honestly.

## 0.9.21

### Scan this form (read-only diagnostic and overview)
- New "Scan this form" command in the NVDA+J menu. It walks every field and
  writes a report, its name, detected control kind, the ATS platform, and what
  the add-on would do for each, to a file you can send and to the NVDA log. It
  never fills or submits. Proven on a live 41-field form.

## 0.9.20

### Calendar flow proven; platform behaviour and logging
- The date write-back and date-picker opening are verified on a real date field:
  a date of birth types back into the field in its own format (confirmed by the
  field's own value), and a date-picker combobox opens our day/month/year picker
  instead of a calendar grid.
- The detected ATS platform is now logged on every fill ("JFF platform: ..."),
  not only when the editor is offered.
- Workday comboboxes are routed to the type-and-Enter fill, since Workday's
  dropdowns are type-to-filter.

## 0.9.19

### Calendar date pickers and platform awareness
- A date-picker combobox (one that opens a calendar dialog or grid) is now
  recognised and routed to our own accessible day/month/year picker; the chosen
  date is typed back into the field in its own format, so the user never has to
  navigate a grid of day cells.
- The review recognises an open calendar's day cells and skips them quietly,
  instead of reading out dozens of "Monday, June 29th" buttons, and treats the
  date-picker field itself as a single date row.
- Platform detection: the add-on identifies the ATS (Greenhouse, SuccessFactors,
  Workday, select2, Taleo, iCIMS) from markup signatures, logged for now and used
  to route dates and dropdowns the way each platform builds them.

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
