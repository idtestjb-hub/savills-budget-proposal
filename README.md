# loaders_v2 — source code index

> **Stale index (backlog A5).** For how the pipeline runs today, read `RUNNING.md`. Six modules
> listed below (`run_etl_v2`, `cell_scan`, `cell_scan_report`, `build_simple_reports`,
> `generate_sample_project`, `list_positions_by_project`) were retired to `legacy/` on 2026-10-04;
> see `legacy/README.md`. Dependencies: `requirements.txt`.

Two generations of work live here. Both are real and both still useful — this index says which
does what, so scaling to 150+ projects means *extending* these, not re-deriving them.

## Generation A — generic ETL pipeline (pre-existing, automated)

Built to run unattended across an arbitrary number of project files without manual verification
per file. Good candidate to be the actual 150-project pipeline once its heuristics are checked
against the ground truth Generation B already verified by hand.

| File | Purpose |
|---|---|
| `common_utils_v2.py` | Shared helpers: `repair_workbook` (strips corrupted defined-names so openpyxl can open real project files), `norm`, `find_sheet_loose`/`find_sheet_exact`, `project_code_from_filename`, `get_dept_abbr`, `split_en_vn` |
| `etl_project_info.py` | Generic key-value scraper over each project's Info sheet → `Fact_ProjectInfo` / `Dim_Project` |
| `etl_staff.py` | Staff/roster extraction from real project files |
| `etl_service.py` | Security/Cleaning/Landscape sheet extraction from real project files |
| `etl_capex.py` | Capex extraction from real project files |
| `etl_budget.py` | Budget line-item extraction from real project files |
| `run_etl_v2.py` | Orchestrates the above into one run |

## Generation B — this session's additions (hand-verified, targeted)

Built to answer specific questions precisely (cell-level classification, ground-truth intake
schema, per-unit rate cards) rather than to run unattended. Where Generation A's heuristics
disagree with these verified numbers, trust these first — they were cross-checked by hand
against the actual source cells.

| File | Purpose | Depends on |
|---|---|---|
| `cell_scan.py` | Scans every non-empty cell across the 8 real project files, classifies INPUT / CALCULATED / ERROR, writes `output/CellScan.sqlite` (1.39M cells) + sheet-level summary | `common_utils_v2.py` |
| `cell_scan_report.py` | Turns `CellScan.sqlite` into `CellScan_SheetSummary.csv`, `CellScan_Errors.csv`, `CellScan_Report.txt` | run after `cell_scan.py` |
| `extract_info_sheets.py` | Finds and dumps the canonical Info sheet (property scale, GFA/NFA/units, parking) from any project file — the manual/precise counterpart to `etl_project_info.py`'s generic scraper. Source of the verified `Dim_Property_v2_verified.csv` (8 rows so far) | `common_utils_v2.py` |
| `build_master_rate_card.py` | Builds the **price-for-1-unit** rate card (staff/service/capex) that feeds the agent's Fabric reasoning layer. Outputs `output/simple_reports/Master_Rate_Card.xlsx` + `output/copilot_studio_package/data/Fact_MasterRateCard.csv` | none (reads `input/` directly) |
| `add_shift_differentials.py` | Appends the staff shift-differential rules (flat % surcharges per Vietnamese labor law — not per-project data) to the rate card | run after `build_master_rate_card.py` |
| `build_simple_reports.py` | The "just make it work, simple and readable" staff-cost summary (totals + index), the checkpoint before the rate-card work | none |
| `generate_sample_project.py` | Fills a copy of `template 2026.xlsx` with a fictional sample project's data (seeded from a real project ±15%) + adds a Comparison sheet vs. 2 real projects. The manual version of what the Copilot Studio agent's "Generate Budget File" tool should do automatically | `common_utils_v2.py` |
| `list_positions_by_project.py` | Named Security/Cleaning/Landscape position lists per project, across all 89 operating properties → `Project_Detail_Lists.xlsx` | none |
| `build_roster_input_form.py` | Builds the fillable `Roster_Input_Form.xlsx` (Month/Year, holiday dates, staffing demand table with dropdown validation) — **run this first**, edit the form, then run `generate_roster.py` | none |
| `generate_roster.py` | Reads `Roster_Input_Form.xlsx` and generates a real full calendar-month roster (correct day count, correct weekdays, round-robin day-off rotation continued seamlessly across the month) priced with real night/holiday differentials on the dates flagged in the form → `Roster_Demand_Model.xlsx`. v2 — the form is now the actual input; editing it and re-running changes the output, which wasn't true of v1 | `build_roster_input_form.py` (must be run first) |

## Suggested run order, from scratch

```
1. cell_scan.py                  → CellScan.sqlite (data-quality baseline)
2. cell_scan_report.py           → human-readable error/summary reports
3. extract_info_sheets.py        → spot-check / extend Dim_Property_v2_verified.csv
4. build_master_rate_card.py     → Master_Rate_Card.xlsx + Fact_MasterRateCard.csv
5. add_shift_differentials.py    → appends shift rules to the same rate card
6. generate_sample_project.py    → optional, demo/pitch file for a new prospect
```

`build_simple_reports.py` is a standalone checkpoint, not part of this chain — run it
independently if you just want the staff-cost totals report.

## When the pool grows to 150+ projects

The honest gap right now: Generation B's precision doesn't scale by hand past a handful of
files — `extract_info_sheets.py` and the rate-card sourcing in `build_master_rate_card.py` were
built by reading real cells one project at a time. Generation A's scripts are the ones actually
designed to run unattended across many files. The real next step is **reconciling the two**:
run Generation A across the full 150, then spot-check its output against what Generation B
already verified for the 8 known-good projects, and tighten Generation A's heuristics wherever
they disagree. That reconciliation pass — not a rewrite — is what "build a pipeline" should mean
here.
