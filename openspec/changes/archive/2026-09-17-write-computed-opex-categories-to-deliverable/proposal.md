## Why

`estimate_opex()` computes five ratio-driven OPEX categories. Three of them —
Electricity, Water, Diesel — are written into the client deliverable. **Two are not:**

| Category | Analysis workbook | Client deliverable |
|---|---|---|
| Electricity | 2,669,371,536 | 2,669,371,536 |
| Water | 306,003,816 | 306,003,816 |
| Diesel (Generator Fuel) | 60,994,764 | 60,994,764 |
| **Repairs & Maintenance (materials only)** | **28,135,740** | **blank** |
| **Administrative Expense (office overhead)** | **57,166,716** | **blank** |

So on the synthetic sample the two generated workbooks disagree by **85,302,456 VND/year**. The
internal analysis costs the project at one figure; the workbook the client sees costs it at
another, 85 million lower. Nothing reconciles them and nothing warns.

This is the same defect class the recovery audit was built to catch, and the same one
`align-methods-with-logic-spec` just closed for `ESS1`/`ESS4`/`ESS16` — there the gap was
210,372,000 VND. The figures already exist and are already trusted enough to drive the analysis
workbook's Cost Priority ranking and profit calculation. What is missing is a write site.

**Real projects budget both lines.** A gap analysis against two real budgets — 11D Thi Sách (the
simplest, an office property) and Green Skyline (residential, year 1) — found:

| Section | 11D Thi Sách | Green Skyline |
|---|---|---|
| `EMA1`–`EMA7`, `EMA14` administrative | 63,600,000 | 79,185,263 |
| `ER` repairs & maintenance | 39,800,000 | 49,720,000 |

Neither line is optional or exotic. Leaving them blank understates the deliverable against every
real comparable.

## What Changes

**The computed categories are written into the client deliverable**, so the deliverable and the
analysis carry the same OPEX figure for every category `estimate_opex()` produces. One of the two
proved unreachable; the outcome is recorded immediately below rather than in a footnote.

**Outcome, recorded after implementation: only Administrative Expense was delivered.**
Repairs & Maintenance could not be written. `ERM` (row 485) is the only leaf of 178 in the `ER`
section whose allocation column reads `$F485` directly rather than the parking-area split every
sibling uses, so writing any value there immediately evaluates
`BM485 = $BK485*$BM$11/SUM($BM$11:$BN$11)` — and `BM11:BN11`, the parking-revenue allocation split,
is **empty in Savills' template**. Two `#DIV/0!` cells result.

That defect is not created by this change and is not confined to it: **351 rows carry the same
division**, dormant only because `'0. Info'!D12` (parking area in m²) is also empty — the same
missing input that keeps `RM.PA` blank. `ERM` is simply the one row whose formula ignores parking
area and therefore fires immediately. Fixing it is
`fix-parking-allocation-divide-by-zero`; this change writes Administrative Expense and leaves
Repairs & Maintenance to that one.

So the cross-workbook gap goes from **85,302,456 to 28,135,740** — 67% closed, not 100%.

**They land on catch-all leaf rows, never on the section roll-up.** `EMA` (row 94) and `ER`
(row 263) both hold live `=SUBTOTAL(...)` formulas over their sections. Writing a value there would
overwrite the template's own arithmetic and put a leaf figure in a roll-up position. The template
provides a catch-all leaf inside each range for exactly this case:

- Administrative Expense → **`EMA15` "Others"** (row 109), inside `=SUBTOTAL(9,G95:G113)` — **written**
- Repairs & Maintenance → **`ERM` "Miscellaneous"** (row 485), inside `=SUBTOTAL(9,G264:G485)` —
  correct placement, but **not written**, for the reason above

Both rows are empty in the template and keep their own `G` formula, so each figure rolls up into
its section total without any formula being destroyed.

