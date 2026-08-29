# PROJECT_STATE: Job Form Filler (NVDA add-on)

A living snapshot of the project, written so a future chat, or another person,
can pick it up cold. If you are that reader: start here, then open the files it
points to. Last updated at version 0.9.73. Phases 5 (phone group), 6
(attachments), 7 (sections and CV seeding) and the language finish (27
languages) are in; the repeating-row NVDA fill is parked.

Repo: github.com/almrany803-alt/form-filler  (GPL v2, open source)

---

## 1. What this is, and who it is for

An NVDA add-on (a Python global plugin) that fills job application forms from
your saved details, in many languages, with spoken and braille review. It is
built for screen reader users. It identifies each field, fills the ones it is
sure of, tells you plainly what it filled and what it left, and never submits a
form.

Author and primary user: Mohammed, a blind developer in Bristol, UK, on
NVDA 2026.1.1 with a QBraille XL. The tool exists because job applications waste
time re-typing the same standard fields, and because the awkward, badly-labelled
fields that sighted applicants skim past are exactly the ones a screen reader
user loses time on.

### Status at a glance

Working and proven on real hardware (see section 3):
- One key, NVDA+J, opens a native menu you can arrow through (NVDA announces
  each item) or drive by access key: Fill this field, Fill all fields, Profile
  (a submenu to switch, create, delete versions), Review fields, Import from CV,
  Enter your details. Fills and the review list act on the page: focus and
  foreground are captured before the menu opens and restored before acting.
- Review fields (NVDA+J, R), the USP: an accessible list over the current form,
  every field with its value or "empty, needs you". Edit is kind-aware: each
  field opens the right accessible control, a text box, a chooser you arrow
  through for a dropdown or radio group, Yes/No for a checkbox, a multi-check
  list, or three dropdowns for a date. A closed dropdown is opened briefly to
  read its real options, so the chooser works even when the page exposes none.
  Writeback routes each kind to its proven primitive, not a blind paste. Proven
  end to end on real NVDA on an accessible form AND an inaccessible one (text,
  chooser, yes/no); the date and multi editors are built and logic-proven, not
  yet driven by the NVDA journey.
- Fill this field (NVDA+J, F) always completes the field. When the add-on knows
  the answer it fills it; otherwise it opens the same accessible editor the
  review uses, right on the field, instead of handing it back. Review and Fill
  share one editor (dialogs.edit_field), so both behave identically. Proven by
  speech on the live Monzo consent checkbox: Fill opens a Yes/No chooser where it
  used to say "over to you".
- Encrypted profile stored on the user's own machine (Windows DPAPI).
- A "My details" form in the NVDA Tools menu to enter and edit your details.
- Multilingual field identification (27 languages: English plus the 26 the
  country data uses), matched on whole-word boundaries and script-aware for
  Chinese and Japanese. The field matcher and the country data now share the
  same language set.
- Country and nationality match through a bundled dataset of all 250 countries
  in 24 languages plus demonyms and phone codes, so "Saudi" fills السعودية on an
  Arabic form and a French form's Royaume-Uni matches. Both are chosen from a
  type-ahead dropdown in the profile, not typed. On CV import the country is
  detected (any of the 24 languages, or the phone's calling code) and pre-filled.
- Date of birth is three accessible dropdowns (day, month, year) in both the
  profile dialog and the review editor, sharing one date helper set.
- Fills native dropdowns (dataset-aware across 24 languages), radio groups,
  checkboxes, multi-selects, and dates (native segmented, UK/US text, custom
  picker, and SAP UI5 date inputs recognised by placeholder + roledescription);
  verifies each against the live accessibility state and never confirms a
  placeholder value (the STC Country false-confirm fix). Custom comboboxes
  (react-select) are opened by keyboard Down on the focused field and their
  options read from the live page; the write commits with Enter and verifies.
  NO mouse is ever used: every control is opened by keyboard, focus-verified.
- Correctly declines fields it cannot identify; declines the controls not yet
  built rather than guessing.
- Handles multi-section applications: fill a section, press Next, fill the next.
- Optional nationality field (Nitaqat on Saudi forms), split cleanly from country.

Working, and proven end to end on real NVDA:
- Profiles are versions: several named profiles, each a version (English,
  Arabic, teaching). The dialog has a selector to pick one, create new, and
  delete. Switching swaps the whole detail set. Store logic tested; import and
  save through the dialog proven in `cv-import.yml`.
- CV import (text, Word, PDF): pick a CV, the fields populate for review, save;
  tested in English and Arabic, all three formats, on real NVDA (`cv-import.yml`).
  Text and Word use the standard library; PDF uses bundled PyMuPDF.

Working and proven end to end on real NVDA (control filling):
- Native <select> dropdowns: read the options, choose the best match (locale
  aware via country aliases), select the option object, verify against the live
  IA2 value. Single-field and whole-form (`select-test.yml`).
- Radio groups and checkboxes: find the group question, match it to a saved
  detail, select the option or toggle the box, verify the live checked state.
  Native and custom ARIA widgets, single-field and whole-form (`radio-test.yml`).

Still to build (grounded in CONTROLS_RESEARCH, section 11):
- The custom single-select combobox (button + listbox), the dominant modern ATS
  control, is the main remaining control.
- The post-CV-attach audit: audit.py exists and is tested, but is not yet wired
  or fed a rich profile. Read a portal's repeating rows and flag duplicates and
  mis-maps as a list, like the review.
- The rich profile: the CV's real sections (summary, education, experience,
  skills, certifications, languages, projects, references), with sections the
  user can add or remove.
