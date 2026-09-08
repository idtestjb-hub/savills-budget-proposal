## Context

See `proposal.md` — Why. The constraints below were read from the code, not assumed.

- `generate_project_budget.py`'s `position_annual_cost(d)` applies `* (1 + EMPLOYER_INSURANCE_RATE)`
  to **every** roster position. `per_position` therefore holds loaded costs for all of them.
- `security_cost`, `cleaning_cost` and `landscape_cost` are category subsets of that loaded dict,
  selected by `SERVICE_CATEGORY_KEYWORDS` (`security` / `cleaning` / `landscape`, `gardener`).
- `staff_remainder` — the `EMH2` figure — is computed as
  `staff_grand_total - security_cost - cleaning_cost - landscape_cost`. It is a **residual**, not an
  independent sum, so anything that changes the three category figures changes `EMH2` unless the
  subtraction is kept on the loaded basis.
- `generate_project_output.py` reaches the same three categories through `_cell_sum`, which sums
  **column U** of the Staff (Roster) sheet — the loaded column — using the identical keyword rules.
- `EMPLOYER_INSURANCE_RATE = 0.205 + 0.01 = 0.215`, defined in `generate_project_output.py` and
  imported by the budget generator.

The residual relationship is the crux: a naive edit that un-loads the three categories before the
subtraction would silently inflate `EMH2` by the same amount it removed, leaving the total unchanged
and the change looking like it did nothing.

## Goals / Non-Goals

**Goals**

- Price the three outsourced services without an employer contribution, in both workbooks.
- Leave `EMH2` covering exactly the same positions it covers today, still loaded.
- Make the resulting movement in figures visible through the existing baseline rather than absorbed.

**Non-Goals**

- Changing which positions count as security, cleaning or landscape. The keyword rules stay as they
  are; only the cost basis changes.
- Switching those lines onto the logic spec's stated method (`m² × unit price` for cleaning,
  `monthly contract × 12` for landscape). Real gap, separate change.
- Introducing an in-house/outsourced toggle.

## Decisions

### D1 — Compute the three categories on an unloaded basis, keep `EMH2` a loaded residual

Add an unloaded companion to the per-position cost, use it for the three service categories, and
keep `staff_remainder` computed by subtracting the **loaded** category costs from the loaded grand
total.

*Why:* it satisfies both requirements at once — the outsourced lines lose the loading, and `EMH2`
continues to represent the loaded cost of every other position, with no position counted twice or
dropped. The residual arithmetic stays on a single consistent basis.

*Alternatives considered:*

- **Remove the multiplier from `position_annual_cost()` entirely.** Simplest edit, and wrong: it
  would un-load `EMH2` too, understating genuine Savills payroll by 21.5%.
- **Divide the category totals by 1.215 after the fact.** Arithmetically equivalent but expresses
  the intent backwards — it reads as "undo a loading" rather than "these were never loaded", and it
  invites the same confusion the next time someone reads it.

*Cost:* two cost figures per position now exist. The code must be explicit about which basis each
consumer wants, and the Remarks must say which one was used.

### D2 — Keep the roster-headcount basis; do not switch to the flat vendor contract total

The three lines continue to be derived from the project's own staffing demand — headcount × daily
rate × coverage — rather than from the Service sheet's citywide contract totals.

*Why:* the daily rates already come from the Service domain, so the basis is a vendor rate applied
to this project's actual post count. The citywide alternative is a flat figure derived from **one**
building (`SampleSize = 1`), which would discard the per-project scaling that makes these lines
respond to gate count, open space and tower count.

*Alternative considered:* price the three from `Service!H` (the citywide annual totals). Rejected —
it trades a project-specific number for an n=1 reference, which is a bigger accuracy loss than the
one being fixed.

### D3 — Change both generators together, in one change

*Why:* the recovery audit's central failure mode is the two outputs describing different projects.
Correcting the deliverable while leaving the analysis loaded would produce exactly that, and the
analysis is what is supposed to explain the deliverable.

### D4 — Expect and quantify the movement before running

*Corrected 2026-09-08 after task 1.1. The original version of this decision named the wrong figures;
what follows is what was measured from the workbook, not what was assumed.*

