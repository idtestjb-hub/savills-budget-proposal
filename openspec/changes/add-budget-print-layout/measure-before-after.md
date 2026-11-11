# Before / after: add-budget-print-layout (2026-11-11)

Fictional sample only: `verification/fixtures/Sample_Project_Input.xlsx`, "ZZ Sample Tower (TEST DATA - NOT A REAL
PROJECT)". No real project or amount appears here.

## Figures: no figure moves

`python verification/verify.py`, run from `Budget_Agent/source_code/` after the change, passed (exit 0):
- **4. BASELINE:** all 24 recorded figures match the baseline within tolerance.
- **5. DELIVERABLE FIGURES:** all 8 ramped deliverable figures match the baseline.
- **Summary ties:** the `1. Summary` ↔ `2. Budget-Management Fund` ↔ A1 reconciliation passes (506 checks).
- **Sheet 4:** `4. Điều chỉnh` ties to its fund lines and leaves every figure unchanged on every sample.
- **Inputs untouched:** the live input workbook is byte-identical, and production files are untouched.

The layout changes only these things:
- row and column visibility;
- print settings and the AutoFilter criteria;
- the signature cells on rows 514–526, which hold text only.

No cell that holds a figure or a formula of the table is written.

## Layout: before and after on the same sample

| Item | Before | After |
|---|---|---|
| Rows hidden on `2. Budget-Management Fund` | 0 | 402 "Not Use" lines + rows 506–513 |
| Print area / titles / footer | none | X2:BB526, rows 9:10, "Page x of y" |
| Columns AC, AE, AF, AI | shown | folded (outline level 2) |
| Signature boxes inside X:AO | 2 of 6 | 8 of 8 |
| PDF A4 from the web | — | 13 pages, A4 landscape; signature block whole on the last page; no "TRUE" |

Check `checks.check_print_layout` passes on the sample. It fails on a copy where a line with a figure is hidden by hand,
confirmed 2026-11-11.

Sign-off: the Head of PM reviews one A4 and one A3 PDF of the fictional sample against the approved sample (task 5.2,
open).
