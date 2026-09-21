## Measured effect — Wayne Tower — Thủ Thiêm (EXAMPLE)

Measured 2026-09-14 via COM full recalculation, on the current code (not assumed from design-time
estimates). Production file hash-verified unchanged before and after every run in this change.

### What moved

Four Required codes on `2. Budget-Management Fund` went from the template's blank default to a
real, sourced figure. Everything else this change touched (`EMH1`, `ESI1`, and 29 further "flagged,
not priced" codes) is a remark-only disclosure — no figure changed. `EMA1`-`EMA4` stay correctly
folded into `EMA15`'s pre-existing, already-disclosed blended figure (unchanged).

| Code | Item | Annual figure (VND) | Source |
|---|---|---|---|
| `EMA7` | Drinking water | 26,510,532 | 23 BQL headcount x 1 L/day x 365 days / 19 L bottle x 60,000 VND/bottle (guideline-cited method) |
| `EMH4` | PCCC training/allowance | 10,567,717 | Live reference to `'A5. Trợ cấp PCCC'!H8` — the template's own real, already-computed total |
| `ESC12` | Environmental incident-response plan | 14,000,004 | Guideline-cited flat figure (14,000,000/year), once/year |
| `ESM25` | Wastewater cross-check | 14,000,004 | Guideline-cited flat figure (3,500,000/occurrence x 4/year) |
| **Total new cost** | | **65,078,257** | |

### Year-one surplus movement

`'1. Summary'!H54` (estimated year-1 surplus), Wayne Tower:

- **Before this change: 7,025,863,071 VND**
- **After this change: 6,960,784,814 VND**
- **Movement: surplus DOWN by exactly 65,078,257 VND** — these are new, previously-undisclosed
  costs with no revenue offset, so the surplus falls by exactly their sum. This is a cost the
  deliverable was silently omitting, not a new expense being added to the project.

Measured two ways, cross-checked against each other:
1. **Reconstructed from the architecture**: `H54 = H46 = H13 - H20`, `H20` is a straight `SUBTOTAL`
   roll-up over the fund's leaf rows (`check_summary_reconciles`, D5, already proves this identity
   holds every run); all four new rows fall inside their section's existing `SUBTOTAL` range. So
   before = after + (sum of the four new figures) = 6,960,784,814 + 65,078,257 = 7,025,863,071.
   *(Caught and corrected a sign error here during review — an earlier draft of this doc had
   subtracted instead of added, implying the surplus rose; it falls. The "before this change"
   figure above is the corrected one.)*
2. **Actual before/after regeneration**: ran Wayne Tower twice — once with the current code, once
   with `ESC12`/`ESM25`/`EMA7`'s three constants temporarily zeroed (an established real
   before/after pattern, not algebra) — `H20` moved by exactly 54,510,540 (`EMA7`+`ESC12`+`ESM25`'s
   own sum), confirming the `SUBTOTAL` architecture behaves exactly as expected. (`EMH4` is a
   formula reference, not a zeroable constant, so it wasn't practical to isolate in this same run —
   its own contribution is separately confirmed to the VND by reading `'A5. Trợ cấp PCCC'!H8`
   directly, see the spot-check below.)

### Manual spot-check (task 6.2 — project rule for new pricing logic)

By hand, against each code's stated source:

- **`EMA7`**: 23 (BQL headcount, Wayne Tower's in-house roster excluding Security/Cleaning/
  Landscape) x 1 L/person/day x 365 days = 8,395 L/year; / 19 L/bottle = 441.84 bottles; x 60,000
  VND/bottle = 26,510,526 VND — matches the written 26,510,532 to within the same monthly-rounding
  artifact (`round(annual/12)*12`) every flat-reference cost in this file already carries. Confirmed
  correct.
- **`EMH4`**: `'A5. Trợ cấp PCCC'!H8` read directly = 10,567,716.92 (1 team leader @ 528,386 + 2
  deputies @ 1,056,772 + 17 members @ 8,982,559, per the sheet's own row-level detail) — the
  written formula `=H8/12` reproduces this exactly (no separate rounding, since F itself is a
  formula, not a literal). Confirmed correct.
- **`ESC12`**: 14,000,000 VND/year is the guideline's own stated provisional figure for this line
  (Costing_Method_Catalogue.csv, verbatim) — the written 14,000,004 is the same monthly-rounding
  artifact. Confirmed correct.
- **`ESM25`**: 3,500,000 VND/occurrence x 4 occurrences/year (quarterly) = 14,000,000, matching the
  catalogue's own stated figure exactly, same rounding artifact on the written value. Confirmed
  correct.

### What did NOT move

- `EMA1`-`EMA4`: still zero, `EMA15`'s pre-existing remark unchanged (already disclosed the blend
  before this change).
- The analysis workbook (`generate_project_output.py`'s output): not touched by this change at all.
- `'2.2 Common area Fund'`: its own totals are unaffected by this change specifically — the
  mechanism that would cascade these four new figures there (`_activate_common_area_passthrough_
  rows`) is implemented but tracked and gated separately (change `activate-common-area-fund-cost-
  share`), and its effect is deliberately excluded from this figure.
- `verify.py`'s 24 analysis-workbook baseline figures: unaffected (this change writes to the
  deliverable only). The one `verify.py` FAIL present today (`staff_cost_annual` and its dependent
  ratios, +379,523,020 VND) is pre-existing drift from the separately-paused change `reconcile-
  summary-with-detail-sheets` — not from this change (verified: nothing in this change touches
  `generate_project_output.py`, `_eff_headcount`, or any analysis-workbook code path).
