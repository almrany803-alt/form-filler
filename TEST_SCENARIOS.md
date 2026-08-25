# TEST_SCENARIOS: stories for each feature

Beta-tester "stories" for the add-on, framed as James Whittaker's exploratory
testing tours (Guidebook = follow instructions; Intellectual = untypical input;
FedEx = follow the data through storage incl. right-to-left; Rained-Out = cancel
and check after-effects; Antisocial = act against the app's logic incl.
injection; Obsessive-Compulsive = repeat an action; Landmark = hit each feature
in order). Status: [done] verified, [new] added this pass, [todo] drafted, not
yet run.

The point is not to list the happy path. It is to walk each feature the way a
real, impatient, non-linear, multilingual user would, and see what breaks.

---

## Feature: review list (NVDA+J, R)

An accessible list over the form you are filling: every field, one per line, with
its current value or "empty, needs you". Arrow the list, Tab to the actions.

- [done] Guidebook: NVDA+J then R opens the list; it reads the live form and
  shows every field with its value. Proven on real NVDA (collected 6 fields on
  the clean form).
- [done] Fill from profile: on a field, pick a saved detail (the recognised one
  preselected); on close the value is written into the form field. Proven end to
  end (filled First name from the profile, landed in the page).
- [done] Edit (type a literal value) and Clear (empty it) are driven from the
  list on real NVDA (`beta-fill.yml`): Edit wrote "Edited Name" into the field,
  Clear emptied it. Go to is wired; the review-as-editor for choice controls is
  the next USP step.
- [todo] A setting to show only the gaps rather than every field (needs the
  settings panel).

## Feature: first run (no profile) - the clean-state journey

The journey I was NOT testing: a brand-new user with nothing saved. Both bugs the
user hit on first use live here.

- [done] Empty-state message is heard: with no profile, a fill puts up a critical
  DIALOG ("No details saved yet. Import a CV or enter your details first"), not a
  fleeting spoken line that the page's focus announcement cancels. The test
  asserts the message appears in the NVDA log's SPOKEN output, not just that a
  field stayed empty (`first-run.yml`).
- [done] Import from CV persists: the menu's Import creates and SAVES a named
  profile (like New profile) BEFORE the review dialog, so it sticks even if review
  is cancelled. Verified by reading the store back off disk (Jane Doe saved).
- Lesson: seeding a profile in every other test hid this whole path; and checking
  DOM values never checks what the user HEARS. Test from empty, and assert on
  speech.

## Feature: the add-on menu (NVDA+J)

- [done] Guidebook: NVDA+J then A fills the whole form; NVDA+J then F fills the
  focused field. Proven on real NVDA through the layer (the letter wins over
  browse-mode quick-nav, since global plugins resolve first).
- [done] Obsessive-Compulsive / wrong-turn: the tabbing story caught a stale
  layer-timer race, a letter falling through as a keystroke; fixed with a
  generation-guarded timeout.
- [todo] NVDA+J then D opens the details dialog (reachable; add a story).
- [done] Antisocial: NVDA+J then an unmapped or random key closes the layer and
  passes through cleanly; a normal fill still works after (`fill_abuse.mjs` now
  drives every command through the layer).

## Feature: My details dialog

- [done] Guidebook: open by keyboard, tab through, type each field, save; the
  encrypted profile on disk holds exactly what was typed.
