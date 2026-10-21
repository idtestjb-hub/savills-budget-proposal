## Status

**MVP built 2026-10-20, rules chosen by the user the same day; demo figures signed off by the user the same day.** The PM team calls this job "Budget Review". The change
keeps its folder name. It grew out of the survey `docs/36-khao-sat-che-do-gia-han-ngan-sach-2026-10-20.md` and the
explore proposal of commit 7907742 (six open questions for the Head of PM). The user decided on 2026-10-20 to build a
first version on the same core, in parallel with Budget Propose, for the PM presentation of 2026-10-21. The demo
project is a real operating building whose approved 2026 budget sits in the scan store; its name stays out of the
repository.

Not in this MVP, said plainly: the per-position roster from the file's staff sheet, the twelve monthly bills, and the
carry-forward rules for lines other than staff and utilities (the explore's change 2). Those stay as the next step.

## Why

The tool builds a budget proposal for a **new** property (Budget Propose). The PM team reads it as a tool to
**review the budget of a property Savills already runs** for the coming year: take last year's approved budget, read
the project's scale from it, produce this year's budget, and see line by line how the new figure compares with the
approved one and where it came from.

What exists today (docs/36, section 1): Existing-project mode on `Project Info` carries staff cost (EMH2, EMH3, EMH4)
and common-area electricity and water (EEE.C, EEW.C) forward from figures the PM **types** into `Prior-Year Roster`
and `Prior-Year Utilities`; every other line is estimated as for a new building; and there is no sheet that sets the
approved figure beside the new one. The scan store outside the repository already reads 62 of the 87 real budget files
by line code, and 97% of the lines with a figure on their main fund sheet match a code of the 2027 form (docs/34), but
that reader has no tests and is not part of the pipeline.

## What Changes

One command, `python review.py <last year's approved budget .xlsx> [--input form] [--facts facts.json]`, does
three things in an isolated work folder (never the live `reports/`):

1. **Import.** Reads the approved budget workbook (the Savills form, 2026 or 2027 layout) with a new, tested module
   `review_import.py` ported from the scan store's rules: both fund sheets, the leaf lines by code, the approved
   annual figure, the twelve months, the VAT basis, the source sheet and row. Reads the project's scale from `0. Info`
   (fee-paying area and units per product, parking bays, fee rate per product). Writes a filled input form in
   Existing-project mode: `Project Info` (mode, prior budget year, budget start month, scale, fee rates, stable
   operation, parking revenue, collect-on-behalf amounts), the `Prior-Year Roster` staff lines, the `Prior-Year Utilities` approved lines, and
   a new sheet **`Prior-Year Budget`** holding every line read plus an `IMPORT NOTES` block listing what could not be
   read, what is not on the 2027 form, and which scale fields were left blank for the PM. Facts the file does not
   carry (towers, floors, gates, pools, district) come from an optional `--facts` JSON or stay blank.
2. **Generate.** Runs the existing pipeline (`run.py`'s two generators) on that form. Staff and utilities move by law
   and tariff as today; every other line is estimated as today. No generator reads the new sheet. New-prospect mode
   does not change by a single VND (A/B on the standard sample and the five fixtures).
3. **Review sheet.** After Excel recalculates the deliverable, a sheet **`Review`** is added at the end of
   `Project_Budget_Output.xlsx`: a summary (revenue, expense, surplus: approved vs tool), then for each fund sheet and
   section one row per code with the item name in Vietnamese, the approved figure as read, the VAT factor, the
   approved figure on the deliverable's basis, the tool's figure, the difference in VND and %, how the tool got its
   figure (carried forward by law / by tariff / entered by the PM / estimated, with the method / no method), and a
   remark. Section and fund totals. Two ties are checked and printed, and the command exits non-zero if either fails:
   the tool column's section totals equal the deliverable's own R and E rows; the approved column's section totals
   equal the source file's own R and E rows.

## Capabilities

### New Capabilities
- `budget-review-workflow`: how last year's approved budget is read into the input form, how the tool's new-year
  figures are set beside the approved ones, and what must tie.

### Modified Capabilities
- None in this MVP. `existing-project-staffing` and `existing-project-utilities` are used as they are (the import
  fills their approved-amount baselines). `input-workbook-reading` is not changed: the new sheet is read only by
  `review.py`, not by the generators.

## Impact

- New: `review_import.py` (reader and form filler), `review.py` (the command and the Review sheet),
  `tests/test_review_import.py`, `tests/test_review_sheet.py`, this change's artifacts.
- Unchanged: both generators, the 2027 template, the reference CSVs, `verify.py`, `build_project_input_form.py`.
- Data files read: the approved budget workbook the user names; the input form (or a fresh one built by the form
  builder); `Costing_Method_Catalogue.csv` (method text per code); the 2027 template (which codes exist on each fund
  sheet). Written: the work folder only (filled form, the three output workbooks, `review_summary.md` and `.json`).
- Recorded baselines: none move. The standard sample is a new prospect and never reaches the new code.
- Risks: input formats vary (PDF and xlsb are refused with a message; a fund sheet that does not tie to its own R
  and E rows is read and flagged); old-form codes that the 2027 template does not carry are listed, not mapped; the
  tool's non-staff lines are estimates, so the Review sheet will show large differences on lines where the approved
  budget carries a negotiated contract. That is the point of the sheet, and the next change decides which of those
  lines should be carried forward instead.
