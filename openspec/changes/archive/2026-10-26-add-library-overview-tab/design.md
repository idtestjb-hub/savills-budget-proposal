## Context

- `webapp/library.py` reads the store CSVs (`BUDGET_WEB_LIBRARY_STORE`, on the server the `_kho_quet` folder inside the SharePoint library) and gives `/api/library` one entry per file with year, extension, `selectable` and a free-text `reason`. The Review tab uses it.
- The price table is built by `build_real_budget_ranges.py` from the same store. Its decisions (which file is used, merged or left out) are only logged as text in `README.txt` (`candidates()` and `group_projects()` append to a `log` list). No machine-readable record exists, so a page cannot say "55 used / 3 merged / 29 left out" from the store CSVs alone.
- The builder writes into `Budget_Agent/data/real_budget_ranges/`, which is tracked in the repository and therefore reaches the server with a deploy; the store lives in the SharePoint library and is read live. The two can drift apart.
- A one-page HTML mock-up (2026-10-26, aggregates only) already shows the layout; it is a design reference, not code to ship.

## Goals / Non-Goals

**Goals:**
- One page in the Budget web that answers: how many files per budget year, how many the tool uses, why the rest are left out.
- Make the builder's decisions a data file, so the page and the README cannot disagree.
- Show aggregates only.

**Non-Goals:**
- Changing which files the price table uses, any range or any figure.
- A file-level list (the Review picker already is one).
- Writing the page to the server or restarting it (a [Hub] release).
- Handling the six "Form riêng" files (separate change).

## Decisions

1. **Usage file written by the builder, not parsed from the README.** `Ref_RealBudgetUsage.csv` (columns `file_id, usage, reason_code, merged_into`) is built from the same `log` events and the `chosen` list in `build()`. Alternative: parse the README text on the server; rejected because the README wording is free text and not part of any contract. Reason codes are English snake_case and mapped to Vietnamese labels in the web layer, so wording can change without touching data.
2. **Usage file lives beside the values file, in the repository.** It is rebuilt in the same run as `Ref_RealBudgetValues.csv`, so the two always come from one store snapshot. Alternative: put it into the store folder on SharePoint; rejected because the builder never writes there and the store folder is also written by the scan scripts.
3. **Match check on the server.** The endpoint compares the usage ids with `dim_file.csv` ids. Equal sets give view 2; any difference marks view 2 unavailable and reports how many files are unlisted or unknown. Alternative: silently show what matches; rejected because a partial total would look correct and be wrong.
4. **One endpoint `GET /api/library/overview` returning aggregates.** The server groups; the browser only draws. Counts come from the same `library.entries()` cache as `/api/library`. A response check in the tests rejects any string that equals or contains a file name, project name or path.
5. **`reason_kind` in `library.load()`.** Each existing `reason` branch gets a stable kind (`not_xlsx`, `missing_file`, `no_fund_sheet`, `other_form`, `year_not_before_template`); the Vietnamese sentence is unchanged. `/api/library` gains one field and nothing else changes.
6. **Client drawing.** The tab follows the existing `showTab` pattern in `static/index.html`. The chart is a small inline SVG (stacked columns, series colours as explicit hex from the Primary palette: navy used, grey merged, red left out; total above each column; no gridlines, no in-chart title). Tables use the template's table style already in the page. No logo.
7. **Visibility.** All logged-in roles, like `/api/library`; the data is counts, no budget values.

## Risks / Trade-offs

- [Usage file older than the store on the server] → Decision 3 shows view 2 as unavailable with the number of unlisted files; the fix is a rebuild and a deploy.
- [The builder's log grows a new kind of event later] → every store file must get exactly one row; a test fails when a file has no row or two, and an unknown event maps to reason code `other` instead of being dropped.
- [Counts differ between the two views (53 selectable vs 55 used)] → intended: they answer different questions. Each view says so in one line under its title.
- [Store ids in the usage file] → ids are already allowed in the README; the file carries no name or path, and the builder's name check covers it.
- [Cloud-only files on the server] → the page counts store rows, not files on disk; a file missing on disk shows in view 1 as "không chọn được" with its existing reason.

## Migration Plan

1. Build and test on the client; run the builder once to write `Ref_RealBudgetUsage.csv` (values file byte-identical).
2. Commit `source_code` first, then the outer repository (usage file, docs).
3. Release note for [Hub]; the server needs no new environment variable. The deploy brings the code and the usage file together.
4. Rollback: remove the tab with the deploy; the extra field in `/api/library` and the extra CSV are harmless.
