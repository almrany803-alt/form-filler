# Changelog

All notable changes to Job Form Filler. Newest first.

## 0.9.53

### Language finish: field matcher and CV reader to 24+ languages
- The field matcher now reads field labels in the full set the country data uses:
  27 languages (English plus 26), adding Turkish, Indonesian, Persian, Urdu,
  Czech, Hungarian, Finnish, Swedish, Croatian, Serbian, Slovak, Estonian, Welsh
  and Breton to the earlier thirteen. Core fields (name parts, email, phone,
  address, city, country, postcode, date of birth, nationality). The CV reader's
  section headings (Education, Experience, Skills) learned the same languages,
  and its name detection is now script-aware, so a Chinese or Japanese name (no
  spaces) is picked up as well as Latin, Arabic and Cyrillic ones. The smaller
  languages, Welsh and Breton especially, are a best-effort seed for native
  speakers to refine, in keeping with the community-contributable lexicon.
## 0.9.52

### Phase 7 (part 4): seed sections from your CV on import
- Importing a CV now also fills your Experience, Education, Skills,
  Certifications and Languages sections, not just the personal fields, so you
  start with entries to review instead of a blank slate. Dates are pulled
  reliably; the title/organisation split is a sensible guess you review and
  correct in the sections manager, which opens straight after import. The CV
  reader learned to recognise more section headings (Experience even when it
  reads "Teaching and Volunteer Experience", plus Certifications, Languages, and
  Projects/Interests/References as boundaries) so sections no longer bleed into
  each other. Tested end to end against a real CV; the live NVDA speech check
  follows.
## 0.9.51

### Phase 7 (part 2): the sections UI (drill-down)
- Added the three-level sections manager, reachable from the NVDA+J menu as "My
  sections...". Level 1 lists Personal details plus your sections, with Open,
  Add section, Rename and Remove (Personal details cannot be renamed or
  removed). Level 2 lists the entries in a section, one summary line each
  ("Peer Mentor, Look UK, Sep 2023 to present"), with Add entry, Edit and
  Remove. Level 3 is a small form for one entry's fields; dates are free text so
  "present", a year alone, or "Sep 2023" all work. Every level is a short list
  or a small form, so a screen-reader user is never facing everything at once.
  A user-invented section (Publications, Volunteering) behaves exactly like the
  built-in ones. The entry summary and the field-selection logic are pure and
  unit-tested; the dialogs' live speech and keyboard feel are covered by the
  NVDA live tests. Still to come in Phase 7: filling repeating rows onto real
  forms, then the full live test pass, then docs.
## 0.9.50