- The testing personas battery. The review journey is the first persona, the
  methodical navigator; next come the quick-nav jumper, multilingual applicant,
  many-versions applicant, backtracker, stuck applicant, re-reader, browse-mode
  reader.
- The date and multi editors are built; driving them through the NVDA review
  journey (many precise keystrokes) is a clean follow-up.

DATE ENTRY, DONE (user decision): the profile dialog and the review editor both
enter a date via three accessible dropdowns (day, month, year), not a typed box.
The addon stores ISO internally and writes to each form field with the tested
segment/text/custom-picker logic.

---

## Combobox and ATS roadmap (phased)

Grounded in reading browser autofill (Firefox reference), the open-source job
autofillers (ApplyAI, laynef/AI-Job-Autofill, andrewmillercode/Autofill-Jobs,
berellevy/job_app_filler) and a practitioner breakdown of Workday's widgets. The
add-on's own architecture (keyboard-driven fill, a structural fingerprint
database, deterministic at runtime with vision only for discovery) matches what
those tools converged on, so this is refinement, not a rewrite.

- Phase 1 - DONE. Strengthen the generic dropdown engine, which helps every
  platform: wait on the control's busy/loading signal for async options; match
  by exact/synonym and hand back on ambiguity rather than pick a wrong option;
  fill multi-selects one value at a time, coping with the chip style that
  redraws; normalise values (whitespace/control chars, line breaks kept) before
  typing. Verify-back stays permissive on purpose because the wrong-option trap
  is prevented at match time. (0.9.65-0.9.68.)
- Phase 2 - DONE. Detect the platform across many ATS (Workday, Greenhouse,
  Lever, Ashby, SmartRecruiters, iCIMS, Taleo, BambooHR, Workable,
  SuccessFactors, plus Jobvite and Recruitee) by URL host and DOM markers, in a
  pure, unit-tested module (core/platforms.py), so the fingerprint database can
  be ATS-aware. The key that unlocks Phase 3. (0.9.69.)
- Phase 3 - IN PROGRESS. Grow the fingerprint database. Reality check: the easy
  platforms (Lever, Greenhouse) already pass on heuristics, so the database
  matters most for the hard, login-walled ones (Workday, iCIMS, Taleo) that CI
  cannot reach. So this phase made the add-on FINGERPRINT-READY: every field-read
  log now carries the full signature (id, role, placeholder, class, haspopup,
  states), so one real run on a hard platform yields ready-to-add entries. Added
  a Greenhouse react-select entry built from a real live log, platform-gated and
  unit-tested. Hard-platform entries grow from real logs and real use. (0.9.70.)
  Audit + source review (0.9.71): read the open-source autofillers' code
  (ApplyAI, laynef, andrewmillercode, berellevy, jasonchen270). Confirmed the
  fingerprint approach matches what they do, and that their key Workday signal,
  data-automation-id, is DOM-only and NOT exposed to NVDA, so we correctly key on
  Workday's name--name id pattern (the accessibility-layer equivalent). The
  Greenhouse entry was re-verified against a real live-form country-combobox
  signature and locked with a test. The matcher fails closed on unknown keys.
- Phase 4 - DONE. Re-read the form after an answer reveals hidden fields and
  fill the newly-shown ones that match stored values. Additive pass (like the
  repeating-section pass), bounded, never clobbers, leaves radios/multi/date for
  the user. Proven on a live conditional-reveal test (choosing Yes reveals a City
  field, which then fills). Widget-type coverage judged complete for now (the
  existing kinds cover the researched Workday widgets; file upload can't be
  auto-attached by an accessibility tool). (0.9.72.)
