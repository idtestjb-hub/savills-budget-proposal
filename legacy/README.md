# legacy/ — retired modules (do not run)

Moved here on 2026-10-04 (backlog A7 `retire-broken-legacy-modules`, risk R-A01). Kept for their
history and as reference code; nothing in the live pipeline or in `verification/` imports any of
them.

**Why they are retired:** each one looks for inputs under `Budget_Agent/input/…`, a folder that
does not exist (the real inputs live one level higher, in `PM/Project/input/`). They therefore fail
on start-up with a missing-directory error that reads like an environment problem. Moving them
here changed nothing about that: their paths are still relative to the old location and still
wrong, and the files sitting next to them in `source_code/` (`common_utils_v2.py`, `etl_*.py`) are
not on their import path any more.

**Do not repath and run them casually.** `cell_scan.py` and `list_positions_by_project.py` read
every confidential client workbook in `input/budget_planning/`. Reviving any of them is its own
change.

| File | What it did | Replaced by |
|---|---|---|
| `run_etl_v2.py` | Orchestrated the "Generation A" ETL (`etl_*.py`) into the `output_v2/` star schema | Abandoned; the live pipeline reads the CSVs in `data/` directly (`docs/10-data-layer-assessment.md`) |
| `cell_scan.py` | Classified every non-empty cell of the real budget files as INPUT / CALCULATED / ERROR into `output/CellScan.sqlite` | One-off data-quality baseline; the database it produced still exists, unchanged |
| `cell_scan_report.py` | Turned `CellScan.sqlite` into CSV/TXT summaries | As above (depends on `cell_scan.py`) |
| `build_simple_reports.py` | Staff-cost / Capex / service summary workbooks (totals, no formulas) | `build_master_rate_card.py` |
| `generate_sample_project.py` | Filled the old `template 2026.xlsx` with a fictional project for a pitch file | `generate_project_budget.py` on the 2027 standard form |
| `list_positions_by_project.py` | Security / cleaning / landscape position lists per project | No direct replacement; staffing now comes from the per-position ratios `derive_position_staffing_ratios.py` produces |

`pandas` (used by `run_etl_v2.py`) is listed in `../requirements-studies.txt`, not in the live
`../requirements.txt`.