### Phase 7 (part 1): the section data model
- The profile store can now hold sections (Experience, Education, Skills, or any
  you add) beside your flat personal fields. A section is a name plus rows, and
  each row is a free-form set of fields, so a section holds whatever a CV needs.
  You can add, rename and remove sections, and add, edit and remove rows within
  them. Sections are stored separately from the personal fields, so the fill
  path is unchanged, and profiles saved before this still load. Renaming or
  deleting a profile carries its sections with it. Suggested field templates are
  provided for the common sections (guidance, not enforced). This is the data
  layer; the drill-down UI (sections, then entries, then one entry's fields) and
  filling repeating rows on forms come next. Fully tested.
## 0.9.49

### Phase 6 (focused): attachments reminder in the review
- The review used to silently skip file uploads. Now a file input, or a control
  whose label reads like one (Upload CV, Attach Cover Letter, Select Files), is
  surfaced as an "attachment" row that reads "attach this yourself", so nothing
  important is dropped and you get a checklist of what to attach. Use "Go to" to
  jump to it and attach it yourself; Edit, Fill and Clear are blocked on these
  rows (with a message) so a file field can never receive a text paste, and the
  apply step refuses them as a backstop. Plain buttons and links are still
  skipped, so the review stays a clean list of real fields. The rest of the
  Phase 6 review-cleanup (region filtering, min-fields guard) was deliberately
  not built: the review is already clean and complete on real forms, so it would
  have been speculative. Attachment detection is tested.
## 0.9.48

### Phase 5: phone group (split the number across a dial-code and a number field)
- When a form has a separate country-code field alongside the phone field, the
  add-on now understands them as one group: it fills the dial code (e.g. +966,
  derived from your stored number) into the code field, and the national number
  (569277208) into the phone field, instead of leaving the code field to you and
  putting the whole international number in both. A form with only a phone field
  still gets the full +966569277208. The split only happens for an explicitly
  international number (one starting with +); a plain national number is never
  guessed at, and North American +1 numbers keep their area code in the number.
  Names and addresses are left per-field, since your forms label each part and a
  positional group parser would be speculative there. Splitter tested; the fill
  wiring is confirmed by simulation and awaits a live-form check.
## 0.9.47

### Documentation refresh (no code change)
- Brought the docs in line with the add-on as it now is: removed the stale
  "optional AI" description (the AI was removed in 0.9.37, the tool is fully
  deterministic, no network, no keys), updated the field-language count from 9
  to 13 with the plan to reach the country data's 24, and refreshed
  PROJECT_STATE with the Phase 4 status and the remaining next steps (the last
  14 languages, the CV reader to the same set, and passport name sub-fields).
## 0.9.46

### Phase 4 (part 6): passport fields
- Added passport field recognition (English and Arabic for now): passport
  number, name on passport, issuing country / place of issue, issue date and
  expiry date. All show "needs you", nothing sensitive is stored. "Issuing
  Country" and "Country of Issue" correctly win over the plain country field,
  and Country, Nationality and Date of Birth are unaffected. The passport-
  specific given/family name sub-fields are deliberately left for when a real
  form shows them, since they need a compound rule the simple matcher can't
  express cleanly. Tested.
## 0.9.45

### Phase 4 (part 5): more languages, starting with the big ones
- The field matcher now reads field labels in Chinese, Japanese, Korean and
  Russian for the core fields (name parts, email, phone, address, city,
  country, postcode, date of birth, nationality), on the way to matching the
  same language set as the country data. To do this the matcher learned the
  same script-aware trick the country list uses: Chinese and Japanese have no
  spaces between words, so they match by substring, while spaced scripts stay
  whole-word. Existing languages are unchanged. Tested, including the cases
  where a short character sits inside a longer word.
## 0.9.44

### Phase 4 (part 4): phone group and organisation
- Widened the phone matching so mobile, cell, home and work phone variants all
  fill your one phone number, while the separate dial-code and extension fields
  stay "needs you" for you to set. Added a company / employer concept, matched
  in nine languages, which shows "needs you" for now (employer belongs to the
  experience section, added later). "Employment Status" and "Business Unit" are
  deliberately left unmatched so nothing is mis-filled. Tested.
## 0.9.43

### Phase 4 (part 3): import name and address field types (multilingual)
- Added the name and address field types from the browser field dictionary,
  with non-English phrases so they work on global forms. New: address line 2
  and 3, house/building number, state/province/region, district/neighbourhood,
  salutation and name suffix. "Address Line 2" no longer grabs line 1's value,
  it now says "needs you". None of these hold a stored value yet, so they show
  "needs you" until a profile has them. Two collisions were deliberately
  avoided: "Job Title" and "Business Unit" stay unmatched. Existing name,
  street, city and country matching is unchanged. Tested.
## 0.9.42

### Phase 4 (part 2): whole-word matching (the anchoring change)
- Field labels are now matched on whole-word boundaries instead of "appears
  anywhere inside". A short concept word like "state" no longer matches inside
  "real estate", and "name" no longer matches inside "username", so a whole
  class of accidental wrong-matches is gone. The no-separator forms that ATS
  put in field names ("firstname", "emailaddress") still match, via a
  concatenated-token path. This is the structural groundwork for importing the
  browser field dictionary. All existing matches were checked and unchanged.
## 0.9.41

### Phase 4 (part 1): stop dial-code and extension fields grabbing country / phone
- A phone dial-code field ("Country Code", "Country / Territory Phone Code") no
  longer matches "country" and fill your country name into it. On a live Almarai
  application this was filling "Saudi Arabia" into the dial-code box, an invalid
  value that helped the save fail. And a "Phone Extension" field no longer grabs
  your full phone number. Both now resolve to their own concepts with no stored
  value, so they show "needs you" and you set them yourself. The real Country,
  Country of Residence, and Phone Number fields still fill correctly. Tested.
## 0.9.40

### Phase 3 (part 2): stop a focused field leaking in as a fake dropdown option
- When a chooser (like "How Did You Hear About Us?") had no readable options, the
  add-on fell back to the field the page highlighted, but that fallback could hand
  back whatever field simply held focus at the time (an edit box such as "Given
  Name(s) - Latin Script"), and offered it as a choice. It now accepts that
  fallback only when the target is genuinely a list option, so a focused edit box
  or button can no longer leak in. The chooser offers a clean type box instead.
## 0.9.39

### Phase 3 (part 1): stop "name" fields grabbing your full name
- Father's-name fields (both "Arabic Father's Name" and "Father's Name - Latin
  Script"), Middle Name, and the "I have a preferred name" checkbox no longer
  get matched to your full name off the bare word "name". They now resolve to
  their own concepts, which hold no saved value, so the review shows them as
  "needs you" for you to handle, instead of "will fill Mohammed Alomrani". The
  given-name and family-name fields still fill correctly. Locked in with a test.
## 0.9.38

### Phase 2: the review shows the real field label and what it will fill
- The Review fields list and the Scan report now show each field's real label
  from the page (for example "Arabic Father's Name") instead of the add-on's
  internal concept name (which was showing indistinguishable duplicates like
  "full name, first name, last name"). The review also shows what it would put
  in each field, e.g. "Arabic Father's Name: will fill Mohammed", or
  "empty, needs you" when it has nothing to fill. So you can now hear both which
  field a row is and what it is about to do, and catch a wrong fill before it
  happens. Label reading and matching were already correct; only the review's
  presentation of them changed.
## 0.9.37

### Phase 1: remove the AI/vision feature (deterministic-only from here)
- Removed the opt-in AI vision fallback entirely: the vision provider module, the
  screen-capture helper, the Vision settings dialog and its API-key field, the
  disagreement log, and the dead-end hook that called vision during a fill. The
  add-on is now fully deterministic, with no AI, no API keys, and no network
  calls. Smaller and simpler, and nothing that read or filled fields changed:
  detection, matching, the review, and filling all behave exactly as before,
  minus the vision path. (141 tests pass; the drop from before is only the
  removed vision tests.)
## 0.9.36

### Two-layer diagnostic for unreadable menus (object tree + display model)
- When a menu opens but its options still can't be read, the add-on now dumps, to
  the log, what BOTH reading layers see while the menu is still open: the object
  tree (a flat walk of every descendant and its role, not just list items) and the
  display model (the rendered screen text, the same layer flat/screen review uses,
  which catches content not exposed as child objects). Covers the focus, its
  parent, and the foreground, since menus often portal far from the field. This
  tells us definitively which layer Workday's options live in. Read-only: no keys,
  no mouse; it only reads and logs.
## 0.9.35

### Poll for async prompts to settle (Workday open-then-read)
- When a custom combobox is opened to read its options, the add-on now polls a few
  times as the list renders, instead of reading once and giving up. Workday's
  prompt opens an empty shell first and fills its options a moment later (it takes
  a beat to settle on expanded), so a single read missed them. It now opens with
  Down / Alt+Down, waits for the options to appear, then reads them. It never
  sends Enter to open (that would commit a value) and never touches the mouse, so
  it cannot select anything; it only reads, then Escape closes the list unchanged.
## 0.9.34

### Stop the stray-option leak on unreadable prompts
- When a field's options genuinely can't be read (as on Workday's "How did you
  hear" prompt, which exposes no aria-controls and no aria-activedescendant), the
  add-on no longer falls back to a blind document-wide search that grabbed an
  unrelated value from elsewhere on the page (the "Saudi Arabia (+966)" leak from
  the phone field). It now offers an honest type-a-value box so you can search the
  field yourself, rather than presenting a wrong option. Correctly built widgets
  are unaffected: their options are still read via aria-controls.
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