- Phase 5 - DONE. Opt-in, offline discovery: the Scan action now also writes a
  discovery file listing custom widgets no fingerprint covers yet, each with a
  suggested fingerprint stub (kind left as REVIEW - we never guess how to fill an
  unknown widget). Pure logic in core/discovery.py, unit-tested; read-only, local,
  and only inside the user-triggered Scan. This is how the hard-platform database
  grows from real use. (0.9.73.)

## 2. How we work: the beta-tester approach

This is the heart of the project, not a footnote. The rule, carried over from
the Zul Simulator project, is: **be the beta tester, not the author.**

- **Test the reachable feature end to end, not the internal function.** A unit
  test that a function returns the right dict proves nothing about whether a
  blind user, pressing a key in a real browser, gets their name into the box.
  So the real tests drive real NVDA in a real browser and check what actually
  lands in the page and what NVDA actually says.

- **Audit before you test.** Read the code back and reason about what could go
  wrong before writing the test. A test only ever covers the cases someone
  thought of. A green suite that never considered the failure mode is a false
  comfort.

- **Do not trust the green tick. Read the log.** More than once the workflow
  went green while a test was actually failing (a failing test masked by a
  passing one after it), or a value said "filled" while the box was empty. Every
  "pass" here is confirmed by reading the real value back, not by trusting the
  status.

- **Fail safe, not silently.** When focus timing is uncertain, the add-on
  skips a field and leaves it for the user rather than pasting into the wrong
  one. Leaving a field is a minor loss; corrupting a different field is a real
  harm.

- **Be adversarial and creative.** Do not only walk the happy path. Tab through
  menus like a user, press the wrong keys, fire commands in the wrong context,
  run several sessions at once to stress timing, throw malformed input at the
  parser. Make scenarios a real, impatient, non-linear user would produce.

- **Be explicit about what can and cannot be verified where.** The Linux
  sandbox proves the pure-Python "brain". Only real Windows + real NVDA proves
  the fill and the dialog. Both are now driven in CI; the one step still not
  automated is navigating the actual NVDA Tools menu to open the dialog.

**The questions that keep finding things** (carried from Zul). Before saying a
feature works, ask what a person on a screen reader would actually do, not what
the code does: can the user reach this, or only the code? If I do it twice, is
anybody told? If the data goes to storage and comes back, does it arrive whole,
including in Arabic and other scripts? What does the user HEAR when it goes
wrong, a sentence or a key name? Does it survive a save, a reload, a cancel?
What if I leave it empty, set it to nothing, or half-fill it?

**Count before you claim.** Never say "tested end to end" without counting what
was actually driven. Say the number.

**Testing is a routine, not a reminder.** Every new feature, or change to one, is
tested this way, has its stories added to `TEST_SCENARIOS.md`, and has its result
recorded here, as a step in the work rather than something done when asked. If a
change touches nothing a user can reach, that is a decision recorded, not a step
skipped.

Bugs this approach has already caught, that a happy-path suite would have
missed: a name-collision crash (see gotchas), a stale-field-position bug that
lost half the form, a paste-before-focus bug that piled values into one box
under load, a false green in the harness itself, and the discovery that Chrome
exposes the useful attributes under different keys than assumed.

---

## 3. What is verified, and how

Two independent sources of truth.

**The user's own machine** (NVDA 2026.1.1, real Chrome): single-field and
whole-form fill work; values actually land in the fields; the bespoke question
box and unlabelled fields are correctly declined; the spoken summary is heard.
Confirmed by the user reading fields back and pasting NVDA logs.

**GitHub Windows CI**, which the assistant drives itself and reads via the
GitHub API. On a real Windows runner with NVDA 2026.1.1 and real Chrome:
- The add-on loads with no error (`nvda-load.yml`).
- A beta-tester fill test (`beta-fill.yml`) opens the form in Chrome, presses
  the add-on's key, and checks what actually landed. A warm-up run first absorbs
  the NVDA+Chrome cold start (see gotchas). It covers five scenarios, all
  passing (real-NVDA control tests add dropdown, radio, and checkbox coverage):
  - clean form (labelled fields fill),
  - messy form (placeholder-only, aria-label, Arabic RTL label fill; unlabelled,
    label-not-associated, native select, custom combobox, date picker all
    correctly left),
  - user journey A: tab from field to field, filling each with the single-field
    key,
  - user journey B: a two-step form, filling each step and pressing Next,
  - abuse / survival: fire the keys in the wrong context, hammer them, press
    random unbound combos, then prove a normal fill still works and that no
    uncaught error was logged.

The pure-Python brain has 98 checks that run in the sandbox and on Linux CI
(`tests.yml`) on every push, including an adversarial "sabotage" suite
(`test_adversarial.py`) that throws malformed and hostile input at every module
and asserts nothing crashes.

