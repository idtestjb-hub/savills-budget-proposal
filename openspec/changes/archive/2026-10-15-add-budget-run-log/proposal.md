## Why

The Budget Agent keeps no history of what it has produced. The internal analysis workbook is overwritten on every
run, and only the client deliverable of each project survives in `sample_output/` (five files today). Nobody can
answer simply: which budgets have been generated, how complete is each one, and how much profit does it bring
Savills?

The Head of PM and the PM team want a dashboard on the Hub server that shows this. A dashboard needs a record of
each run, written at the moment the numbers exist. That record has to come from the tool itself, because the
analysis figures cannot be recovered afterwards.

## What Changes

- Every complete run of `run.py` writes one small run record into a new folder, `Budget_Agent/reports/run_log/`,
  one file per run, so that PMs working on different PCs never write to the same file.
- A record holds:
  - which project, when, which mode (New prospect or Existing project), the budget year and the deliverable file name;
  - **completeness:** how many of the Required lines (AI Guideline) carry a figure above 0, how many are zero with a
    stated reason, how many are zero with no reason, and the percentage;
  - **money (VND per year, as the deliverable states it):** revenue, expense and fund surplus of the Management
    Fund, and the VAT basis;
  - **profit to Savills:** the analysis workbook's *Total Profit Value* (Savills' own service fee less the staff,
    operating and capex costs it carries), with the cost basis the PM had selected;
  - the number of formula-error cells and whether the figures could be read.
- The figures are read from the finished workbooks after Excel has recalculated them, the same way `verify.py`
  reads them. If Excel is missing, the record is still written, with the figures left blank and a plain warning.
- A problem with the run log never stops a run and never changes the deliverable or the analysis.
- `verify.py` gains a check that the log works on the synthetic project.

Not in this change: the dashboard page itself. It is built afterwards as a page on the Hub server (`/budget/`)
and deployed by the `[Hub]` session. It reads the folder this change creates.

No budget figure moves and no recorded baseline changes: the change only adds a file after the workbooks are written.

## Capabilities

### New Capabilities
- `budget-run-log`: what a run record contains, how its figures are measured, where it is written, and what happens
  when a figure cannot be read.

### Modified Capabilities
- `budget-workflow-verification`: verification also exercises the run log on the synthetic project.

## Impact

- **New code:** a small module that reads the finished workbooks and writes the record; one call at the end of
  `run.py` (`main()`), after the "both outputs describe the same project" check.
- **Reads:** the client deliverable and the internal analysis (through Excel, read-only copies), and
  `data/master_list_verified/AI_Guideline_Required_Classification.csv` (already used by `verify.py`).
- **Writes:** one new file per run in `Budget_Agent/reports/run_log/` (outer repository, no remote). Nothing else.
- **Data protection:** the records hold real project names and figures. They stay in the synced library and the outer
  repository; the inner repository (pushed to GitHub) gets code, specs and tests with invented names only.
- **Run time:** one extra Excel recalculation per run. To be measured in task 5.1; the expected cost is under half a minute.
- **Baselines:** none move.
- **Later work:** the `/budget/` dashboard page (Hub web flow), and an optional back-fill of the five existing
  deliverables, which have no analysis workbook, so profit stays blank for them.