**Why a catch-all rather than the specific leaves.** Both figures are single blended
per-m²-of-NFA ratios derived from one property (A&K Tower, n=1). Neither decomposes into the
template's line items — there is no data saying how much of the administrative figure is stationery
versus drinking water, and the `ER` section is organised by building system (electric, generator,
lifts, chillers, …) with no all-systems row. Spreading one ratio across those leaves would invent a
breakdown that does not exist.

**A semantic mismatch is recorded rather than papered over.** `Repairs & Maintenance (materials
only)` is deliberately narrow — spare parts and materials, explicitly *excluding* maintenance
contracts, which Vietnamese law funds from the separate sinking fund. But what the two real
projects actually spend under `ER` is almost entirely `ERCS` clearance and suction work — water
tank cleaning, drainage, STP and septic (100% of 11D's `ER`, 84% of Green Skyline's). Those are
services, not materials. The figure is placed in `ERM Miscellaneous` and its remark states what it
covers and what it does not, so a reader is not misled into reading it as the clearance budget.

Deliberately **not** in scope:

- Every other cost code the gap analysis found blank: insurance `ESI1`/`ESI2`, night-shift
  allowance `EMH3`, waste `ESS9`/`ESS10`/`ESS19`, pest control `ESS12`, community events
  `ESC1`–`ESC5`, periodic clearance `ERCS1`–`ERCS4`, bank and audit `EMB1`/`EMB4`, STP chemicals
  `ESM10`/`ESM13`, and the contingency lines `EM#`/`ES#`/`EE#`. Each needs its own rate basis.
- `EMH1`, which stays blank per `docs/05-decisions.md` D1.
- **How either figure is derived.** `estimate_opex()` is unchanged. This change moves an existing
  number into a workbook it was already meant for; it does not improve the number. Both remain
  n=1 ratios, and both remain as thin as they were.

## Capabilities

### New Capabilities

<!-- None. The requirement that both generators agree on a cost line already exists under
     logic-spec-method-alignment; this change adds a scenario to it rather than a capability. -->

### Modified Capabilities

- `logic-spec-method-alignment`: the existing requirement that both workbooks carry the same figure
  for a cost code is extended to cover a figure the pipeline **computes but does not write** —
  silence in one workbook and a number in the other is the same divergence as two different
  numbers, and is harder to notice.

## Impact

**Code**

- `generate_project_budget.py` — `opex_admin` → row 109 added to `MGMT_FUND_ROWS` with a
  `write_even_monthly()` call whose remark states the ratio, its `n`, and that it is a whole-section
  total rather than a breakdown. `opex_repairs` is documented in place as deliberately not written,
  with the reason.
- `generate_project_budget.py` — `assert_row_code()` added: a hardcoded row is checked against the
  cost code the sheet carries in column Y before anything is written, so a reshaped template stops
  the run instead of filling the wrong cost line. Applied to the row this change adds; the other
  twenty remain unverified and that is stated at the function.

**Data**

- None. No reference table is read differently, no CSV changes, no Fact/Dim join key changes, so
  the Copilot Studio package's live data (Generation B) is unaffected. `estimate_opex()` already
  reads `Fact_OPEX.csv` (Generation A) for these two categories on every run today.

**Figures**

- Deliverable Management Fund total **+57,166,716** on the synthetic sample (`EMA` section). The
  `ER` section stays at 0. Both figures were measured under full recalculation while the two-line
  version was in place: `EMA` +57,166,716, `ER` +28,135,740, TOTAL EXPENSE +85,302,456 exactly, so
  the deferred half is known-good and blocked only by the template defect.
- The analysis workbook does **not** move — it already carried both figures. This change closes the
  gap by raising the deliverable to meet it.
- Tracked baseline figures `opex_admin_annual` and `opex_repairs_annual` do not move either; they
  are read from the analysis sheet. The baseline may still need re-recording if any deliverable-side
  figure it tracks is affected, with a stated reason.

**Not affected**

- No dependency changes. No production data changes. No template changes.