Also verified in CI (`dialog-test.yml`): the "My details" dialog driven entirely
by keyboard, open it, tab through the fields typing each, press Enter to save,
then read the encrypted profile back off disk and confirm it holds exactly what
was typed. The dialog is opened via a test-bound key; navigating the actual NVDA
Tools menu to open it is the one interaction step not yet automated (fiddly to
drive blind, but not impossible). Further dialog "stories" are verified in
`dialog-scenarios.yml`: Cancel does not save (Rained-Out tour), reopen-and-edit
persists only the changed field (Prior-version tour), and an Arabic given name
plus an apostrophe/CJK surname round-trip through save and reload byte-for-byte
(FedEx tour).

---

## 4. Architecture and key decisions

- **A pure NVDA add-on, not a browser extension.** The add-on reads the
  accessibility tree across all browsers and native apps, needs no web store,
  and works for non-Chrome users. (An earlier Chrome-extension idea was dropped.)

- **Identify-and-fill, fully deterministic.** The user stays in control and
  submits themselves. The AI/vision rungs were removed entirely in 0.9.37: no
  AI, no network, no API keys. Field matching is a dictionary-and-rules job (the
  same approach browsers and the main job-autofill tools use); the only thing an
  "AI autofill" tool uses a model for is writing open-ended custom answers, which
  this tool leaves to the user.

- **Read the field's real HTML attributes from the accessibility tree.** Chrome
  exposes, in its IA2 object attributes: `html-input-name` (the HTML name, e.g.
  "given-name", "email", "tel"), `text-input-type` (the input type), `name-from`
  (how the label was derived: a real label vs a placeholder vs aria-label), and
  `xml-roles` (the ARIA role). We read these. ISimpleDOM was investigated as a
  richer source but returned empty on Chrome, so the IA2 keys are the source of
  truth. A label that came only from a placeholder is demoted to a "guess".

- **Fill by clipboard paste** (copy value, send Ctrl+V) so the page's own input
  events fire and React/Workday state updates. Whole-form fill resolves every
  field object UP FRONT (before any paste, because pasting mutates the page and
  invalidates positions not yet used), then for each field confirms focus
  actually landed on it before pasting, and skips safely if not.

- **Multilingual, 27 languages** (en plus the country data's 26: es fr de it pt
  pl nl ar zh ja ko ru tr id fa ur cs hu fi sv hr sr sk et cy br). The autocomplete/HTML-name signal
  is language-independent; the keyword lexicon is extensible per language; accent
  and stroke folding normalises diacritics (including Polish's non-decomposing
  ł); matching is whole-word (anchored), and script-aware for Chinese and
  Japanese, which have no word spaces and so match by substring, the same trick
  the country matcher uses.

- **Store the profile as plain JSON.** It holds ordinary contact details, not
  secrets, and the CV they came from is already on the device in plain form, so
  encryption buys little here. The pluggable crypto slot stays for later, if the
  tool ever handles anything sensitive.

- **Never guess.** Fields the matcher cannot confidently identify are declined
  and reported ("2 need you: ..."), never filled with a wrong value.

- **The control-filling spine: act on the object, verify the live state.**
  Selecting a dropdown option, a radio, or a checkbox is done by calling the
  target object's own accessibility action (doAction), which applies
  immediately. Keyboard-driven selection is avoided inside the whole-form loop
  because injected keys queue behind the running script and only take effect
  after it returns (they broke verification and would misfire across multiple
  controls). Verification reads the LIVE IA2 value or state via a raw COM call
  (accValue / accState), never NVDA's cached obj.value or obj.states, which lag
  the change and caused false mismatches. Both lessons were caught by reading
  the log while a test was green.

- **Radios are matched by their group, not the single button.** A radio's own
  label is the option ("Yes"), so the addon finds the group container, reads the
  question from it, matches that, reads the sibling options, and selects the one
  that matches the saved value. Radio groups are deduped in the whole-form pass.

- **Dropdowns keep a real prior selection.** A select always has a value, often
  a placeholder ("Choose..."). The whole-form fill sets a dropdown only when it
  is still on a placeholder, and leaves a real prior choice for review, the same
  do-not-clobber rule as pre-filled text.

---

## 5. Repo layout

- `addon/globalPlugins/jobFormFiller/__init__.py` — the global plugin: the two
  fill commands, the field reader (`_descriptor_from_object`, reads the IA2
  keys), the whole-form walk with the fail-safe focus check, the Tools-menu item,
  heavy "JFF" logging.