- [done] FedEx (round-trip, right-to-left, special chars): enter an Arabic name
  (محمد), an apostrophe-and-CJK surname (O'Brien-李), save, and confirm the
  profile round-trips them byte-for-byte. Data must survive storage unmangled.
- [done] Rained-Out (cancel): with details already saved, open the dialog, change
  a field, then cancel (Escape). The saved profile must be untouched.
- [done] Prior-version (reopen + edit): save, reopen (fields should prepopulate),
  change one field, save again; only that field changes, the rest persist.
- [todo] Intellectual (extremes): a 5,000-character address; a name that is only
  spaces; every field at maximum length. Save must not truncate silently or
  hang.
- [todo] Antisocial / crime-spree (injection): paste `'; DROP TABLE --` and
  `<script>` into fields; they must be stored and reloaded as literal text, never
  interpreted.
- [todo] Couch-Potato (defaults): save with only name and email filled, the rest
  blank; the blanks stay blank and the fill later skips them.
- [todo] Obsessive-Compulsive: open and cancel the dialog ten times rapidly; no
  leak, no crash, profile unchanged.

## Feature: whole-form fill (NVDA+J then A)

- [done] Guidebook: labelled form, one press, all identifiable fields fill, a
  spoken summary names what was left.
- [done] FedEx: values actually land in the real DOM, not just announced.
- [done] Obsessive-Compulsive: five rapid presses in a row; no corruption (the
  fail-safe focus check skips rather than double-pastes).
- [done] Antisocial / wrong-turn: press the key with focus on a non-editable
  element; it declines gracefully.
- [done] Mangled parse (do not clobber): when a field already holds a value (an
  ATS auto-parse often drops a WRONG one in), fill leaves it untouched, still
  fills the empty fields, logs the existing value, and the summary says how many
  already had values so you open Review fields to check them. Proven on real
  NVDA; the review list's Fill from profile is the fix path.
- [todo] Intellectual: a form with 60+ fields; performance and completeness.
- [todo] Antisocial: press fill on a page mid-load, before fields are ready.

## Feature: single-field fill (NVDA+J then F) + tabbing

- [done] Landmark: tab from field to field, fill each individually.
- [done] Guidebook: fill the focused field.
- [done] No dead ends: on a field it cannot fill from the profile, Fill opens the
  right accessible editor instead of "over to you", Yes/No for a checkbox, an
  options chooser for a dropdown, radio choices, a date picker, a type box for
  text, and writes the choice back. Proven by speech on the live Monzo consent
  checkbox (Fill opens a Yes/No chooser). Judge by what NVDA speaks, not the DOM.
- [todo] Wrong-turn: fill a field, tab backwards, fill it again; no duplication.

## Feature: applicant-style live testing (judge by speech)

- [done] The live harness inspects the page source first, lands on each field
  type the way a user tabs onto it, presses the add-on command, and asserts only
  on what NVDA speaks. It never reads the DOM as proof and never submits.
- Rule of thumb baked in: if a blind applicant could not perceive it, it is not
  proof. The add-on never moves or clicks the mouse; every control is opened by
  keyboard after confirming focus.

## Feature: field identification (multilingual + messy)

- [done] Landmark: labelled fields in English map correctly.
- [done] FedEx / localization: placeholder-only, aria-label-only, and Arabic
  right-to-left labels all identify; name-only via html-input-name identifies.
- [done] Couch-Potato: unlabelled, label-not-associated, native select, custom
  combobox, date picker are all correctly left alone.
- [done] Localization breadth, grounded in the accessibility research: a form with
  French and German labels (identified by label alone) alongside inaccessible
  ATS-style fields (no visible label, identified by html attributes) and a bare
  field with nothing to go on. On real NVDA the labelled and tagged fields filled;
  the bare field was declined. Matcher identifies labels in all 13 languages (growing to the country data's 24).

## Feature: multi-section applications

- [done] Landmark: fill step 1, press Next, fill step 2.
- [todo] Wrong-turn: press Next before filling, fill step 2, go Back, check step 1.

## Feature: profiles as versions (in progress)

Design: several profiles, each a version (English, Arabic, a teaching CV). One
level. Switching swaps the whole detail set. Language is just a tag we pick a
version by. Import asks before it changes anything you already saved.

- [done] Store foundation: several named profiles coexist, switching the active
  one swaps the whole detail set, each keeps its own fields, editing one leaves
  the other, renaming keeps it active, and it all round-trips through save and
  load (English and Arabic together).
- [done] Bug caught: every store shared one profiles dict (a shallow copy of a
  module default), so two stores bled into each other. Fixed: each store gets
  its own fresh data.
- [done] Store: create, switch, edit, rename, delete (re-points active), all
  round-tripped and tested. Dialog import+save through the selected version is
  proven on real NVDA.
- [done] Drive New profile and Delete by keyboard on real NVDA: create a second
  version (Teaching), save, both exist with the new one active; delete the active
  version, save, only the other remains and is active (`profile-crud.yml`).
- [todo] Import into the chosen version, and where the CV would change a value
  you already have, ask before applying (per field or all).
- [todo] Fill picks the version by the form's language, or you choose.

## Feature: profile store / persistence

- [done] FedEx: DPAPI encrypt on save, decrypt on load, as the same user.
- [done] FedEx: non-ASCII and RTL values survive the encrypt/decrypt round-trip.
- [todo] Antisocial: a corrupted profile.dat on disk; load fails cleanly, the
  add-on still starts. (Covered in spirit by test_adversarial.py.)

## Feature: robustness / the "seedy district"

- [done] Saboteur / Antisocial: fire the keys in hostile contexts, hammer them,
  press random unbound combos; a normal fill still works and no uncaught error
  is logged (`fill_abuse.mjs`).
- [done] Crime-spree (unit level): hostile/malformed input to every brain module
  (`test_adversarial.py`), nothing crashes.

## Feature: the test harness itself (audit before you test)

The tests are code too, and they have had their own bugs. Recording them so the
lessons are not re-learned.

- [done] False green caught: a failing test was masked by a passing one after it
  in the same step, and the run went green. Each test now fails the run on its
  own exit code.
- [done] Cold-start flake: the very first fill right after NVDA and Chrome start
  intermittently missed. A `warmup.mjs` run now absorbs the cold start so the
  first real test is never the cold one.
- [done] Unicode print crash: the Arabic round-trip check first "failed" only
  because printing Arabic to the Windows console threw, before it ever compared;
  the check now writes UTF-8. The data had survived; the harness had not.
- [done] Untruncated logs: the CI console truncated the add-on's log lines, so the
  full NVDA log is uploaded as an artifact and read from there.

## Feature: choice controls (dropdowns, radios, checkboxes)

Grounded in the real ATS research (SuccessFactors, Taleo, Workday, Greenhouse,
Lever, Jadarat). The spine: act on the target object's accessibility action,
verify against the LIVE IA2 value or state (not NVDA's cached copy).

- [done] Native dropdown, exact match: focus a Country select, fill, it lands on
  United Kingdom; verified against the live value (`select-test.yml`).
- [done] Native dropdown, locale alias: a French form listing Royaume-Uni is set
  from the English value "United Kingdom" via the country aliases.
- [done] Native dropdown, decline: when the saved value is not among the options,
  the dropdown is left on its default, nothing wrong is picked.
- [done] Whole-form: a placeholder dropdown is set alongside text; a dropdown
  already on a real choice is left for review (do-not-clobber).
- [done] Bug caught by reading a green log: keyboard-arrow selection queued behind
  the running script and only applied after it returned (would misfire across
  several dropdowns). Switched to the option object's action. Then the verify read
  NVDA's cached value and reported a false mismatch; switched to a live IA2 read.
- [done] Radio group (native fieldset): the question "Are you authorised to work
  in Saudi Arabia?" is found from the group, matched to work authorisation, Yes is
  selected and confirmed via the live checked state (`radio-test.yml`).
- [done] Radio group (custom ARIA widget): the same on a div role=radiogroup with
  role=radio children; the object action drives the widget's own handler.
- [done] Checkbox: toggled to the wanted state and confirmed via the live state.
- [done] Whole-form over text + select + radio + checkbox together: all four set
  in one fill-all, with an honest summary ("Filled 4 of 4. Nothing left for you").
- [todo] Custom single-select combobox (button + listbox), multi-select, dates,
  and the async search-box combobox (location).
- [todo] The review list as an accessible editor for each of the above.

## Feature: nationality (Nitaqat / Saudi forms)

- [done] Nationality is identified distinctly from country in English, Arabic
  (الجنسية vs الدولة), and the other languages, and is a profile key
  (`test_nationality.py`). It is optional: blank means the addon does not fill it.
- [todo] On a real Saudi form, a nationality dropdown filled from the saved value.

## Feature: CV import

- [done] Guidebook (text and Word): open the dialog, press Import, pick a .txt
  or .docx CV, the fields populate for review, save; parsed details in the
  profile. Word is read with the standard library (zip+xml, no lxml).
- [done] FedEx (multilingual): English and Arabic CVs imported end to end on real
  NVDA (text and Word); name, email, phone parsed and saved, Arabic intact.
  Spanish and Polish mapping (two-part surnames, diacritics) is unit-tested.
- [done] Couch-Potato / layering, observed: importing a second CV overwrites only
  the fields the new CV provides and leaves the rest as they were. Deliberate for
  one person updating their own details; revisit if it surprises users.
- [done] PDF import via bundled PyMuPDF: an English and a Spanish PDF parsed and
  saved end to end on real NVDA. PyMuPDF is a self-contained compiled library
  (the approach the working NVDA PDF add-on uses), so it fits NVDA's Python where
  pure-Python pypdf could not.
- [done] Chain import to fill: import a Word CV, then fill a real form from it,
  end to end on real NVDA (Jane Doe imported, then filled into the form).
- [todo] Antisocial: a password-protected PDF; an image-only (scanned) PDF; a CV
  with no recognisable sections; a 40-page CV. Each must fail or degrade cleanly.

## Feature: the review editor as an accessible editor (the USP)

[done] Methodical navigator, accessible form: open the review list, change the
name via the text editor, the country via the chooser (arrow to United Kingdom),
and the right-to-work checkbox via Yes/No; confirm each landed in the DOM and
each announced in the debug speech log. (review-journey.yml, fill_review_journey)
[done] Same journey on an INACCESSIBLE form (no labels, bare select): the review
still enumerates the fields, opens the closed dropdown to read its real options,
and the three editors still write back.
[todo] Drive the date (three dropdowns) and multi-check editors by keyboard.
[todo] Backtracker: fill, go back, change an answer through the review editor.
