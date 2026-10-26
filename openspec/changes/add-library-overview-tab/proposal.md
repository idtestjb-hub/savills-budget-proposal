## Why

The Budget web lists the 87 files of the real-budget store only as a long picker on the Review tab. Nobody can see at a glance how many files there are per budget year, how many the tool actually uses, and why the rest are left out. That answer exists today only in the build README of `Ref_RealBudgetValues.csv` (store ids and reasons in free text) and in a one-off summary page made on 2026-10-26. A tab inside the Budget web keeps the picture current whenever the store or the price table is rebuilt.

## What Changes

- New tab **Kho ngân sách** in the Budget web, one page, two views:
  - **Dùng cho Review**: files per budget year, selectable or not, grouped reasons, by file type. Built from the data `/api/library` already reads (53 selectable of 87).
  - **Dùng cho bảng giá thực tế**: files per budget year as used / merged into a newer file of the same project / left out, grouped reasons, by file type (55 / 3 / 29 of 87).
- New endpoint `GET /api/library/overview`: aggregates only (counts), no file name, no project name, no path; behind the same login as `/api/library`.
- `webapp/library.py` entries gain a machine-readable `reason_kind` next to the existing free-text `reason`, so the first view can group reasons without parsing sentences.
- `build_real_budget_ranges.py` writes a second output, `Ref_RealBudgetUsage.csv`, next to `Ref_RealBudgetValues.csv`: one row per store file with its class and a reason code. The second view needs it because the four store CSVs do not say which files the price table used.
- When the usage file is missing or does not match the store, the tab shows view 1 only and says view 2 is not available.
- No change to any figure: `Ref_RealBudgetValues.csv` stays byte-identical, no baseline moves.

## Capabilities

### New Capabilities
- `library-overview`: the Kho ngân sách tab and its aggregate endpoint (both views, privacy limits, missing-data behaviour).

### Modified Capabilities
- `real-budget-ranges`: the builder also records, per store file, whether the price table used it, merged it or left it out, and why.

## Impact

- Code: `webapp/library.py`, `webapp/server.py`, `webapp/static/index.html`, `build_real_budget_ranges.py`; new tests next to `tests/test_webapp_library.py` and `tests/test_build_real_budget_ranges.py`.
- Data read: store CSVs (`dim_file.csv`, `file_profile.csv`, `project_map.csv`, `reconcile.csv`) and `Budget_Agent/data/real_budget_ranges/Ref_RealBudgetUsage.csv`. Data written: only `Ref_RealBudgetUsage.csv`, by the builder.
- Deploy: the server reads the usage file from the repository it runs from; deploying is a [Hub] release (release note, not done by the session that builds this change). Until then the server has no usage file and the tab hides view 2.
- Not in scope: the Review picker, the price-range maths, the six "Form riêng" files, Power BI.