- `addon/globalPlugins/jobFormFiller/dialogs.py` — the "My details" wx dialog
  and save flow. Named `dialogs`, NOT `gui`, on purpose (see gotchas).
- `addon/globalPlugins/jobFormFiller/core/` — the pure-Python brain, no NVDA
  imports, fully testable: `matcher.py` (multilingual field matcher, 9-language
  lexicon), `controls.py` (classify a control, choose an option, verify),
  `announce.py` (spoken summaries + the audit summary), `profile.py` (encrypted
  ProfileStore + DPAPI), `cvparse.py` (extract text from docx/pdf/txt + parse CV
  sections), `audit.py` (duplicate/extra/mismatch detector).
- `tests/` — 96 pure-Python checks (matcher, data, cv extract, audit, langs, and
  `test_adversarial.py` sabotage/hostile-input cases), all runnable without NVDA.
- `betatest/` — the real-NVDA-real-Chrome tests: `fill_test.mjs` (clean),
  `fill_messy.mjs` (messy stress), `fill_journey.mjs` (tabbing + multi-section),
  `fill_abuse.mjs` (abuse/survival), `warmup.mjs` (cold-start warm-up), the forms
  (`test_form.html`, `messy_form.html`, `multi_form.html`), `send_nvda_key.ps1`
  (injects NVDA+Shift+<key> at OS level), `seed_profile.py` (seeds an encrypted
  profile as the runner user).
- `.github/workflows/` — `tests.yml` (Linux, brain), `nvda-load.yml` (Windows,
  real NVDA load), `beta-fill.yml` (Windows, real Chrome fill), `dialog-test.yml`
  and `dialog-scenarios.yml`, `cv-import.yml` (Windows, the My details dialog and CV import driven by keyboard), `nvda-live.yml` (a guidepup
  scaffold, secondary).
- `build.py` — one command to package the `.nvda-addon` and print its SHA256.
- `buildVars.py` — the manifest source (name, version, NVDA version range).
- README, LICENSE (GPL v2), REPO_SETUP.md, setup-repo.ps1.

---

## 6. Build, install, test

Build the add-on:
```
python build.py            # -> jobFormFiller-<version>.nvda-addon, prints SHA256
```

Run the brain tests:
```
python -m unittest discover -s tests -p "test_*.py"
```

Install: press Enter on the `.nvda-addon`, let NVDA restart. Requires NVDA
2024.1+, tested on 2026.1.

First run: open NVDA menu, Tools, "Job Form Filler: My details", enter your
details, save. Then on any form press NVDA+Shift+A.

The live NVDA tests run on Windows (locally or in CI); see `betatest/` and the
workflows.

---

## 7. How the CI is driven

The assistant pushes to the repo and the workflows run on push. Workflow runs,
logs, and artifacts are read back via the GitHub REST API. `beta-fill.yml`
uploads the full NVDA log as an artifact so the real per-field detail can be
read untruncated. A fine-grained token scoped to this one repo (Contents +
Workflows) is used for pushing; it cannot trigger `workflow_dispatch` (that
needs the Actions permission), which is why the workflows run `on: push`.

---

## 8. Gotchas learned (hard-won, do not re-learn these)

- **Our `core` subpackage shadows NVDA's `core` module.** A bare `import core`
  or `core.callLater` binds to OUR package and fails. Use `wx.CallLater`.
- **The dialog module is `dialogs.py`, not `gui.py`,** to avoid shadowing
  NVDA's own `gui` module (same class of bug as `core`).
- **Resolve all form-field objects before pasting.** Pasting mutates the page
  and invalidates browse-mode positions not yet consumed, so the later fields
  resolve to the wrong nodes if you resolve them lazily.
- **setFocus is not synchronous.** Under load, a paste can fire before focus
  moves, piling values into one field. The fill now confirms the focused
  element's id matches the target before pasting, and skips safely otherwise.
- **Chrome hides the standard `autocomplete` token from IA2** but exposes
  `html-input-name` and `text-input-type`; read those. ISimpleDOM returned empty
  on Chrome.
- **In the test harness, every test must fail the run.** Chaining `node a; node
  b` lets a's failure hide behind b's success. Track exit codes explicitly.
- **Cold-start timing flake:** the very first fill right after NVDA+Chrome start
  can miss. Fixed by running `warmup.mjs` before the real tests, so the first
  real test is never the cold one. It is a harness timing issue, not the add-on.
- **NVDA ships a trimmed Python** (3.13, 64-bit as of 2026.1). Its frozen
  runtime omits stdlib modules it does not itself use (secrets, stringprep,
  xml.dom, ...), so pure-Python libraries that assume the full stdlib (pypdf)
  fail to import. The fix that works, and that other add-ons use: a self-contained
  COMPILED library. PDF uses bundled PyMuPDF (an abi3 win_amd64 wheel, forward
  compatible across 3.10+), which is C code and needs no stdlib extras. For .docx,
  a stdlib zip+xml reader is enough.
