# Controls research and design note

Grounded in real application systems, so the control work is built against how
these forms actually behave, not assumptions. Sources are listed at the end.
This note is the reference for the multi-control build (radios, checkboxes,
comboboxes, multi-select, dates, async search boxes) and for the review list
becoming an accessible editor for all of them.

## Why the review list is the point

Auto-fill from the profile is the easy subset: the fields we hold data for. The
real value is the review list (NVDA+J, then R). It is a plain, accessible NVDA
dialog, and from it the user can set any field on the page, including controls a
site built badly. Each field becomes a simple native prompt (type a value, pick
from a list, tick some boxes, yes or no), and the addon writes the choice back
into the real control. Even when there is nothing to auto-fill (a consent box, a
"how did you hear about us" radio), review still lets the user set it. So every
control type below needs two primitives: read (its current value and options)
and write (set a chosen value). Auto-fill uses write for the fields we have data
for; review uses both and offers the right editor per field.

## The systems Saudi applicants actually meet

Company-run career sites dominate, not only the government portal.

- SAP SuccessFactors: dominant. Aramco, most large corporates, government-linked.
- Oracle Taleo: SABIC, banking (Al Rajhi, Saudi National Bank), telecoms, multinationals.
- Workday: the modern giga-projects (NEOM and similar).
- MenaITech: regional ATS common among Saudi SMEs.
- Jadarat: the government platform, auto-filled from Nafath.

## The real SuccessFactors application, field by field

From the full candidate manual. Flow: upload CV first (parser pre-populates),
fill sections, submit. Sections:

- Profile Information: name, surname, email (pre-filled from the account), phone with international code, contact details.
- Work Experience: repeatable entries (Add / Remove), each with dates and a part-time percentage.
- Education: repeatable diploma entries with dates.
- Languages: repeatable entries, each with a proficiency level (a dropdown).
- My Documents: CV and cover letter upload.
- Job-Specific Information: per-job questions in mixed formats (multiple choice, short and long open text), a declaration to tick, a special-needs question.
- Mandatory fields carry a red asterisk; a section will not save until they are filled.

Every control type on the build list is real and common here.

## Control patterns and how the addon handles each

- Native select. Tree: combobox, then a LIST, then LISTITEM options. DONE. Select the option object via its accessibility action, verify against the live IA2 value (NVDA caches obj.value, so a raw accValue read is required).

- Custom single-select combobox. The dominant modern pattern (Workday, Greenhouse, SuccessFactors). A button or input with role=combobox, aria-haspopup=listbox, aria-expanded, aria-controls to a ul role=listbox with li role=option children. Open it, act on the target option, verify the combobox value.

- Async search-box combobox. Greenhouse and Lever location. input role=combobox, aria-autocomplete=list. Options do not exist until you type; they load over the network. Write: type the value, wait, pick the match. Review fallback: type a value, we enter it, the user confirms the match. Where it cannot confirm, say so and offer Go to.

- Radio group. fieldset or role=radiogroup with radio children (work authorisation yes/no, gender, how did you hear). Read the option labels and which is checked, act on the target radio, verify checked state.

- Checkbox. input type=checkbox or role=checkbox. Boolean. Many have no profile value (consent, declaration), so they are review-only: the user ticks them accessibly, we never auto-fill them. Read checked state, toggle to the desired state, verify.

- Multi-select. Greenhouse "multi value multi select". A native select multiple, a group of checkboxes, or a combobox where each pick becomes a tag. Read options and the selected set, toggle the set. Review offers a multi-check list.

- Date. Three real shapes. Native input type=date (segmented, type or arrow). Workday segmented arrow spinbuttons (Left/Right between day, month, year, Up/Down to change). Oracle/Taleo drops the calendar in screen-reader mode so you type the date as text. Custom calendar dialogs are the worst case. Approach: native and text entry first, Workday segments best-effort, custom calendars fall to review type entry or Go to.

## The reusable spine

Proven on native selects and expected to generalise: act on the target object
directly through its accessibility action, then verify against the live state,
not NVDA's cached value. Radios, checkboxes, and custom-combobox options are all
"act on the object, verify the state," so one mechanism covers most of them.
Keyboard-driven selection queues behind the running script and must be avoided
inside the whole-form loop; object actions apply immediately.

## Saudi and Arabic specifics

- Nationality and Iqama status are near-universal because of Nitaqat (Saudization). Nationality especially is almost always a required dropdown.
- Phone is expected in +966 format.
- Much arrives pre-filled: Jadarat from Nafath, SuccessFactors from the CV parse. The do-not-clobber rule matters most here.
- Forms are right-to-left Arabic, but RTL is visual only; labels the matcher reads are the same. The Arabic lexicon and Arabic country and nationality aliases already cover them. Some fields are searched bilingually.

## Design decisions

- Nationality is an optional profile field. The user fills it only if they want it used; blank means the addon does not fill nationality fields. Added to the details dialog and the matcher (English and Arabic and other languages).
- File upload is out of auto-fill: the user must pick the file. The review list may still jump to it (Go to).
- Repeatable work and education sections are out of auto-fill: they are CV-parsed or user-managed, and the do-not-clobber rule leaves them alone. The review list may still jump to them.
- Build order: radios and checkboxes first (reuse the object-action spine), then the custom single-select combobox (the dominant modern pattern, and nationality and language-level are usually comboboxes), then multi-select, then date, then the async search-box combobox.

## Sources read

SuccessFactors candidate manual (EASA), SuccessFactors candidate guides (Purdue,
Vermont), SAP accessibility notes, Workday accessibility guide, Oracle Taleo
accessibility features, Greenhouse Job Board API schema and support docs, Lever
application form docs, Jadarat (HRDF) apply pages, Saudi CV and ATS guides
(SuccessFactors and Taleo dominance, Nitaqat, Iqama, +966), WAI-ARIA combobox
and date-picker patterns.

## Dates: formats and inaccessible pickers (researched + handled)

Grounded in real screen-reader reports (Telerik, react-datepicker NVDA issue
12644, Angular Material, IBM Maximo, DigitalA11y's native input type=date walk).

Findings:
- Native input type=date is the good case but it is NOT one text box: it is
  separate day, month, and year spin buttons plus a calendar button. Typing a
  full slashed string misfires (the slashes jump you to the wrong segment).
- The fiddly/inaccessible ones are custom calendar widgets: react-datepicker
  (NVDA reads one character at a time and skips days), Angular Material (the
  highlighted day does not move), jQuery UI, Telerik/Kendo, IBM Maximo (arrow
  keys do not move focus at all). NVDA users get trapped in the calendar grid.
- Format differs by locale: UK DD/MM/YYYY, US MM/DD/YYYY, ISO YYYY-MM-DD.

How the addon handles dates (stored as ISO YYYY-MM-DD):
- Text date field: format to the field's own placeholder hint (DD/MM/YYYY etc.),
  else the order implied by the saved country (US month-first, else day-first).
  Proven on real NVDA for UK and US formats.
- Native input type=date: type each segment in the order the segments appear
  (which is the browser's display order), identifying each segment as day, month,
  or year from its own name and placeholder, so it is locale-independent. Never
  types a slashed string, never opens the calendar. Verified by reading the
  segment values back. Proven on real NVDA.
- Custom calendar widget (react-datepicker and friends): NEVER navigate the grid.
  Prefer the underlying text input (type the formatted date straight in); if the
  widget is calendar-only with no text input, hand back honestly ("this is a
  calendar date picker, over to you") and let the review editor offer a plain
  box. Do not pretend.
