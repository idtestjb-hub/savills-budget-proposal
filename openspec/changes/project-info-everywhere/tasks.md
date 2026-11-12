## 1. Facts and sources

- [x] 1.1 `facts_prefill`: add `elevators`, `basements`, `pool_count`, `street` to `FIELDS` / `NUMERIC` /
  `MASTER_COLUMNS`. Master elevators and floors are used only for a one-tower project, otherwise noted. Tests.
- [x] 1.2 `server.FACT_LABELS` and section 2 of `index.html`: the four new cells (Passenger Elevators per Tower, Number
  of Basements, Number of Pools, Street Address), prefilled like the others
- [x] 1.3 `review.py`: blank facts from `master_facts(prior.project_name)` before `write_form`. Sources "danh sách
  master", notes into the run log. A page or approved-file value wins. Tests: upload, library, two matching rows.
- [x] 1.4 `review_import.write_form` and `webapp/fill_input`: write the `Fact Sources` sheet (label, value, source)

## 2. Deliverable 0. Info

- [x] 2.1 `read_info`: record the car row ownership. `write_form`: form label "Car Parking Ownership" (appended to the form by write_form when the form lacks it, so the live input form is not rebuilt; forms without it read "Chung").
- [x] 2.2 Generator:
  - car slots and the applied car price on row 15 or 16 by ownership;
  - motorbike slots and price on row 18;
  - F12 no longer written;
  - G7 note in Vietnamese.
- [x] 2.3 Generator: "QUY MÔ DỰ ÁN / PROJECT SCALE" block from row 23, with value, unit and source for every fact in
  the spec. A blank fact is shaded and reads "Chưa có số — PM nhập". The source comes from `Fact Sources`, else "form
  nhập liệu".
- [x] 2.4 `verification/checks.py`: the block is present with every fact row. The parking rows match the parking
  revenue inputs. F12 is blank. No formula errors on `0. Info`.

## 3. Site package and run page

- [x] 3.1 `build_site_package.py`:
  - `--master-row` / `--no-master`;
  - match the own project in the office master;
  - stop on 0 or 2+ matches, listing the candidates;
  - write `facts` and `fact_notes` to `site.json`, with `--facts` winning.
  - Tests.
- [x] 3.2 `/api/site` returns `fact_notes`. The page shows them under the matching cells.
- [x] 3.3 `results.py`: `project_info` for a run, read from its form plus `Fact Sources`. `index.html`: a folding
  "Thông tin dự án" section for new and Review results, viewers included.

## 4. Coverage over all projects

- [x] 4.1 `verification/fact_coverage.py`: for every master project and every library file, how many facts are found
  per source (counts only, no names). Write the result into `measure-coverage.md` of this change.

## 5. Verification and delivery

- [x] 5.1 Full pytest and `verification/verify.py` pass (12/11: pytest 1517 passed + the 4 package tests fixed with
  `--no-master`; verify.py exit 0, its baselines unchanged)
- [ ] 5.2 Run the Lô G Review in a rebuilt Sunrise package (`--master-row "Sunrise Riverside Lot G"`). Check in
  Excel and on the page:
  - the block and the parking rows;
  - the facts section;
  - the lines that came out 0 because a fact was blank.
- [ ] 5.3 The user signs off on the moved Review figures; re-record the Review sample baselines
- [ ] 5.4 Rebuild the City Garden package. Write the Hub release note through [Hub].
