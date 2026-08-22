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

## Feature: whole-form fill (NVDA+Shift+A)

- [done] Guidebook: labelled form, one press, all identifiable fields fill, a
  spoken summary names what was left.
- [done] FedEx: values actually land in the real DOM, not just announced.
- [done] Obsessive-Compulsive: five rapid presses in a row; no corruption (the
  fail-safe focus check skips rather than double-pastes).
- [done] Antisocial / wrong-turn: press the key with focus on a non-editable
  element; it declines gracefully.
- [todo] Intellectual: a form with 60+ fields; performance and completeness.
- [todo] Antisocial: press fill on a page mid-load, before fields are ready.

## Feature: single-field fill (NVDA+Shift+F) + tabbing

- [done] Landmark: tab from field to field, fill each individually.
- [done] Guidebook: fill the focused field; decline a bespoke question box.
- [todo] Wrong-turn: fill a field, tab backwards, fill it again; no duplication.

## Feature: field identification (multilingual + messy)

- [done] Landmark: labelled fields in English map correctly.
- [done] FedEx / localization: placeholder-only, aria-label-only, and Arabic
  right-to-left labels all identify; name-only via html-input-name identifies.
- [done] Couch-Potato: unlabelled, label-not-associated, native select, custom
  combobox, date picker are all correctly left alone.
- [todo] Localization breadth: a full form labelled in Spanish, then Polish, then
  German, each filled end to end.

## Feature: multi-section applications

- [done] Landmark: fill step 1, press Next, fill step 2.
- [todo] Wrong-turn: press Next before filling, fill step 2, go Back, check step 1.

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

## Feature: CV import (not yet wired)

- [todo] once wired: Guidebook import of a Word CV, then a PDF, then plain text.
- [todo] FedEx: CVs in English, Spanish, Polish, Arabic through import → review →
  fill, using CVs modelled on real-world structures.
- [todo] Antisocial: a password-protected PDF; an image-only (scanned) PDF; a CV
  with no recognisable sections; a 40-page CV. Each must fail or degrade cleanly.