**The three `service_*_annual` figures do NOT move.** They read the Service sheet's column H — the
citywide vendor reference, computed as `post rate ÷ shift roles × night blend × headcount × 12`. No
insurance loading has ever been applied to it, so there is nothing there to remove.

The loaded figures live in column I and in the Cost Priority STAFF rows. Measured after
implementation, all four categories move — including **Cleaning — Supervisory**, which the first
version of this table omitted:

| Cost Priority STAFF row | Loaded | Unloaded | Falls by |
|---|---|---|---|
| Security | 1,596,082,320 | 1,313,648,000 | 282,434,320 |
| Cleaning | 392,858,100 | 323,340,000 | 69,518,100 |
| Cleaning — Supervisory | 184,874,400 | 152,160,000 | 32,714,400 |
| Landscape | 325,841,130 | 268,182,000 | 57,659,130 |
| **Total** | **2,499,655,950** | **2,057,330,000** | **442,325,950** |

Supervisory belongs to the same vendor contract — the deliverable's `ESS4` has always covered
Cleaning plus Supervisory as one line — so it takes the same basis.

**The headline figure moves by less than that total, because it follows the Cost Basis toggle.**
Security and Cleaning are Must-Have; **Landscape is Conditional and Supervisory is Optional**. Under
the sample's "Must-Have Only" setting, verified against the generated workbook:

| Figure | Before | After | Change |
|---|---|---|---|
| `staff_cost_annual` | 3,949,764,525 | 3,597,812,105 | **−351,952,420** |
| `total_profit_value` | 4,796,852,093 | 5,148,804,513 | **+351,952,420** |
| `margin` | 0.393887 | 0.422788 | +0.028901 |
| `service_*_annual` (×3) | — | — | **unchanged** |
| Cost Priority Staff TOTAL | 6,790,821,867 | 6,348,495,917 | −442,325,950 |

*Why state it up front:* the baseline will fail after this change, and the only way to review that
failure honestly is to know beforehand which figures should move, in which direction, and by how
much. A movement that does not match this table is a defect, not a result.

*What this correction cost:* nothing but the prediction. Decisions D1–D3 are unaffected — the
approach, the code sites and the task breakdown all stand. Recording the starting point before
touching code is what surfaced it.

## Risks / Trade-offs

- **`EMH2` silently absorbs the reduction** → the residual subtraction stays on the loaded basis, and
  a task asserts `EMH2` is unchanged against its recorded baseline value.
- **The two generators drift apart** → both are changed in this change, and a task compares the three
  figures across the two workbooks from the same run.
- **Keyword matching quietly captures a different set of positions** → the keyword rules are not
  touched, and the position counts reported in the Remarks provide a visible cross-check.
- **The baseline is re-recorded before the diff is understood** → the re-record requires a stated
  reason, and the task ordering puts review before re-recording.
- **The two workbooks can differ by a few VND on a service line** → the deliverable stores a MONTHLY
  figure and the template derives the annual as `F x 12`, so any annual not divisible by 12 leaves a
  residue of at most 11 VND. Security lands on +4 after this change; `EMH2` already carried +3
  before it. This is inherent to the monthly split, not introduced here, and is not worth distorting
  the template's structure to remove. Treat "the two workbooks agree" as agreeing to within that
  rounding.
- **Real-project accuracy is unproven** → this corrects a double-count, which is a modelling
  correction, not a calibration against real budgets. The three lines remain n=1 citywide rates
  (`R-D02`), and that is unchanged by this work.

## Migration Plan

No data migration. The change alters generated output only; no stored artefact is rewritten.

Rollback is reverting the code change and re-recording the baseline with a reason. The previous
baseline values remain recoverable from version control.

## Open Questions

- **Service sheet column I** is labelled *"Staff (Roster) Equivalent, incl. Employer Insurance"* — a
  deliberate in-house-versus-outsourced comparison. This change leaves it loaded and leaves its
  label alone, on the grounds that the comparison is the point of the column. The specs do not say
  either way. Raised and deferred at task 1.1; revisit if the column starts being read as the cost
  rather than as a reference.
- Whether the analysis workbook should eventually price these three from the Service sheet's
  contract totals rather than the roster. Deferred: it changes the figures again and needs the
  wider `R-D02` sample-size question answered first. It does not affect this change's specs,
  approach or tasks.
