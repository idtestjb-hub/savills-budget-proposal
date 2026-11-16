## Context

How project facts reach a run today:
- **New project:** the PM fills the input form's `Project Info`.
- **Review:** `review_import.write_form` builds the form from two places: the approved file's `0. Info` (products,
  car / motorbike bays) and the facts that section 2 of the page sends (`server.FACT_LABELS`, 13 cells).
- **Section 2 prefill:** filled from earlier run > approved file's 0. Info > master list (`webapp/facts_prefill.py`),
  but only when a library file is picked (`/api/library/{id}/facts`).
- **Site package:** prefills from `site.json` facts, which today hold what `--facts` gave (city and district for
  Sunrise). The package's master list codes every name, the project's own included (`site_data.MASK`), so nothing can
  be looked up inside a package.

What the generator does with the facts:
- It reads the form's `Project Info`: towers, floors, gates, elevators, basements, pools, areas, parking.
- On `0. Info` it writes only the four-product fee table and `F12 = car_slots`
  (`generate_project_budget.py:5124-5197`).

Decisions already taken that this change keeps:
- master tower count never filled (29/10/2026);
- master floor count is per tower, so it is used only for a one-tower project (28/10/2026);
- the PM's entry always wins;
- names matched by folded name only.

## Goals / Non-Goals

**Goals:**
- Every run's facts are as complete as the known sources allow, whatever the source mode: upload, library, earlier
  run, package.
- The facts and their source are visible in the deliverable (`0. Info`), on the run page and in the package page.
- Every approved project and every master project is checked for how many facts it would get.

**Non-Goals:**
- No new costing from the facts. Lines costed from facts only move because a blank fact is now filled.
- No change to the master list or the scan store.
- No new input-form labels: all four new section-2 cells already exist on `Project Info`.
- The internal analysis workbook is not changed.
- The sinking fund is a separate change.

## Decisions

**D1. One fact table in `facts_prefill`.**
- `FIELDS` / `NUMERIC` / `MASTER_COLUMNS` grow by:
  - `elevators` (Passenger Elevators per Tower). Master `ElevatorCount` is the project total, so it is divided by
    the tower count only when the master gives one tower; otherwise it is a note, like floors.
  - `basements` (master `BasementCount`);
  - `pool_count` (master `PoolCount`; `has_pool` follows from it as today);
  - `street` (master `Street`, else `Address_Raw`).
- `server.FACT_LABELS` gains the same four.
- `master_facts()` stays the one place that applies the master rules.
- Alternative considered: a second master reader in `review.py`. Rejected, because two copies of the 28/10 and 29/10
  rules would drift apart.

**D2. Master fallback at run time, in `review.py`, before `write_form`.**
- The project name is known only after the approved file is read, so the fallback runs there.
- Blank facts take `master_facts(prior.project_name)`.
- Sources go into `facts['_sources']` as "danh sách master"; notes go into the run notes.
- The page still prefills a library pick as today. The fallback only fills what is still blank. That makes it a no-op
  in a package, where no name matches.

**D3. `site.json` carries facts and notes.**
- `build_site_package.py` calls `master_facts` on the office master (the full names, before masking) with the folded
  `--site` name or the exact `--master-row` name.
- 0 or 2+ matches stop the build with the candidate names, unless `--master-row` or `--no-master` is given.
- `--facts` values win.
- `fact_notes` is a list of {key, text}.
- `/api/site` returns `fact_notes`. The page shows them with `factNote`.
- Facts sit in `site.json` and not in the master list, because the leak check and `site_data.MASK` stay unchanged.

**D4. Source of each fact: `Fact Sources` sheet on the run's input form.**
- `review_import.write_form` and `fill_input` (new project from the web) write it: label, value, source.
- The generator reads it with `SheetLabels`-style lookup. When it is absent the source is "form nhập liệu", which
  covers hand-filled forms and old runs.
- Source labels:
  - nhập trên trang web;
  - file ngân sách đã duyệt;
  - danh sách master;
  - lượt trước <date>;
  - dữ kiện đóng trong gói;
  - form nhập liệu.
- Alternative considered: a source column on `Project Info` itself. Rejected, because the form's columns C–F are
  already used by the product table, and a protected form layout should not move.

**D5. `0. Info` block from row 23, styled like the fee table.**
- Header row 23: Hạng mục / Giá trị / Đơn vị / Nguồn. Data from row 24, in the fixed order of the spec.
- Columns B (label), C (value), D (unit), E–G merged (source).
- Blank values get the PM-fill shading already used for `PM điền` cells and the text "Chưa có số — PM nhập".
- Row 21 (TỔNG CỘNG THỰC TẾ) stays where it is. Row 22 stays blank as a spacer.
- Nothing on the template reads rows 23+ (checked against the template's cross-sheet references, docs/09).
- `print_layout` only touches sheet 2, so printing is unaffected.

**D6. Parking rows.**
- `read_info` records which car row held the bays: `car_row_owner = True` when the row label says "riêng".
- `write_form` writes a new form label "Car Parking Ownership" ("Riêng CĐT" / "Chung"). The generator puts the car
  slots and the applied car price on row 15 or 16 accordingly, default 16.
- Motorbike slots and price go on row 18.
- The applied prices come from the same resolver as the parking revenue lines (`rates['parking']`), so `0. Info` and
  the fund sheet agree.
- F12 is not written: row 12 is the developer's car park charged a management fee per m², and the tool has no figure
  for it.
- Alternative considered: no ownership label, always row 16. Rejected, because the approved file states it and the
  review should show it back the same way.

**D7. Run page section.**
- `results.py` adds `project_info` (list of {label, value, unit, source, blank}), read from the run's input form plus
  `Fact Sources`.
- `index.html` renders it as a folding section like the other result sections (fold state kept per run).

**D8. Coverage check over all projects.**
- A script under `verification/` (`fact_coverage.py`) runs `master_facts` for every master row, and `read_info` plus
  `master_facts` for every library file.
- It prints, per fact, how many projects get a value and from which source. Counts only, no names.
- It is a report, not a gate.

## Risks / Trade-offs

- **[Master values are old or per-phase]**: a master value may be out of date, or describe a different phase of the
  project (Lô G vs Lô G6).
  → It is always shown with source "danh sách master" and can be overwritten on the page. Ambiguous names stop the
    package build and need an explicit `--master-row`.
- **[Figures move in Review runs]**: lines costed from facts that used to be blank now get a value.
  → Expected and wanted. The Review sample baselines are re-recorded only after the user signs off (task 5.3).
- **[Old forms]**: forms saved before this change have no `Fact Sources` sheet and no ownership label.
  → Fallback "form nhập liệu", default row 16. Covered by a test.
- **[Leak check]**: `site.json` now carries the own project's address and district.
  → That is the package's own project, which the leak rule allows. The check still scans for other projects' names.

## Migration Plan

1. Code and tests.
2. Run `verify.py`.
3. Rebuild City Garden and Sunrise Riverside with the new facts. Sunrise needs `--master-row`, because Lô G and Lô G6
   both match.
4. Write a budget-web release note through [Hub] only. The pending bf0ed32 notes are not touched.

Rollback: revert the commit and rebuild the packages from the previous code.

## Open Questions

- Should the master's per-tower floor count be multiplied by the master's tower count, when both exist, to suggest a
  total floor count?
  Today it is a note only, by the 28/10 decision. Kept as is unless the user says otherwise.
