## Why

The Review now adds year N-1 columns (Duyệt, Thực tế, Dự kiến) when the approved budget of year N carries them, but the
"Kho ngân sách" tab does not say how many store files will give those columns. The user asked (2026-10-28) to show it on
that tab, measured with the Review's own reader so the count matches what a Review run produces.

## What Changes

- A builder `build_prior_coverage.py` runs the Review reader (`review_import.read_prior_budget`) on every selectable
  store file and writes `prior_coverage.csv` into the store folder: file id, store budget year, read status, and per
  kind (approved, actual, expected) of the Management Fund whether the column was kept, whether it ties and its
  period. No amount, no project or file name, no error message text (only the exception class).
- `GET /api/library/overview` gains a `prior` block: counts per budget year of selectable files, files read, files
  with each N-1 column (and how many tie), files with all three, and the measurement date. When the file is missing or
  does not cover every selectable file, `prior.available` is false with a reason instead of counts.
- The tab's "Dùng cho Review" view shows that block as a table under the existing charts.

Rules approved by the user on 2026-10-28: only selectable files; a column counts when the Review reader keeps it for
the Management Fund (MF), under the same checks as a Review run (year N-1, not a template, empty or other-project
column); ties shown separately; files the reader cannot read are their own row; years are the store's budget years;
the Common-area Fund is not counted.

## Capabilities

### New Capabilities

### Modified Capabilities
- `library-overview`: the Review view also shows N-1 column coverage measured by the Review reader.

## Impact

- New `build_prior_coverage.py`; `webapp/library.py` (`overview()`), `webapp/static/index.html` (tab Kho).
- New store file `prior_coverage.csv` (client store `Savills-local\budget-agent\scan-2026-10-07\final_v4`, server store
  `_kho_quet`): the [Hub] session copies it with the store; the web shows a reason until it is there.
- No change to the Review itself or to any deliverable.
