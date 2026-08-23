# PROJECT_STATE: Job Form Filler (NVDA add-on)

A living snapshot of the project, written so a future chat, or another person,
can pick it up cold. If you are that reader: start here, then open the files it
points to. Last updated at version 0.3.2-dev.

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
- Review fields (NVDA+J, R): an accessible list over the current form, every
  field with its value or "empty, needs you". Actions per field: Go to, Edit,
  Fill from profile (recognised detail preselected), Clear; changes apply on
  close. Proven on real NVDA (lists the form, fills a field from the profile).
- Encrypted profile stored on the user's own machine (Windows DPAPI).
- A "My details" form in the NVDA Tools menu to enter and edit your details.
- Multilingual field identification (9 languages).
- Correctly declines fields it cannot identify; leaves dropdowns alone (for now).
- Handles multi-section applications: fill a section, press Next, fill the next.

Working, and proven end to end on real NVDA:
- Profiles are versions: several named profiles, each a version (English,
  Arabic, teaching). The dialog has a selector to pick one, create new, and
  delete. Switching swaps the whole detail set. Store logic tested; import and
  save through the dialog proven in `cv-import.yml`.
- CV import (text, Word, PDF): pick a CV, the fields populate for review, save;
  tested in English and Arabic, all three formats, on real NVDA (`cv-import.yml`).
  Text and Word use the standard library; PDF uses bundled PyMuPDF.

Built/tested but not yet wired or verified live:
- Profile selector, create and delete are built and the store logic is tested,
  but the create/delete keyboard flow is not yet driven in CI (next check).
- Dropdown / choice-control filling; the post-CV-attach audit.

---

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
  passing (46 assertions as of this writing):
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

The pure-Python brain has 96 checks that run in the sandbox and on Linux CI
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

- **Default ceiling is identify-and-fill.** The user stays in control and
  submits themselves. AI (for hard/inaccessible fields) is explicit opt-in per
  form, never the default.

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

- **Multilingual, 9 languages** (en, es, fr, de, it, pt, pl, nl, ar). The
  autocomplete/HTML-name signal is language-independent; the keyword lexicon is
  extensible per language; accent and stroke folding normalises diacritics
  (including Polish's non-decomposing ł).

- **Store the profile as plain JSON.** It holds ordinary contact details, not
  secrets, and the CV they came from is already on the device in plain form, so
  encryption buys little here. The pluggable crypto slot stays for later (the AI
  feature, if it ever handles anything sensitive).

- **Never guess.** Fields the matcher cannot confidently identify are declined
  and reported ("2 need you: ..."), never filled with a wrong value.

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
field / fill all fields, the review list (Fill from profile), profiles as
versions (create/switch/delete), CV import (text, Word via stdlib, PDF via
bundled PyMuPDF) across all 9 supported languages, the import-to-fill chain, real
ATS field patterns (Greenhouse, Workday, Taleo, iCIMS) including the camelCase
fix, accessible and inaccessible forms, and the do-not-clobber behaviour for a
mangled ATS auto-parse.

Still to do:
1. Automate the last menu paths by keyboard in CI: the Profile submenu
   (switch/new/delete), Import from CV, Enter your details. The operations are
   tested; driving them from the menu itself is not yet scripted.
2. Review list: CI-drive Go to, Edit and Clear (only Fill from profile is
   automated end to end so far).
3. A settings panel, home for the review-list "show every field vs only the
   gaps" toggle, and the point to revisit whether the Tools-menu item still
   earns its place.
4. Dropdown / choice-control filling (the classify/choose/verify logic is tested;
   dropdowns are currently left).
5. Remembered answers for recurring bespoke questions (notice period, right to
   work), keyed to the question wording; and a "jump to the next field that
   needs you".
6. Duplicate-and-extras audit after a CV attach (the ATS-mangle consequence):
   flag likely duplicate or misplaced entries so the user can prune them.
7. The AI opt-in rung, and OCR (Tesseract) for genuinely inaccessible fields.
8. Publish to the NVDA add-on store (VirusTotal, CodeQL, note the ~18MB size
   from PyMuPDF), once out of -dev.
9. Housekeeping: revoke the repo access token when the build phase ends.

## 9a. Logging (for real-world testing)

Every add-on line is prefixed `JFF`. A startup banner records the version; each
field logs what was read and what it matched (label, html name, aria-label,
autocomplete, role -> key, confidence, source); a whole-form fill logs each
field's action, the summary, and any field that already held a value (so an ATS
auto-parse's wrong value is visible in the log rather than silently skipped). The
menu logs the chosen command, import logs what was parsed, the review list logs
what it collected and applied. See LOGGING.md for how to capture and read a log;
set NVDA's logging level to Info.

---

## 10. Picking this up in a new chat

Read this file, then `addon/globalPlugins/jobFormFiller/__init__.py` and the
`core/` modules. The tests in `tests/` and `betatest/` show intended behaviour.
Trust the repo over any summary. Keep the beta-tester approach in section 2:
drive the real feature, read the real log, fail safe, and be adversarial.
