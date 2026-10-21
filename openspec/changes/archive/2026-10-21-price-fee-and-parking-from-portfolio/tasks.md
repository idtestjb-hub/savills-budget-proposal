Sign-off for every measured movement: the user, standing in for the Head of PM. Measurements run on the standard
sample, the four fixtures and the four real projects of the M3 runner, from
`Savills-local\budget-test\2026-10-20-laneB-fee-parking\` (a copy of the M3 runner pointed at the lane-b clone).
Real project names stay in `Savills-local`; the repository and `docs/` carry anonymous ids only. Nothing is committed
on `lane-b` until the user says so; `main` stays at `14778cb`.

## 0. Before

- [x] 0.1 Record the "before" on `14778cb`: the standard sample and the four fixtures (deliverable + analysis, RC 0,
  fund rows and `_UNIT_RATES` dumped to JSON), and the four real projects with the M3 runner copy
  (`run_m3.py --commit 14778cb --label fee-before`). Verify: 9 runs, RC 0, `compare/fee-before/summary.json` exists.
  - Done 2026-10-20: 5 fixtures (`before_fixtures.log`) and 5 real-project runs (`real_before.log`; the lane-C
    `masteri_td_2026_esi1` variant needs a field `14778cb` lacks and is left out), RC 0, ties 0/0.
- [x] 0.2 Confirm the store still matches its sources (every source file's modified time against
  `dim_file.modified`, no new file in `input/budget_planning/`). Verify: 0 changed, 0 new; else stop and report.

## 1. Reference data: `RM.AP` in the values file

- [x] 1.1 Extend `build_real_budget_ranges.py` (design D1, D2): read `RM.AP` and `RM.0A`, `file_profile.nfa_apartment`,
  write the `RM.AP` row as (ΣRM.AP + ΣRM.0A) ÷ apartment NFA with `basis = apartment_nfa`, `basis = fee_nfa` for the
  other codes; no row when the apartment NFA is missing or 0; README lists the count and states the denominator and the
  `RM.0A` rule. Verify with unit tests on the invented mini-store (`tests/test_build_real_budget_ranges.py`): a file with
  `RM.0A`, a file without apartment NFA, the `basis` column.
- [x] 1.2 Run the build on the real store into `Budget_Agent/data/real_budget_ranges/` (id map in the store folder).
  Verify: the name scan passes; `RM.AP` has 24 values (2025: 7, 2026: 13, 2027: 3, 2028: 1) and an independent SQL
  count with the same rules agrees; the ten existing codes' counts are unchanged; with the standard sample left out at
  least 10 projects remain after IQR. Log in the measurement folder.
  - Done 2026-10-20 (lane B): 41 projects, 446 rows (410 + 36 `RM.AP`: 24 values, 12 zero/blank; 5 without the
    line; 1 file left out for no apartment NFA). Independent SQL count agrees on all 11 codes
    (`independent_count.out.txt`); the 10 earlier codes' counts unchanged; name scan PASS (`name_scan.out.txt`);
    previous file kept in `values_before/`. `build_real.log`.

## 2. The range as a rate

- [x] 2.1 `real_budget_ranges.py` (design D4): `RATE_CODES`, `basis` read with a default, `price_line` for a rate code
  (median/P25/P75 exposed, no NFA multiplication, `usable` by the floor), `CODE_NAMES['RM.AP']`, a Vietnamese remark
  sentence for the rate case (N projects, median, P25–P75, "chưa VAT, giá năm 2027", the applied incl.-VAT rate).
  Verify with unit tests on invented values (`tests/test_real_budget_ranges.py`): rate exposed, 9 projects → not usable,
  self left out by NFA, old file without `basis` loads.
- [x] 2.2 `master_comparables.resolve_product_rates()` (design D3): source `range` between `entered` and `comparable`,
  VAT conversion at the first budget month, `apartment_comparable_rate` kept, `apartment_range` returned, fallback to the
  comparables when not usable. Verify with unit tests (`tests/test_rate_resolver.py`): range used; entered wins; range
  not usable → comparable rate identical to before; other products' fallback follows the range rate; KHOÁN basis.

## 3. Parking prices

- [x] 3.1 New `parking_prices.py` (design D5): loader, parser with statuses, `form_range`, `resolve(project)` with the
  precedence recorded → entered → range → default. Verify with unit tests (`tests/test_parking_prices.py`) on an
  invented table reproducing every text pattern of the real column (plain number, dotted thousands, comma thousands,
  decimals, tiers, "VND/xe/tháng" suffix, "không có", "N/A", "CĐT đã bán ô", 0, blank, a car price in the band's
  neighbour): parsed value and status per pattern, median/IQR/floor, self left out by name, each precedence case.
- [x] 3.2 `operating_inputs.py` and `build_project_input_form.py` (design D6): the two labels, `read_parking_prices`,
  not gated by the stable switch, the form rows with comments. Verify with unit tests (`tests/test_operating_inputs.py`):
  absent label → None; 0 → None; text → error naming the field; the built form carries both labels (`tests/
  test_input_form_guard.py` style, in memory); the live input file is not touched.

## 4. Deliverable

- [x] 4.1 `generate_project_budget.py`: `RM.AP` remark for the range case (spec deliverable-remarks), the Comparison
  sheet and `0. Info` fee note label the source; `RP1`/`RP2` rows, `_UNIT_RATES`, `_HELPER_FIGURES['parking']`, the
  `RPa` narrative and helper sheet B5 read `project['parking_prices']`; range remark, entered-price remark, and the
  former wording only for the `default` source. Verify: run the standard sample; the `RM.AP`, `RP1`, `RP2` remarks read
  as specified; `1. Summary` `RPa` and B5 quote the same prices; `python -c` check that no sheet names a project.
- [x] 4.2 Prove only the two lines and their consequences moved on the standard sample: diff every row of
  `2. Budget-Management Fund` and `2.2 Common area Fund` against the 0.1 dump. Verify: the changed codes are a subset of
  {RM.AP, RM.0A, RP1, RP2, RPa, RM#, RP#, R#, EMH1 (if % fee), RI1, EM#, ES#, EE#, totals, BM11}; list them.
  - Done 2026-10-20: leaf lines moved on the three New-prospect fixtures: RM.AP, RM.0A, RP1, RP2, RI1 and RM.KG (the
    nursery row falls back to the Apartment rate, as specified); Operating (entered rate, recorded parking) and
    Villa (0 bays, no apartments) unchanged to the line (`diff_fixtures.log`, `make_tables.py`).

## 5. Internal analysis

- [x] 5.1 `generate_project_output.py`: `Management Fee` and `Comparison` sheets label the Apartment source and show the
  comparable rate the range replaced; `Real-Budget Ranges` shows `RM.AP` as a rate (role, applied incl.-VAT rate, no
  annual amount); Additional Revenue gets the parking block (counts, median/P25/P75, applied price and source, one row
  per master-list project with text, parsed price or reason, outlier/self flag). Verify: open the analysis; the parking
  block's row count equals the residential master-list row count; the `RM.AP` applied rate equals the deliverable's.
- [x] 5.2 Printed run summary (`run.py` / `report_lines`): one line per rate with its source. Verify: run output shows
  "Apartment rate: range (N projects)" and "Car price: range / entered / recorded / default".

## 6. Verification and tests

- [x] 6.1 `verification/`: remark assertions for the `RM.AP`, `RP1`, `RP2` range wording; a cross-generator assertion
  that the analysis' parking prices equal the deliverable's `_UNIT_RATES['RP1']`/`['RP2']`; the operating-fixture
  section lists the two new fields as blank-tolerant. Verify: `pytest tests` passes (count recorded, was 915 on
  `14778cb`).
- [x] 6.2 `verify_gate_open.py` (lane B copy) PASS, RC 0, log in the measurement folder; record the baseline gate
  difference counts (13/6/0/12 on `14778cb`).
  - Done 2026-10-20: PASS, RC 0, gate differences 14/8/0/12 (`verify_gate_open.log`); the new parking-price agreement
    check reports RP2 1,200,000 / RP1 145,000 on both workbooks.

## 7. Measurement and sign-off

- [x] 7.1 A/B after the fee tasks (groups 1–2, 4.1 fee part) and after the parking tasks (3, 4.1 parking part), on the
  standard sample and the four fixtures: a table of `RM.AP`, `RM.0A`, `RP1`, `RP2`, `RI1`, year-1 surplus before →
  after, and the list of every other code that moved (expected: none beyond the consequences). Verify: table in
  `task_log.md`.
- [x] 7.2 A/B on the four real projects (`run_m3.py --label fee-after`): per project `RM.AP`, `RP1`, `RP2` tool before →
  after vs real, excl. VAT, million VND, and the total |gap| of the three codes (41,559 + 4,336 before). Verify: table
  in `task_log.md`; note that Verosa's `RM.AP` is a product-code case (villa), not a rate case.
  - Done 2026-10-20: both A/Bs measured in one step (the two sources touch disjoint codes, so each line's movement
    is attributable by code; design D10's two-step run was not needed). Tables in `task_log.md`.
- [x] 7.3 The user signs off the movements (standing in for the Head of PM), then says to commit on `lane-b`. Verify:
  the sign-off and the commit hash are recorded in `task_log.md`; no push, no merge into `main`.
  - Done 2026-10-20: the user signed off both RM.AP and RP1/RP2 ("Ký cả RM.AP và RP1/RP2") and asked for the commit on
    `lane-b`; hash in `task_log.md`.

## 8. Docs

- [x] 8.1 `RUNNING.md` (the `RM.AP` code, the `basis` column, the two form fields, the rebuild command) and `README.md`
  (`parking_prices.py` in the module map). `docs/05-decisions.md` and `docs/project-status.md` (outer repository) are
  handed to the coordinating session with the commit hash. Verify: both files mention `RM.AP` and `parking_prices.py`.
- [x] 8.2 Finish with `python verification/verify.py` (through `verify_gate_open.py` until group 10), run from
  `Budget_Agent/source_code/`, passing.
