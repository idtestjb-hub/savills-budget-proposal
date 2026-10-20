# source_code — module map

**How to run the pipeline:** `RUNNING.md`. **Dependencies:** `requirements.txt` (the one-off study scripts also use `requirements-studies.txt`).

This map was checked on 2026-10-05 against the `import` statements of every `*.py` file in this folder (31 files), not against older documentation. A module is "live" if `run.py`, `generate_project_budget.py`, `generate_project_output.py` or `build_project_input_form.py` imports it, directly or through another live module. If you add or move a module, re-check that statement.

## 1. The live pipeline (12 modules)

| Module | What it does |
|---|---|
| `run.py` | The one command: checks the input workbook exists and is not locked, runs both generators, then confirms the two outputs name the same project |
| `build_project_input_form.py` | Builds the blank `reports/Project_Budget_Input.xlsx`. Refuses to replace an existing one unless run with `--force` (which backs it up first) |
| `input_labels.py` | Finds each field of the input workbook by its label, not by cell address |
| `generate_project_budget.py` | Reads the input workbook and fills Savills' 2027 Resi budget form: the client deliverable (`sample_output/`) with its `Comparison` sheet, and the shift roster (`reports/Roster_Demand_Model.xlsx`) |
| `generate_project_output.py` | Reads the same input and writes the internal analysis workbook `reports/Project_Budget_Output.xlsx`, showing the reasoning behind each figure |
| `master_comparables.py` | The comparable projects, their areas and management-fee rates, and the ranking and rate-derivation functions both generators use |
| `estimate_capex_qty.py` | Estimates Capex quantities for a new project by scaling the nearest real project's item list by total NFA; used by both generators |
| `estimate_opex.py` | Estimates electricity, water, diesel, pool salt and repairs from `data/generation_A_star_schema/Fact_OPEX.csv` |
| `estimate_new_project.py` | Staffing-headcount estimate (`estimate_staff_headcount`), used by the analysis workbook's cross-check; also a standalone four-part estimation model |
| `fill_curve.py` | The single monthly occupancy fill-up curve both generators share |
| `vn_holidays.py` | Vietnamese statutory public holidays, computed (including the lunar ones) rather than typed in |
| `labor_law_params.py` | Reads the dated labour-law table `data/generation_B_verified/Ref_LaborLawParams.csv` (regional minimum wage, insurance base and caps, employer rates) and returns the values in force each month of a year |
| `existing_staffing.py` | Existing-project mode: reads the prior-year baseline by label, recomputes the staff lines (EMH2/EMH3/EMH4) under law only, keeps a reason for every change, and replicates the template's A1/A1.1 formulas for the Staff Bridge |
| `add_existing_project_sheets.py` | Adds the Existing-project fields to a dated copy of an already filled input workbook; the original is never touched |
| `real_budget_ranges.py` | Prices the Required lines with no other source (EMB4, ESS12, ESC5, ESS7, ESS23, ESC1, ESC2) from the anonymous range of real Savills budgets in `data/real_budget_ranges/`: the project itself left out, outliers dropped, at least 10 projects, CPI to 2027; also the cross-check ranges of ESI1, EMH1 and EMH3 |
| `review_import.py` | Budget Review, step 1: reads last year's approved budget workbook by line code (both fund sheets, year column, twelve months, VAT basis) and the scale from `0. Info`, and fills the Existing-project form plus the `Prior-Year Budget` sheet |
| `review.py` | Budget Review in one command: import, both generators in an isolated work folder, Excel recalculation, and the `Review` sheet (approved vs tool per line, with how the tool got each figure, two ties) |
| `common_utils_v2.py` | Shared workbook helpers, for example `repair_workbook` |

## 2. Scripts that prepared the reference data (run once; not part of a run)

Their output files are the data the live pipeline reads. They are not re-run per project. Those marked † read the confidential client workbooks in `input/budget_planning/`; do not run them without a reason.

| Script | Writes |
|---|---|
| `build_real_budget_ranges.py` | `data/real_budget_ranges/Ref_RealBudgetValues.csv` and its `README.txt`, from the real-budget scan store in `Savills-local` (the name-to-id map stays there) |
| `transform_master_list.py` | `data/master_list_verified/Dim_Property_Residential.csv` and `Dim_Property_Commercial.csv`, parsed from `input/project/2026_Master List.xlsx` |
| `derive_position_staffing_ratios.py` | `data/master_list_verified/Fact_StaffingRatio_ByPosition.csv` (per-position staff per 1,000 m² NFA) |
| `derive_staffing_benchmarks.py` | `Fact_StaffingBenchmark_Derived.csv` and `Staffing_Benchmark_Analysis.xlsx`, in the same folder |
| `rescan_capex_from_source.py` † | `data/generation_A_star_schema/Fact_Capex_Rescanned.csv` and `reports/Project_Detail_Lists.xlsx` |
| `rescan_capex_reserve.py` † | `Fact_CapexReserve.csv` (the Years 2+ reserve rate), same folder as the Capex file |
| `rescan_opex_from_source.py` † | `Fact_OPEX.csv`, same folder |
| `build_master_rate_card.py` | `output/simple_reports/Master_Rate_Card.xlsx` and the `Fact_MasterRateCard.csv` the pipeline reads for unit prices |
| `add_shift_differentials.py` | Appends the shift-differential rules to the rate card above |
| `extract_info_sheets.py` † | Dumps the canonical `Info` sheet of each real project budget, for spot-checking the master list |

The folder `data/generation_A_star_schema/` keeps its historical name; three of its files (`Fact_OPEX.csv`, `Fact_Capex_Rescanned.csv`, `Fact_CapexReserve.csv`) are live inputs, and its other files are not read at run time.

## 3. One-off studies and older tools (not reached by a run)

| Module | What it is |
|---|---|
| `study_capex_qty_estimation.py` | The two studies behind the ratio constants in `estimate_capex_qty.py`; writes `Capex_Qty_Estimation_Study.xlsx` |
| `generate_from_real_project.py` | A demonstration: fills a deliverable from a real project's Info sheet as if it were a new prospect's intake |
| `build_roster_input_form.py`, `generate_roster.py` | The earlier standalone roster tool (`Roster_Input_Form.xlsx` to `Roster_Demand_Model.xlsx`). The roster is now produced by `generate_project_budget.py` from `Project_Budget_Input.xlsx` |
| `build_project_plan_v2.py` | Builds the project-plan workbook `Budget_Agent/docs/PROJECT_PLAN_v2.xlsx` |
| `etl_project_info.py`, `etl_staff.py`, `etl_service.py`, `etl_capex.py`, `etl_budget.py` | The generic star-schema extractors of the abandoned "Generation A" ETL. Their orchestrator `run_etl_v2.py` is retired and nothing imports them; kept for reference (`docs/10-data-layer-assessment.md`) |
| `estimate_capex_qty.sql`, `estimate_new_project.sql` | SQL equivalents of the estimation logic of the same names; reference only, not run by the pipeline |

## 4. `legacy/`

Six retired modules that fail on start-up because they look for inputs in a folder that does not exist. Do not run them. See `legacy/README.md`.
