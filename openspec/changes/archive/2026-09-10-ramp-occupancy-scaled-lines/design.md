## Context

See `proposal.md - Why`. Current state:

- `fill_management_fund_sheet()` writes every leaf via `_write_even_monthly_row(ws, row, annual)`
  (frequency `Monthly`, `F` and `H:S` all = annual/12) or `_write_year1_lump_row` (Capex).
- `generate_project_output.py` already carries a monthly fill curve:
  `_MONTH_ANCHORS = [(0, 0.0), (12, 0.50), (24, 0.70), (36, 0.90), (48, 1.00)]` and
  `_monthly_fill_path()` (linear interpolation), used by `Owner Operating Position` and
  `Savills Fee Position`. It is a "disclosed assumption, NOT real data".
- The deliverable covers 12 months. The analysis treats those as operational months 1–12 (fill
  0% → 50%). No intake field carries a budget "operational year".
- The method catalogue marks these occupancy-scaled and states the method:
  `RM.AP..RM.KG` (area × rate), `RM.0A` (developer-covers-unlet), `RPa`/`RP1`/`RP2`
  (bays × fill × rate), `EEW`/`EEW.C`, `EEE`/`EEE.C` (with a 40% floor).
- `RM.0A` is not in `MGMT_FUND_ROWS`. `RM.AP..RM.KG` are in `PRODUCT_REVENUE_ROWS` (rows 14–22);
  `RM.0A` is row 23 on the standard form (to be verified and guarded like the rest).
- Change A already put `Tỷ lệ lấp đầy cư dân` and `Tiến độ lấp đầy bãi xe` in the deliverable, with
  their guideline formulas intact but example inputs cleared. They currently show `#DIV/0!` on the
  curve rows (dividing by the cleared unit/bay counts) — this change resolves that by populating
  them.

## Goals / Non-Goals

**Goals**

- Ramp `RM.AP..RM.KG`, `RM.0A`, `RPa`/`RP1`/`RP2`, `EEW`/`EEW.C`, `EEE`/`EEE.C` month by month.
- One fill-up curve in a shared module; the analysis workbook's numbers unchanged.
- Populate the two fill-up sheets; each ramped remark points to its sheet.
- Measure the figure movement on a real project and put it on record for PM sign-off.
- A verification baseline for the deliverable's ramped lines.

**Non-Goals**

- Ramping `ESS4` cleaning (staffing judgement — its own change) or adding `RP5`/`RP6` visitor
  parking (needs a volume basis — change D). `EED` diesel stays flat.
- A per-project curve intake field, or a "which operational year / already stable" toggle —
  deferred; this change always ramps year 1 (0% → 50%).
- Multi-year / pre-opening output (change E).
- Changing how `EEE`/`EEW`'s *annual* figure is derived (`cost-energy-from-consumption-and-tariff`).
- Driving the fill-up sheets' full guideline formula machinery — see D6.

## Decisions

### D1 — One shared `fill_curve.py`

New module `fill_curve.py` in `source_code/`: exposes `MONTH_ANCHORS`, `monthly_fill_path()` and a
helper `year1_fills()` returning the 12 fractions for operational months 1–12
(`[0.5*1/12, 0.5*2/12, …, 0.5]`). `generate_project_output.py` imports `MONTH_ANCHORS` /
`monthly_fill_path` from here and deletes its local copy — a task asserts its output is
byte-unchanged. `generate_project_budget.py` imports `year1_fills()`.

### D2 — A month-by-month writer

`_write_ramped_row(ws, row, monthly_values, remark)` alongside `_write_even_monthly_row`: sets
`C='Schedule'` (so `G=SUM(H:S)`), writes the 12 values into `H:S`, clears `F`. Occupancy-scaled
codes route through it; everything else is untouched.

### D3 — `RM` and `RM.0A` as a matched pair

For each product, full monthly fee = product NFA × product rate. `RM.<product>` month m =
full monthly fee × `resident_fill(m)`. `RM.0A` month m = (Σ full monthly fee over all products) ×
`(1 − resident_fill(m))`, written to row 23. So `RM.<all> + RM.0A` per month = the full monthly fee
for all units — the collected-vs-developer split, exactly the guideline's model. `RM.0A` gets a row
guard entry (`RM.0A` at row 23). If `savills_fee_pct` is set, `mgmt_fee_expense` (`EMH1`) still
takes `pct × annual` — unchanged, the annual is the same.

### D4 — Parking fill tracks resident fill, faster where bays are scarce

`parking_fill(m) = min(1.0, resident_fill(m) × k)` where `k = 2` if the vehicle's bay count is
below the unit count, else `1` (guideline: "~2× faster if bays < units"). Computed per vehicle type
(motorbike bays vs units, car bays vs units). `RP1`/`RP2` month m = bays × `parking_fill(m)` ×
monthly rate; `RPa` = their sum. This replaces the flat `PARKING_FEE_*_MONTHLY × slots × 12 / 12`.

### D5 — Electricity floor

`elec_fill(m) = max(0.40, min(1.0, resident_fill(m) / 0.40))`. `EEE`/`EEE.C` month m =
(annual / 12) × `elec_fill(m)`. `EEW`/`EEW.C` month m = (annual / 12) × `resident_fill(m)` (no
floor — water tracks occupancy directly per the guideline).

### D6 — Populate the fill-up sheets with values, not by driving their formulas