- **A popup menu steals page focus.** Opening a menu from NVDA's frame pulls
  focus off the web page, so a fill run straight after finds no document and the
  paste lands in the wrong window. Capture the page's focus object and foreground
  window before the menu, and restore the foreground and pass the saved focus to
  the fill, which runs after the menu closes. Also: a native menu stays open on a
  non-command key (unlike the old one-shot layer), so tests that fire junk keys
  must send Escape to close it.
- **Critical messages must be dialogs, not speech.** A spoken ui.message right
  after the menu closes is cancelled by the page's focus announcement (the "did
  not sound in time" bug). The whole-form summary dodges this with a 400ms delay;
  anything the user MUST act on (no details saved, a save/import failure) now uses
  a modal box (gui.messageBox) that cannot be cut off.
- **Test from the empty state, and assert on speech.** Every fill test seeded a
  profile, so the no-profile paths (empty-state message, import-from-scratch)
  never ran, and tests only checked DOM values, never what NVDA SPOKE. Two real
  bugs slipped through green CI. `first-run.yml` now starts with no profile and
  asserts the empty-state message against the NVDA log's spoken output.
- **Import from CV must persist like New profile.** The menu import used to open
  a prefilled dialog and rely on save-on-close; it now names, creates and saves
  the profile up front, then opens it for review.
- **ATS field names need splitting.** Real ATS name fields as camelCase
  ("firstName") or bracketed ("job_application[first_name]"). Without splitting
  camelCase, "name" substring-matches "firstname" and the field is mislabelled a
  full-name field. The normaliser now splits camelCase and treats brackets and
  dots as separators. Tested against Greenhouse, Workday, Taleo and iCIMS
  patterns ().
- **No shared mutable defaults.** The store built each instance's data with a
  shallow copy of a module-level default, so every store shared one profiles
  dict. Build fresh nested data per instance instead.
- **Layer timers must be generation-guarded.** The command layer opens on
  NVDA+J and closes on the next key or a timeout. A plain 4-second timeout let a
  stale timer from an earlier press close a freshly opened layer, so the command
  letter fell through as a keystroke ("f" typed into a field). Each opening now
  carries a generation number; only its own timer may close it.
- **PowerShell has no bash heredoc.** A `python - <<'PY'` block in a pwsh step
  is a parse error; put the Python in a file.

---

## 9. Roadmap (what is next, roughly in order)

Done and proven on real NVDA: the NVDA+J menu (navigable, announced), fill this
field / fill all fields, the kind-aware review editor (the USP: text, chooser
and yes/no editors on an accessible AND an inaccessible form, opening a closed
dropdown to read its options), native dropdowns / radios / checkboxes /
multi-select / dates, country and nationality via the bundled 24-language
dataset (the nationality demonym fix), country/nationality type-ahead dropdowns
and the three-dropdown date of birth, CV country detection, profiles as versions
(create/switch/delete), CV import (text, Word via stdlib, PDF via bundled
PyMuPDF) across its 9 CV section-heading languages (expanding with the CV
multilingual work), the import-to-fill chain, real ATS field
patterns (Greenhouse, Workday, Taleo, iCIMS) including the camelCase fix,
multi-section applications (fill, Next, fill), and the do-not-clobber behaviour
for a mangled ATS auto-parse.

Still to do:
1. Automate the remaining menu paths by keyboard in CI: the Profile submenu
   (switch/new/delete) and Enter your details. Import from CV IS now driven from
   the menu (first-run.yml); the other two are not yet.
2. Extend the review journey to drive the date (three dropdowns) and
   multi-check editors by keyboard (text, chooser and yes/no are done).
3. A settings panel, home for the review-list "show every field vs only the
   gaps" toggle, and the point to revisit whether the Tools-menu item still
   earns its place.
4. The custom single-select combobox (button + listbox) is the main remaining
   control. Native dropdowns, radios, checkboxes, multi-select and dates are
   DONE and proven on real NVDA.
5. Remembered answers for recurring bespoke questions (notice period, right to
   work), keyed to the question wording; and a "jump to the next field that
   needs you".
6. Duplicate-and-extras audit after a CV attach (the ATS-mangle consequence):
   flag likely duplicate or misplaced entries so the user can prune them.
7. The recoverable "other fields" section in the review: demote uncertain
   controls into an expandable group rather than dropping them, plus the
   min-fields guard and region filtering.
