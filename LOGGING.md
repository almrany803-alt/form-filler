# Capturing logs for real-world testing

When you test the add-on on real application forms and send the log back, this
is how to capture a useful one and what it contains.

## Set the log level so the add-on's lines are recorded

The add-on logs at INFO level. NVDA records INFO by default, but to be sure
(and to catch more detail):

1. NVDA menu (NVDA+N), Preferences, Settings, General.
2. Set "Logging level" to "Info" (or "Debug" for the most detail).
3. OK. No restart needed.

## Where the log is

- NVDA menu, Tools, "View log" opens the current log.
- On disk it is `%TEMP%\nvda.log` (the current session) and
  `nvda-old.log` (the previous session).

Copy the whole file, or just the lines containing `JFF` (that prefix is on
every line this add-on writes).

## What the log tells you

Every add-on line starts with `JFF`. The useful ones:

- `JFF: Job Form Filler <version> starting` — which build produced this log.
  Always include this line so the version is known.
- `JFF: profile store loaded, N field(s) present` — your saved details loaded.
- `JFF menu: chose ('form',)` — which menu command you ran.
- `JFF read: ...` and `JFF match: key=... conf=... src=...` — for a single
  field: what the add-on saw (label, html name, aria-label, autocomplete,
  role) and what it decided the field is, how confident, and from which signal.
  This is the line to look at when a field is filled wrongly or not at all.
- `JFF form field: <field> -> key=... conf=...` — the same, per field, during a
  whole-form fill.
- `JFF form field: 'email' already holds 'parsed-wrong@ats.example', left
  as-is` — a field that already had a value (often an ATS auto-parse). The
  add-on does not overwrite it; the value shown is what was there.
- `JFF form action: filled 'given_name' with 'Mohammed'` — a field that was
  filled, and with what.
- `JFF form summary: Filled 4 of 6. 2 need you: ...` — the outcome.
- `JFF nsel: read N option(s): [...]` / `JFF nsel: after='United Kingdom'
  verdict='confirmed'` — a native dropdown: the options read, and the value read
  back live after selecting, with the verdict. "mismatch" means it did not take.
- `JFF radio: question='...' options=['Yes','No']` / `JFF radio: value='Yes' ->
  idx=0` / `JFF radio: verdict='confirmed'` — a radio group: the question found,
  the options, the option chosen, and whether the live checked state confirmed it.
- `JFF checkbox: want=True now=True verdict=confirmed` — a checkbox: the wanted
  state, the live state after, and the verdict.
- `JFF options[...]: role=... name=...` — the raw tree read while opening a
  dropdown or finding a radio group (verbose; useful when a control is missed).
- `JFF review: collected N fields` / `JFF review: applying N change(s)` — the
  review list read the form / your edits were written back.
- Any line with `Traceback` — an error, with the full stack. Include these.

## The most useful thing to send

For a form that misbehaved: the `JFF: ... starting` line, then every `JFF read`
/ `JFF match` / `JFF form field` line for that form, the `JFF form summary`
line, and any `Traceback`. That is enough to see, field by field, what the
add-on saw and decided.

## Review editor and country (0.9.11-dev)

The kind-aware review editor logs what it collected and how:
- `JFF review: collected N field(s) [text, single, yesno, date, multi]` names
  the accessible editor chosen for each field, in order.
- `JFF review: opened select, read N option(s)` appears when a closed dropdown
  exposed no options to the cached tree, so the addon opened it to read them.
- `JFF review: applying N change(s)` on close; `wrote idx=.. kind=.. ok=..` per
  change, so a writeback that did not take is visible.
- The per-option dump (one line per dropdown option) has been removed; a long
  dropdown now logs a count and a sample, and speaks "Reading the list, one
  moment" before the read.

The review journey CI runs NVDA at debug (`-l 10`), so the log carries the
`Speaking [...]` lines and focus events. Read those to confirm each editor
actually announced (the chooser reading its options, Yes/No, the date dropdowns),
not just that the DOM changed.
