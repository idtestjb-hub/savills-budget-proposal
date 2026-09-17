## Context

See `proposal.md - Why`. Design-relevant current state, verified 2026-09-09 and extended by the
full sheet diff run 2026-09-10 (task 1.1):

- `generate_project_budget.py` opens `TEMPLATE_PATH` (`input/template/202608 - 2027 Resi Budget
  Form.xlsx`), `shutil.copyfile`s it, runs `common_utils_v2.repair_workbook()` (strips the corrupt
  `definedNames`), then fills leaf cells. It accesses every sheet **by exact name**
  (`wb['2. Budget-Management Fund']`, `wb['0. Info']`, `wb['A2. Bảo vệ - Security']`, …).
- The live `202608` file has **21 sheets**: 19 Savills sheets + `1. Staff cost From 08.2026 (VN)` +
  `1.1 Allowance (From 08.2026)` (pasted by a PM 2026-08-28; the pipeline writes only column G of
  the staff sheet and relies on that sheet's own payroll formulas). The deliverable adds a
  `Comparison` sheet → 22 sheets out.
- `2. Budget-Management Fund` is **row-identical** between `202608` and the 25-sheet AI Guideline
  form — every code the pipeline writes (`RM.AP` r14, `RP1` r26, `ESS1` r145, `ESS4` r148, `ESS16`
  r160, `ESM4` r196, `EEW.C` r230, `EEE.C` r240, `EED.C` r251, `EMA15` r109, `EN1..EN4` r223-226,
  `ESM2/3/5/8`) is at the same row. 493 codes each. `2.2 Common area Fund` is likewise identical
  (453 codes; the pipeline writes rows 20 and 26).
- **The rest of the shared sheets are NOT identical** (task 1.1, 2026-09-10):
  | Sheet | vs `202608` | Pipeline writes? | Effect |
  |---|---|---|---|
  | `3. Budget-Sinking Fund` | ~2,782 cell diffs — the guideline form adds an INCOME block (`RO2`, `PL2CA`) at the top and shifts every row and SUBTOTAL range down | no | — |
  | `3.1 Report-Sinking Fund` | ~979 diffs, following the same shift | no | must travel as one matched set with… |
  | `1. Summary` | 3 diffs — `H69`/`I69` VLOOKUP ranges `$Z$13`→`$Z$14`, tracking the sinking-fund shift; `K29` blanked | no | …the sinking fund. Taking the summary from one source and the sinking fund from the other makes those VLOOKUPs read one row off. |
  | `0. Info` | row 11 label `Shopping Mall` → `Shophouse`; unit-label cells `J9/J10/J11/J15/J16/J18` filled | **yes** — writes Shopping Mall's GFA/NFA/units to `C11/D11/E11` | on the new form those land in the **Shophouse** row. `0. Info` is display only — the K column recomputes but nothing in the pipeline reads it; `RM` revenue is written straight to `2. Budget-Management Fund`. No budget figure moves. |
  | `A2. Bảo vệ - Security`, `A3. Vệ sinh - Cleaning` | 22 / 18 diffs — different example staffing (`E10` hours 12→24, position counts) | rate cell only (`G3` / `K3`) | **none to any figure** — ESS1/ESS4/ESS16 cost is computed in Python from `Staffing Demand` + `SERVICE_CITYWIDE_RATES`, not from these sheets' rows |
  | `A4`, `A5`, `B1`–`B5` | identical | `B*` yes | none |
  | `2.1`, `2.2.1` reports | 1–2 blanked cells | `H4` only | none |
- The AI Guideline form's `2. Budget-Management Fund`, `1. Summary` and `2.2 Common area Fund` carry
  **zero formula references** into the new fill-up / waste sheets — the occupancy link is done by
  hand when the sheet is filled, not by a live cross-sheet formula. So carrying the new sheets in
  creates no broken formulas in the shared sheets.
- The four sheets the 25-sheet form adds over `202608`:
  | Sheet | Formula cells | External refs | Safe to carry? |
  |---|---|---|---|
  | `Tỷ lệ lấp đầy cư dân` | 523 | `0. Info` only | yes |
  | `Tiến độ lấp đầy bãi xe` | 739 | none | yes |
  | `B2.6 Rác sinh hoạt (QD67)` | 14 | none | yes |
  | `Master Info ( tính Staff cost)` | ~1,577 | `[3]A1. Tổng hợp`, `[3]Info`, … + existing `#REF!` | **no** |

## Goals / Non-Goals

**Goals**

- One committed blank template file that is the 25 standard sheets (from the AI Guideline form, with
  its instruction columns removed) + the two PM staff sheets, opening clean in Excel with no error
  cells.
- `generate_project_budget.py` builds the deliverable from it, with every currently-written figure
  landing unchanged.
- A guard that stops the run if any written code is no longer at its expected row.
- Verification re-baselined (sheet count) with a stated reason and a new "carries the standard sheet
  set" assertion.

**Non-Goals**

- Filling the three new sheets with project figures — that is change B (fill-up) and change D
  (waste).
- Carrying `Master Info` — excluded here (see D3); it returns with the per-product / comparables
  change (C).
- (was a non-goal: "folding the staff fill into `A1.`/`A1.1`" — now done in D1, since the sheets
  turned out identical.)
- Touching `generate_project_output.py` (the 5-sheet internal analysis; does not use the template).
- Any change to `MGMT_FUND_ROWS`, `PRODUCT_REVENUE_ROWS`, `COMMON_AREA_FUND_ROWS`, or any fund /
  common-area fill function — those sheets are row-identical between the two templates.
- Modernising `0. Info` beyond the one row-11 relabel — e.g. also displaying Shophouse and Nursery,
  which the new form's fee table can now hold. Deferred; the `0. Info` K column feeds nothing.
- Clearing `A2`/`A3` example staffing — the pipeline does not read those rows and `202608` already
  ships example rows there, so it is not a regression. Cosmetic follow-up.

## Decisions

### D1 — Take all sheets from the AI Guideline form (strip its instruction columns); no graft

**Superseded the earlier "graft from `202608`" plan** after task 1.1 (2026-09-10) showed
`3. Budget-Sinking Fund`, `3.1 Report-Sinking Fund` and `1. Summary` differ materially between the
two templates and must travel as one matched set (the summary's VLOOKUPs track the sinking fund's
row layout). The only internally-consistent, current source for that set is the AI Guideline form
itself.

Approach:
- Start from a copy of the AI Guideline form.
- Delete its `AI GUIDELINE` instruction columns — `L` on `0. Info` and `1. Summary`, `W` on
  `2. Budget-Management Fund`, and the `Master Info` sheet is dropped whole (D3). Delete any
  `AI GUIDELINE` / advisory column on `A2`/`A3` (col `V` / `Y`).
- Do **not** attempt a blanket "clear all example data" pass. The guideline form's residue is a
  handful of round token values (`2. Budget-Management Fund`!`G12`=10,000,000, `1. Summary`!`H13`=
  5,000,000, and example staffing on `A2`/`A3`) — comparable to what `202608` already ships and
  smaller. The pipeline already overwrites or tolerates every cell it depends on. Clearing the three
  grafted new sheets' example curve values is still done (they must be blank scaffolding).
- **No staff-sheet graft.** The guideline form's native `A1. Staff cost 08.2026 (VN)` /
  `A1.1 Allowance (From 08.2026)` are the *same* payroll calculator as the PM's
  `1. Staff cost From 08.2026 (VN)` / `1.1 Allowance` in `202608` — identical dimensions, header,
  and all 74 position rows; the only cell that differs is row 15 (`D15='PM'` and a `G15` placeholder
  in the guideline version, both of which the pipeline overwrites). So `STAFF_COST_SHEET` is
  re-pointed at `'A1. Staff cost 08.2026 (VN)'` (one constant) and `fill_staff_cost_sheet` runs
  unchanged. The deliverable then carries one standard staff sheet, not two. This supersedes the
  2026-09-09 Q2 answer ("keep the pipeline's own, reconcile A1/A1.1 later") — the reconciliation is
  now a one-line change, done here.

Rationale for not stripping example values broadly: it is high-risk (which cells are example vs
template default is not always distinguishable) for near-zero benefit, and the current pipeline
already produces a deliverable carrying `202608`'s own residue (e.g. `RO` = 5,000,000).

### D1a — The `0. Info` write is updated for the new fee-table layout

`generate_project_budget.py`'s `0. Info` block writes `Shopping Mall` GFA/NFA/units to
`C11/D11/E11`. On the new form row 11 is `Shophouse`. The fix: write
Apartment(8) / Officetel(9) / Office(10) / **Shophouse(11)** and stop writing Shopping Mall to
`0. Info` (there is no Shopping Mall row on the new form). A Shopping Mall project still gets its
`RM.SM` revenue written directly to `2. Budget-Management Fund` — unchanged. `0. Info` is a display
sheet; nothing in the pipeline reads its cells. **No budget figure moves.** The stale comment at
`generate_project_budget.py:977-979` ("Shophouse and Nursery … have no equivalent row") is updated.

### D1b — Two example cost values `202608` shipped are NOT carried; the deliverable total shifts ~28M VND

Measured 2026-09-10 (task 4.1), fixture deliverable, old template vs new:

| Line | `202608` (example default) | Standard form | Effect |
|---|---|---|---|
| `ESC12` Mandatory environmental incident-response plan | 14,000,000 VND/year | blank | −14M |
| `ESM25` Cross-check of the wastewater-plant water quality | 3,500,000 VND/quarter → 14,000,000/year | blank | −14M |
| `RI` (linked from `2.2 Common area Fund`, one differing example cell) | — | — | −119,177 |

Net: **expense −28,000,000 VND (−0.28%), estimated surplus +28,000,000 VND (+0.30%)** on the fixture.
The pipeline writes none of these lines — `202608` carried them as unsourced template defaults and
Savills' current standard form deliberately leaves them blank (they are two of the "blank lines"
change D fills with a real basis; the method catalogue already has entries for both — `ESC12`
`regulation-fixed-estimate`, `ESM25` `frequency-x-unit-cost`).