8. Publish to the NVDA add-on store (VirusTotal, CodeQL, note the ~18MB size
   from PyMuPDF), once out of -dev.
9. Housekeeping: revoke the repo access token when the build phase ends.
10. Grow the field fingerprint database by hand from real logs. The database
    (fingerprints.py + field_fingerprints.json) is still wired in and checked
    first in _classify, but its old growth engine was the AI vision layer,
    removed in 0.9.37, so it no longer grows itself. It holds only a few
    Workday entries now. Adding entries by hand from real forms (the accessible
    date picker, the big Almarai nationality and salary dropdowns) would make
    those hostile widgets classified instantly rather than re-derived by the
    heuristics each time. Deterministic, offline, crowd-sourceable; no AI
    needed to add entries, only to have discovered them, which we now do from
    logs instead.

### Phase 4 status (0.9.41 to 0.9.46), and what is left of it

Done and shipped, each version built, audited line by line, tested, and where
possible confirmed against real Workday and Almarai forms: AI removed (0.9.37);
review shows the real label plus fill intent (0.9.38); matching-core fixes for
father's and preferred name and for the phone dial-code and extension
(0.9.39-0.9.41); whole-word anchoring (0.9.42); imported name and address field
types, multilingual (0.9.43); phone variants and organisation (0.9.44); Chinese,
Japanese, Korean and Russian with script-aware matching (0.9.45); passport
fields (0.9.46).

Still to finish Phase 4, agreed to do last:
1. The remaining 14 languages to reach the country data's 24: Turkish,
   Indonesian, Persian, Urdu, Czech, Hungarian, Finnish, Swedish, Croatian,
   Serbian, Slovak, Estonian, Welsh, Breton. All spaced scripts, so the
   script-aware plumbing is already done; these are vetted word additions. Value
   is concentrated in the first few; Breton especially is near-zero for real
   forms and lowest confidence, included only for parity with the country set.
2. The CV reader to the same language set: expand its section headings beyond 9,
   and make its name check script-aware, so a name in Chinese, Japanese or
   Arabic script is picked up too. (Its email, phone and country detection are
   already language-independent or 24-language.)
3. Passport given and family name sub-fields, only if a real form shows them,
   since they need a compound "mentions passport AND given/family name" rule the
   simple matcher cannot express cleanly.

### Phases 5 to 7 and the language finish (0.9.48 to 0.9.53) - done

- Phase 5, phone group (0.9.48): when a form has a separate country-code field
  and a phone field, the dial code fills one and the national number the other.
  NANP-safe; never guesses a code onto a plain number. Live-tested.
- Phase 6, attachments (0.9.49): file uploads and upload-labelled controls show
  in the review as "attach this yourself"; edit/fill/clear are blocked so a file
  field never gets a text paste. The speculative review-filtering was skipped as
  not needed. Live-tested.
- Phase 7, sections (0.9.50-0.9.52): a section data model (add/rename/remove
  sections and rows, free-form fields, backward compatible), a three-level
  drill-down UI reachable as My sections, and CV seeding that fills Experience,
  Education, Skills, Certifications and Languages on import. Proven on real NVDA
  by speech: import journey, add, delete, edit, and read-back all confirmed
  (`import-sections-journey.yml`, `section-crud.yml`, `section-edit.yml`,
  `section-speech.yml`). The repeating-row NVDA fill is parked; its pure planner
  (`rowfill.py`) is built and tested.
- Language finish (0.9.53): field matcher to 27 languages (the country data's
  set), CV headings to the same set, CV name check made script-aware. The
  smallest languages are a best-effort seed for native speakers to refine.
- Passport given/family name sub-fields: still deferred until a real form shows
  them.

## 9a. Logging (for real-world testing)

Every add-on line is prefixed `JFF`. A startup banner records the version; each
field logs what was read and what it matched (label, html name, aria-label,
autocomplete, role -> key, confidence, source); a whole-form fill logs each
field's action, the summary, and any field that already held a value (so an ATS
auto-parse's wrong value is visible in the log rather than silently skipped). The
menu logs the chosen command, import logs what was parsed, the review list logs
what it collected and applied (including opening a closed dropdown to read its
options). See LOGGING.md for how to capture and read a log. Info is enough for
normal use; the review journey CI runs NVDA at debug (-l 10) so the log carries
the speech and can confirm each editor announced.

---

## 10. Picking this up in a new chat

Read this file, then `addon/globalPlugins/jobFormFiller/__init__.py` and the
`core/` modules. The tests in `tests/` and `betatest/` show intended behaviour.
Trust the repo over any summary. Keep the beta-tester approach in section 2:
drive the real feature, read the real log, fail safe, and be adversarial.

