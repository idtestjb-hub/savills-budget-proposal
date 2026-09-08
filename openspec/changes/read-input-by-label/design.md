## Context

See `proposal.md` — Why. Read from the code, not assumed.

`read_input()` in `generate_project_budget.py` reads **twenty-one** fixed addresses:

| Sheet | Addresses | Fields |
|---|---|---|
| `Project Info` | `B3`, `B5`–`B10`, `B25`, `B26`, `B29`, `B30`, `B31`, `B34`, `B35` | segment, name, site area, garden, open space, floors, towers, parking, pool, gates, fee terms |
| `Roster Setup` | `B4`–`B8`, `B12`, `B13` | staffing ratios, month, year |

Plus two positional scans: the product block at `row 14 + len(PRODUCT_ROWS)`, and public holidays
over `rows 20–30` of `Roster Setup`.

`Staffing Demand` already reads labels from column A over a row range and is not part of this
change — it is the shape the rest should look like.

Every one of these sits immediately to the right of a label in column A. The information needed to
find them robustly is already in the file.

## Goals / Non-Goals

**Goals**

- A field is found by what it is called, not where it sits.
- A field that cannot be found stops the run and says which one.
- Workbooks in either layout — before or after the Product Mix grew — read correctly.
- **No figure moves.**

**Non-Goals**

- Changing the form's layout, or what any field means.
- Excel defined names (see D4).
- The Excel formulas inside the generated form, which reference `Project Info` cells by address.
  Excel maintains those itself when rows are inserted in Excel; they are outside this change.

## Decisions

### D1 — Match on the label text in column A, take the value from column B

A small resolver builds a `{normalised label → row}` index for a sheet once, then each field is
requested by label.

Normalisation matters because the labels carry units, em-dashes and hints:
`'Pool Area (m²) — optional'`, `'% of Collected Management Fee — leave blank if not %-based'`.
Matching SHALL be on a normalised prefix — case-folded, whitespace-collapsed, and cut at the first
`(` or `—` — so that a label can gain or lose a parenthetical hint without breaking the read.

*Why:* the labels are already there, already stable, and already the thing a human uses to find the
field. It needs no change to the form and no migration of existing workbooks.

*Alternatives considered:*

- **Match the full label exactly.** Simpler, but brittle in a different direction: editing
  `'Pool Area (m²) — optional'` to drop "optional" would break the read. The failure would at least
  be loud, but it trades one fragility for another.
- **Match on a substring anywhere in the cell.** Too loose — `'Car Parking Slots'` and
  `'Moto Parking Slots'` both contain `'Parking Slots'`, and a sloppy rule would pick whichever came
  first.

### D2 — A missing label raises, naming the label and the sheet

*Why:* this is the entire point. The bug being fixed was a silent misread; replacing it with a
different silent behaviour would be pointless. Same reasoning as `isolation.py`'s missing-constant
guard, which aborts and names what it could not find rather than falling back to production paths.

*Cost:* a form with a genuinely renamed label now fails instead of limping. That is the intended
trade.

### D3 — Present-but-empty is a value, not a missing field

`Project Info!B34`/`B35` (Savills' fee) are **deliberately blank** — D1 in `docs/05-decisions.md`.
Blank must keep meaning "not yet known", so an empty value cell is a found field with an empty
value, distinct from an absent label.

### D4 — Not Excel defined names, despite being more idiomatic

Naming the cells in the form and reading by name is the conventional Excel answer, and it survives a
user inserting rows by hand.

*Why not:* names only exist in files the current form generates. Every input workbook already in
circulation would need regenerating — the exact migration this change exists to remove the need for.
Recorded as a possible successor once no pre-name workbooks remain in use.

### D5 — The product block is found by its own header, then read down by product name

Rather than starting at a fixed row 14, locate the `PRODUCT MIX` section header, take the row of
column headers beneath it, and read each product from the row whose column A matches that product's
name.

*Why:* it removes the last positional assumption in `Project Info`, and it makes the reader
independent of how many products the form carries — which is what broke last time.

### D6 — Correctness criterion: the baseline must not move

This refactors the function every figure depends on. The test is unusually clean: run verification
before and after, and **every one of the 24 figures must match**.

A second, stronger check is available for free: the **pre-migration fixture** kept from the previous
change has the old layout. Label lookup should read it correctly and produce the same figures as the
current fixture, since the two carry identical values in different positions. That single comparison
demonstrates the whole point of the change.

## Risks / Trade-offs

- **A subtly different value is read and no one notices** → the baseline is the guard, and it must
  be unchanged rather than re-recorded. A re-record here would hide exactly the defect being
  guarded against.
- **Normalisation matches the wrong label** → two labels normalising to the same prefix is a
  programming error, so the resolver fails on a duplicate rather than picking one.
- **The old fixture is not actually different enough to prove anything** → it carries the products
  at the same start row but every section below shifted by four, which is precisely the failure mode
  that occurred.
- **Someone later reverts to address-based reading for a "quick fix"** → the requirement is
  recorded in the spec, not only in the code.

## Migration Plan

None required — that is the point. Workbooks in either layout read correctly afterwards.

Rollback is reverting the code; no stored artefact changes, and the baseline is untouched either
way.

## Open Questions

- Whether `generate_roster.py`'s `Setup!B26`/`B27` should get the same treatment. It is a different
  workbook on a module outside the live pipeline path, and pulling it in would widen this change
  without reducing the risk it targets. Deferred; it does not affect these specs, the approach, or
  the tasks.