The two sheets carry the guideline's own elaborate model (handover %, NĐ-khó-thu, per-product
lines) built for a human filling 24 months by hand. Rather than reverse-engineer and feed that,
this change **writes the monthly fill-up percentages as values** into the sheets' curve rows
(`Tỷ lệ lấp đầy cư dân` resident row; `Tiến độ lấp đầy bãi xe` motorbike/car rows) and clears any
`#DIV/0!` the cleared example inputs left. The sheets then *show* the curve the budget used; they do
not need to self-compute it. Exact target cells are pinned in `tasks.md` after re-reading the
sheets. A ramped line's remark reads e.g. "distributed across the 12 months by the resident fill-up
curve on sheet 'Tỷ lệ lấp đầy cư dân' (0% → 50% over year 1)".

### D7 — A deliverable-figure baseline

`verification/baselines/` gains `deliverable_baseline.json`: year-1 total of `RM` (Σ products),
`RM.0A`, `RPa`, `EEW.C`, `EEE.C`, and the deliverable's estimated surplus, read from the recalculated
deliverable. `checks.py` gains a comparison, re-recordable with a stated reason like the existing
analysis baseline. This is the `budget-workflow-verification` delta.

### D8 — "Year 1 of operation" is assumed, not asked

The deliverable's 12 months are operational months 1–12. A project that is actually in year 2, or
already stable, would want a different (or no) ramp — that needs an intake field and is change E's
concern. Recorded as a stated assumption in every ramped remark and in `docs/05`.

## D3a — Measured effect (task 5.1)

Diamond Skyline, `1. Summary` (and `2. Budget-Management Fund` for the collected/developer split),
recalculated in Excel, before vs after this change (both on the current standard template), VND:

| Line | Before (flat, 100%) | After (ramped, year 1) | Δ |
|---|--:|--:|--:|
| **RM** total (summary — includes RM.0A in its subtotal) | 17,381,400,000 | 17,381,400,000 | **0** |
| — RM collected from residents (`RM.AP..RM.KG`) | 17,381,400,000 | 4,707,462,500 | −12,673,937,500 |
| — `RM.0A` developer top-up on unsold units | 0 (blank) | 12,673,937,500 | **+12,673,937,500** |
| `RPa` monthly parking (`RP1`+`RP2`) | 9,504,000,000 | 2,574,000,000 | **−6,930,000,000** |
| `RI` | 11,963,117 | 11,963,117 | 0 |
| **Total operating revenue (A)** | ~26,899,000,000 | 19,972,363,117 | **−6,927,000,000** |
| `EEW` water | 440,442,996 | 119,286,648 | −321,156,348 |
| `EEE` electricity (40% floor) | 3,842,128,512 | 2,645,465,568 | −1,196,662,944 |
| `EED` diesel (not ramped) | 87,792,096 | 87,792,096 | **0** |
| **Total energy (EE)** | 4,370,363,604 | 2,852,544,312 | −1,517,819,292 |
| **Total management expense (B)** | 11,818,765,971 | 10,300,946,679 | −1,517,819,292 |
| **Estimated year-1 surplus** | 15,080,527,506 | 9,671,416,438 | **−5,409,111,068** |

**Total management-fee revenue is unchanged** — `RM.0A` (developer pays on the ~73% of units not
yet handed over in year 1) exactly offsets the drop in what residents pay. The `−5.41bn` surplus
change is entirely: parking revenue `−6.93bn` (a half-full building's residents rent ~27% of the
bays in year 1, and there is no developer top-up for parking) partly offset by energy `+1.52bn`
(less consumption while half-empty; electricity floored at 40%). Every other line is unchanged.

This is the intended correction: the flat model showed a 15bn year-1 surplus for a building that
opens the year mostly empty, booking full parking income and full utilities. The ramped view is a
realistic year 1; the building still clears a healthy surplus because the developer carries the
management fee on unsold stock.

## Risks / Trade-offs

- **Large, deliberate figure movement.** → Task group 5 measures every affected line's year-1 total
  before/after on a real project and the net surplus change; the PM signs it off; `design.md` and
  `docs/05` D6-family record it; the deliverable baseline locks it going forward.
- **Deliverable `RM` (ramped) vs analysis `Management Fee` sheet (full annual).** The analysis
  sheet is explicitly "a ceiling, not a realistic average"; the analysis's *ramped* view is on
  `Owner Operating Position`. → The verification delta's third scenario handles this: same curve,
  and the analysis's full-occupancy line is identified as a stated ceiling, not a mismatch.
- **The fill-up sheets' own formulas disagree with the written values.** → D6: write values into the
  curve rows; if a downstream formula on the sheet recomputes and diverges, that is display-only and
  feeds no budget total (task 1.3 of change A proved the fund/summary sheets don't reference these
  sheets). A task confirms zero error cells after population.
- **`RM.0A` row position.** → Guarded like every other written row; generation stops if row 23 is
  not `RM.0A` on the current template.
- **`year1_fills()` sums to ~3.25/12 not 1.0**, so a naive "annual × fill(m)" understates the
  annual. → The writer distributes `full_monthly × fill(m)` and lets `G=SUM(H:S)` be whatever the
  ramp implies — the annual *is* lower, on purpose. Remarks state the full-occupancy annual
  alongside.

## Migration Plan

Additive: new module, new writer, `RM.0A` added, fill-up sheets populated, new deliverable baseline.
Rollback: route occupancy-scaled codes back through `_write_even_monthly_row` and drop `RM.0A`; the
analysis workbook is untouched by a rollback (it only gained an import). The 24 analysis baselines
never move.

## Open Questions

- Exact target cells on the two fill-up sheets for the curve rows — pinned in `tasks.md` after
  re-reading them; does not affect the specs or the approach.