## Verified platform limitation (autocomplete)
Chrome does not expose the HTML autocomplete purpose (given-name, family-name,
address-line1...) via the IA2 object attributes NVDA reads, even inside a <form>.
Confirmed empirically: a field with only an autocomplete attribute (no label, no
meaningful name) is not identifiable and is correctly declined. The addon
identifies fields via label, HTML name, and aria-label, all of which Chrome does
expose. ia2['autocomplete'] (ARIA list/inline/both on comboboxes) is still read
because it helps classify comboboxes.

## 11. Controls: grounded design (from real ATS research)

Consolidated from CONTROLS_RESEARCH.md (which keeps the full detail and sources).
The control work is built against how real application systems behave, not
assumptions.

### The systems Saudi applicants actually meet
Company-run career sites dominate, not only the government portal.
- SAP SuccessFactors: dominant (Aramco, most large corporates, government-linked).
- Oracle Taleo: SABIC, banking (Al Rajhi, Saudi National Bank), telecoms.
- Workday: the modern giga-projects (NEOM and similar).
- MenaITech: regional ATS common among Saudi SMEs.
- Jadarat: the government platform, auto-filled from Nafath.

### Real control patterns and how the addon handles each
- Native select: combobox, then LIST, then LISTITEM options. DONE.
- Custom single-select combobox: button/input role=combobox, aria-haspopup=listbox,
  aria-controls to a ul role=listbox with li role=option. The dominant modern
  pattern (Workday, Greenhouse, SuccessFactors). Open it, act on the option.
- Async search-box combobox (location): ASSISTED. The addon types the value and
  fires the async search (proven: options load in the DOM), then guides the user
  to arrow down and Enter. It cannot auto-select because NVDA's cached tree does
  not see the async-loaded options. Honest by design; full auto needs live COM
  reads (future).
- Radio group: fieldset or role=radiogroup with radio children. DONE.
- Checkbox: input type=checkbox or role=checkbox. DONE. Many (consent) have no
  saved value and are review-only.
- Multi-select: native select multiple, a checkbox group, or a tag combobox.
- Date: DONE for native input type=date (fill each segment in display order,
  locale-independent) and text date fields (format from the placeholder hint or
  the country-implied UK/US order). Custom calendar widgets: prefer the text
  input, never navigate the grid, hand back honestly if calendar-only.

### Saudi and Arabic specifics
- Nationality and Iqama status are near-universal (Nitaqat). Nationality is
  usually a required dropdown. Added as an optional profile field.
- Phone expected in +966 format.
- Much arrives pre-filled (Jadarat from Nafath, SuccessFactors from CV parse), so
  the do-not-clobber rule matters most here.
- Right-to-left Arabic is visual only; the labels the matcher reads are the same.
  The Arabic lexicon and Arabic country and nationality aliases cover them.

### Decisions
- Nationality is optional: the user fills it only if they want it used.
- File upload is out of auto-fill (the user picks the file); the review list may
  still jump to it.
- Repeatable work and education sections are out of auto-fill (CV-parsed or
  user-managed); the review list may still jump to them.
- Build order: radios and checkboxes (done), then custom combobox, multi-select,
  dates, and the async search box, with the review-list editor across all of them.

---

## 12. Country data (design and attribution)

Country and nationality are backed by one bundled dataset,
`core/countries.json`, loaded by `core/countries.py`. For each of 250 countries
it holds the canonical English name, ISO code, phone calling code, whether the
country is independent, and every name it goes by: official, common, native,
demonyms, and translations across 24 languages. This is what lets the addon
match a page's option whatever language it is written in, resolve a demonym
("Saudi" -> Saudi Arabia), and detect a CV's country.

Matching is script-aware, because scripts differ. Latin, Cyrillic, Arabic and
Korean put spaces between words, so a name is matched as a whole word; short
foreign names are allowed, short ASCII strings are not, so a two-letter code
cannot match a common word. Chinese and Japanese do not use spaces, so those
match by substring. Names are compared accent-folded. CV detection prefers the
phone's calling code (a +966 number is Saudi Arabia) over scattered place
mentions. All of this is pure Python and covered by `tests/test_countries.py`,
including a per-language sweep.

The field-recognition lexicon (which box is name, email, and so on) is at 27
languages and growing to match the country layer's 24, so the two eventually
line up; Chinese and Japanese already share the country layer's script-aware
substring matching. Widening the lexicon is recognition data, not translating
the interface.

ATTRIBUTION: the country dataset is built from the open mledoze/countries
project (https://github.com/mledoze/countries), licensed ODbL 1.0 for the data.
It is reused here with attribution, as that licence allows.
