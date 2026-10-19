## Why

The deliverable leaves several Required lines at 0 VND because the tool has no price for them. Examples are the
operation audit (`EMB4`), pest control (`ESS12`) and Tết decoration (`ESC5`). docs/27 lists them among the largest
missing lines by VND across the 8 detailed budgets. The real-budget scan store now holds 83 Savills budgets
(75 new + 8 old), 50 of them usable, so these lines can be priced from what Savills projects actually budget. On
2026-10-12 the user approved using the store in place of the rule that only the 8 detailed budgets are used for
estimating (`docs/05-decisions.md`, "Real-budget scan store replaces the 8-budget rule").

## What Changes

- **A build step turns the scan store into one anonymous data file.**
  - The file holds one row per project and code: VND per m² of fee-paying NFA per month, excluding VAT, brought to
    2027 prices.
  - It is written to `Budget_Agent/data/` (outer repository, no remote). It carries no project name, file name or
    other identifying text.
  - The store itself stays in `Savills-local`.
  - The build applies the approved store rules:
    - main operating-fund sheet only, tying to its total rows;
    - no PDF, xlsb or content duplicate;
    - the latest file per project, and a file with no project name counts as its own project;
    - zero and blank amounts kept out of the values and counted separately.
- **A CPI table brings older budgets to 2027**, with the source of each year.
  - Published so far: 2025 average +3.31%, 9-month 2026 average +4.52% (Cục Thống kê).
  - The step from 2026 to 2027 has no published figure yet. Its stand-in is an open decision (design D4).
- **At run time the tool prices these lines from the range:**
  - per m²: `EMB4`, `ESS12`, `ESC5`, `ESS7`;
  - `ESS23` only on a project with a pool.
  - The steps:
    1. Leave the project being budgeted out of its own range.
    2. Drop outliers outside P25 − 1.5×IQR to P75 + 1.5×IQR.
    3. Require at least 10 projects.
    4. Take the median × the project's fee-paying NFA × 12, then add the budget-year VAT.
  - With fewer than 10 projects, the line stays at 0 and its reason says so.
- **`ESC1` (events) and `ESC2` (fire drill)** get the same range as a flagged stand-in. The AI Guideline prices them
  as count × price per event, and the store holds totals only.
- **`ESI1` (asset insurance), `EMH1` and `EMH3` are not priced from the store.** The internal analysis shows their
  store range next to the tool's figure as a cross-check. `apply-head-of-pm-decisions-2026-10` owns `EMH1` and `EMH3`.
- **Client remark on each priced line, in Vietnamese:** the median, P25–P75, the number of Savills projects, the
  price year, and the VAT. No project name appears.
- **New internal analysis sheet `Real-Budget Ranges`:** for each code it lists the projects used (anonymous ids),
  those dropped as outliers or as the project itself, P25 / median / P75, and the figure written.
- **Verification** ties that sheet to the deliverable, checks the 10-project floor and the leave-one-out, and scans
  the data file for names.
- **BREAKING (figures):** on the standard sample, the 7 lines above stop being 0, so totals and the surplus move. The
  baseline is re-recorded once, after a measured before/after and the Head of PM's sign-off.

## Capabilities

### New Capabilities
- `real-budget-ranges`: how the scan store becomes an anonymous per-project data file, how a range is formed at run
  time (leave-one-out, outliers, floor, CPI, VAT), which codes it prices and which it only cross-checks, and the
  internal `Real-Budget Ranges` sheet.

### Modified Capabilities
- `guideline-required-line-items`: a Required code with no recorded pricing method, or with a guideline method the
  inputs cannot feed, may be priced from the real-budget range instead of being left at 0. The range is the most
  itemized real source now available.
- `deliverable-remarks`: a line priced from the real-budget range states the median, range, project count, price year
  and VAT in Vietnamese. `ESC1`/`ESC2` state that the figure stands in for count × price.
- `budget-workflow-verification`: a check that the `Real-Budget Ranges` sheet ties to the deliverable, the floor and
  leave-one-out hold, and the data file carries no project or file name.

## Impact

- **Code:**
  - new build script `build_real_budget_ranges.py`, beside the other rescan and build scripts, reading the store path given on the command line;
  - new module `real_budget_ranges.py`;
  - `generate_project_budget.py`: the zero-reason table for these codes, and the remarks;
  - `generate_project_output.py`: the new sheet;
  - `verification/checks.py` and `verify.py`.
- **Data:**
  - new `Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv` (anonymous, outer repository);
  - new `Budget_Agent/data/generation_B_verified/Ref_CPI_VN.csv` (public figures with sources).
  - No existing table changes.
- **Figures:** standard-sample totals move. `verify.py` baselines are re-recorded once with the user's approval.
  New-prospect and Existing samples both change on these lines.
- **Order with other changes:** `apply-head-of-pm-decisions-2026-10` also re-records the baseline (its group 10).
  Decided 2026-10-19 (design D7): fold both into that one re-record, with this change's A/B measured and signed on
  its own first.
- **Docs:**
  - `openspec/config.yaml`: its context line "Comparables used for estimating come from the 8 detailed project
    budgets only" changes;
  - `docs/project-status.md`, `docs/05-decisions.md` (sign-off), `RUNNING.md` (how to rebuild the data file).