Not carried forward: (a) they are unsourced example numbers, (b) the standard form's own authors
removed them, (c) the shift reduces a small overstatement, (d) change D restores them properly.
**No figure the pipeline writes changes, and none of `verify.py`'s 24 baseline figures move** (those
are all analysis-workbook figures, which do not use the template). Recorded here and in
`docs/05-decisions.md` D6; the proposal's "no figure moves" is caveated accordingly.

### D2 — A one-time builder script, committed with the change

`build_standard_template.py` in the change folder: reads the AI Guideline form, writes
`input/template/2027 Resi Budget Form (IT team).xlsx` (strips the instruction columns, drops
`Master Info`, strips the 4 stale external-workbook links, clears the new sheets' example inputs).
Same pattern as `adopt-guideline-as-costing-method-spec`'s `build_catalogue.py` — not wired into the
pipeline, re-runnable when Savills revises the form.

### D3 — `Master Info` is excluded from the deliverable template

Its ~1,577 formulas link to an external workbook (`[3]…`) that does not travel and it already
carries `#REF!`. Carrying it in would put visible error cells in a client file and fail
`budget-workflow-verification`'s "no formula errors after recalculation" check. Benchmark
comparables are data, not a deliverable surface; they belong with the per-product management-fee
change (C). This narrows D6's wording ("…and the Master Info benchmark comparables"); recorded here
and to be noted in `docs/05-decisions.md` D6 and `docs/08-guideline-change-family.md`.

### D4 — Keep the exact-name sheet access; verify names, don't make lookups loose

The pipeline's `wb['<exact sheet name>']` calls work unchanged because the new template keeps every
existing sheet name. A task verifies each accessed name resolves in the new template before any fill
code runs. Not switching to `find_sheet_loose` — exact-name failure is a useful signal if Savills
renames a sheet.

### D5 — The row guard already exists; extend its coverage

`generate_project_budget.py` has `assert_row_code(key, expected_code)` for `MGMT_FUND_ROWS`. Confirm
it runs against the new template and covers `PRODUCT_REVENUE_ROWS` and `COMMON_AREA_FUND_ROWS`
too; add coverage where missing. This is the D3-spec requirement "a leaf row that moved is caught,
not written blind".

## Risks / Trade-offs

- **A shared sheet differs from `202608` in a way that affects a cell the pipeline writes.** → Task
  1.1 diffed every pipeline-touched sheet (done 2026-09-10). Only `0. Info` row 11 affects a write
  site, handled by D1a; the sinking-fund/summary differences are on sheets the pipeline never
  writes. If a re-run of the diff after the strip finds a new one, the fix is surfaced, not absorbed.
- **The three new sheets carry example curve values the clear misses.** → After building, open in
  Excel under full recalculation and assert zero non-empty numeric cells outside the formula
  scaffolding on `Tỷ lệ lấp đầy cư dân`, `Tiến độ lấp đầy bãi xe`, `B2.6`, and zero error cells
  anywhere in the workbook.
- **The guideline form's token residue (`G12`, `H13`, `A2`/`A3` example staff) shows in the
  deliverable.** → Accepted: it is comparable to `202608`'s own residue, which the current
  deliverable already carries; the figure-parity diff (task 4.1) is against the `202608`-based
  deliverable, so any such value that would change a figure is caught there.
- **Deleting the instruction columns shifts a formula.** → No shared-sheet formula references column
  `L` / `W` (they are the rightmost, guideline-only columns). The builder asserts the sheet's used
  range and formula count are unchanged except for the deleted columns.
- **`repair_workbook` behaves differently on the new file.** → The builder output is opened through
  the same `copyfile → repair_workbook → load_workbook` path the pipeline uses, and sheet count and
  names asserted, as a build step.
- **A rounding-only figure shift on recalculation against the new template.** → Allowed by the spec
  if the baseline is re-recorded with a stated reason; a task compares old vs new deliverable
  line-by-line and records any delta before re-baselining.

## Migration Plan

Additive to the repo (new template file, new builder script) plus a one-line `TEMPLATE_PATH` change
and verification-baseline updates. Rollback: revert `TEMPLATE_PATH` to `202608` and restore the
recorded baseline — the old template stays in place. No data migration.

## Open Questions

- Final template filename — settled in `tasks.md`, does not affect specs or approach.
- Whether `Comparison` (pipeline-added) should move to sit after the Savills sheets or stay last —
  cosmetic, default keep last.
