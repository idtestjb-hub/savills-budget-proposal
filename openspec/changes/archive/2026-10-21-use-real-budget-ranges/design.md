## Context

See proposal.md for why. Current state that shapes the approach:

- **The scan store** sits in `Savills-local\budget-test\scan-2026-10-07\final_v2\`. It is a SQLite file
  (`budget_scan_v2.sqlite`) plus CSVs, built by read-only scripts from the 83 budget files in
  `input/budget_planning/`.
  - The tables used are `file_profile`, `project_map`, `dim_file` and the view `v_line`.
  - `v_line` already holds `amount_excl_vat_per_month` and `nfa_total`; `file_profile` holds `budget_year_v2`,
    `primary_sheet` and `primary_confidence`.
  - On 2026-10-12 all 83 source files were unchanged since the scan, and the folder had no new file.
- **The store holds real project names**, so it must not enter the repository. The inner repository
  (`source_code/`) is pushed to GitHub. The outer repository (`PM/Project`, which holds `Budget_Agent/data/`) has no
  remote.
- **Today these lines are written as 0** with a reason from `_FLAGGED_NO_METHOD` in `generate_project_budget.py`
  (`EMB4`, `ESC1`, `ESC2`, `ESC5`, `ESS12`, `ESS23`; `ESS7` likewise). `ESI1` has its own zero reason.
- **The tool's fee-paying area** is `project['total_nfa']`, the sum of the products' NFA. It is the same concept as
  the store's `nfa_total`.
- **VAT:** the deliverable is inclusive unless `2. Budget-Management Fund!F7` reads KHOÁN.
  `apply-head-of-pm-decisions-2026-10` (group 2) introduces dated VAT rates by month.

## Goals / Non-Goals

**Goals:**
- One rebuildable, anonymous data file; ranges formed at run time so that the project itself can be left out.
- A PM can reproduce every figure in Excel from the `Real-Budget Ranges` sheet.

**Non-Goals:**
- No new input field. The PM cannot yet override a range-priced line; that is a later change.
- No reading of PDF or OCR figures, no xlsb, no actual-spend columns. Budget lines only.
- No change to how `ESI1`, `EMH1` and `EMH3` are priced.
- No split by project type (user's choice, 2026-10-12).

## Decisions

### D1. Per-project values in the data file, ranges at run time
The build step writes per-project values, not finished ranges. The tool computes P25 / median / P75 when it runs.
- Leaving the project itself out (approved rule) needs the per-project values.
- So does a PM checking the sheet in Excel.
- **Alternative:** precomputed ranges. Rejected: they would include the project being budgeted in every Existing-mode
  back-test, and the figures could not be traced.

### D2. Anonymous id and the keys for leaving the project out
- **The id** is a sequence number, `P001`…, assigned by the build in Savills-local. The id-to-name map stays there
  (`real_budget_ranges_map.csv`).
- **Each row also carries two match keys:**
  - `name_key`: the first 16 hex characters of SHA-256 of the project name, normalised (NFC, lower case, spaces and
    punctuation removed);
  - `nfa_m2`: the fee-paying NFA, rounded to 10 m².
- **At run time** the tool leaves an id out when the input's normalised name hashes to its `name_key`, or when the
  input's total NFA is within 0.5% of its `nfa_m2`.
  - **Added 2026-10-19 (user's choice):** the input's name is also hashed without a trailing "(...)", so that a
    rebuilt or renamed copy ("CITY GARDEN (REBUILT AS NEW PROSPECT)") still matches its own entry. The 0.5% NFA
    tolerance is unchanged.
- **Alternatives:**
  - The name itself: rejected, it is identifying.
  - A salted hash: rejected, because the tool could not reproduce it without the secret.
  - Leaving the project out at build time: impossible for a project not yet known.
- **Accepted trade-off:** someone who already knows a name can confirm whether it is in the file. That stays within
  the outer repository, which has no remote.

### D3. Store rules applied by the build; range rules applied by the tool
- **The build applies:**
  - main sheet only, with `primary_confidence = 'high'`;
  - `source_type = 'excel'` (no PDF, no xlsb);
  - no `content_dup_of`;
  - the latest `budget_year_v2` per named project; an unnamed file is its own project, flagged `unnamed`;
  - a value only when `amount_excl_vat_per_month > 0` and `nfa_total > 0`, giving value = amount ÷ NFA, VND per m²
    per month;
  - per code, the counts of projects with a value and with 0 or blank.
- **The tool applies:**
  - leave-one-out (D2);
  - IQR outliers;
  - the 10-project floor;
  - the median.
- **Percentiles:** inclusive linear interpolation, the same as Excel's `PERCENTILE.INC`, so the sheet can be checked
  in Excel.
- **Outliers:** decided once on the projects left after leave-one-out, not iterated.

### D4. CPI to 2027: published years plus one stand-in
- **`Ref_CPI_VN.csv`** has one row per year: year, average CPI change, status (`published` / `stand-in`), source,
  checked on.
- **A value from budget year Y** is multiplied by the product of (1 + rate) over the years Y+1 … 2027. A 2027 budget
  gets 1; the one 2028 budget is divided by (1 + the 2028 rate), and that rate uses the same stand-in.
- **Published so far:**
  - 2025: +3.31% (Cục Thống kê, 05/01/2026);
  - 9 months of 2026: +4.52% (Cục Thống kê, 03/10/2026).
  - 2021–2024 are read from Cục Thống kê's year-end releases during the build (task 1.2).
- **Stand-in, approved by the user on 2026-10-12:** use the 9-month 2026 average, 4.52%, for:
  - 2026, until the full-year figure is published in January 2027;
  - 2027, until the Quốc hội's 2027 CPI target is passed. Then use that target, marked `stand-in`.
  - **Alternative:** no step after the last published year, so a 2026 budget keeps factor 1. Rejected as a default:
    it under-prices by about 4–5% against a 2027 budget.

### D5. VAT added at the budget year's rate
- **Values are stored excluding VAT.** The figure written = median × NFA × 12, × (1 + the budget-year VAT rate) when
  the deliverable is inclusive.
- **The rate is 10% in 2027** for these services: the 8% reduction ends 31/12/2026, under Nghị quyết 204/2025/QH15
  and Luật Thuế giá trị gia tăng 48/2024/QH15.
- **Source of the rate:** read from the dated rates of `apply-head-of-pm-decisions-2026-10` when that change has
  landed. Until then, from the rate the deliverable already uses for the budget year.
  - **As built (2026-10-19):** that change has landed, so the line is written like its other VAT lines: each budget
    month's twelfth with that month's rate (one value repeated when every month has the same rate), none under
    KHOÁN. The remark says "cộng VAT <rates> theo từng tháng" and ends with the annual figure.

### D6. Where the code goes
- **`build_real_budget_ranges.py`**, beside the other build scripts:
  - takes `--store <path to final_v2>` and `--out <data dir>`;
  - writes `Ref_RealBudgetValues.csv` and a short `README.txt` (rules, build date, counts);
  - writes the id map into the store folder, never into the repository;
  - refuses to write if any store project name appears in the output.
- **`real_budget_ranges.py`** loads the CSVs and returns one result per code:
  - the ids used and left out, P25 / median / P75, the factor, the figure and the Vietnamese remark;
  - the result carries the reason when the range is not usable.
- **`generate_project_budget.py`:**
  - for each code in scope that has no other figure, writes the result to its fund leaf row;
  - drops the code from `_FLAGGED_NO_METHOD` only when the range is usable.
- **`generate_project_output.py`:** the `Real-Budget Ranges` sheet.

### D7. Baseline and order with `apply-head-of-pm-decisions-2026-10`
- Both changes move standard-sample figures, and that change ends with a single baseline re-record (its group 10).
- **Chosen by the user on 2026-10-12:** build this change after that one is archived. It then measures its own before/after on top of a
  settled baseline, and records once more with the user's approval.
- **Alternative:** fold this change's lines into that change's re-record. Rejected: it mixes two sign-offs in one
  baseline movement.
- **Changed by the user on 2026-10-19 (plan docs/31):** fold the two into one baseline record, at that change's
  group 10. The worry above is met by keeping the sign-offs apart: this change's A/B is measured and signed on its
  own, on the merged code of groups 0-9 (`f8238ea`), and group 10 checks that the recorded movement equals the sum of
  the A/Bs of groups 2-9 and this change.

### D8. Which projects a line applies to
- `ESS23` only when "Has Swimming Pool?" is Yes.
  - **Added 2026-10-19 (user's choice):** and only when the roster employs no pool staff in-house (no Staffing
    Demand position containing "Pool" that is not an outsourced service). The standard sample has two pool
    attendants on A1, so its `ESS23` stays at 0 with a reason naming A1.
  - **Also 2026-10-19 (user's choice):** an Existing project whose staff cost is one approved lump (`EMH2` kind
    `lump`, no A1 position rows) keeps `ESS23` at 0, with a reason saying the approved lump may already include pool
    staff.
  - **Accepted by the user:** a new prospect with a pool always gets pool attendants on A1 (a blank or 0 headcount is
    estimated from Thông tư 03/2018), so `ESS23` is priced only when the pool positions are declared as an outsourced
    service. In practice the range rarely prices it.
- `ESS7` (façade cleaning): only 16 of the 50 usable budgets carry it.
  - **Approved by the user on 2026-10-12:** apply it only when the input has at least one tower ("Tower Count" ≥ 1).
  - Without a tower it stays at 0 with a stated reason.
- Every other code in scope applies to every project.
- **Phasing (user's choice, 2026-10-19):** every line is spread evenly over the 12 months, `ESC5` (Tết) and `ESC1`
  (events) included.

## Risks / Trade-offs

- **[Range from different kinds of project]**
  - The type mix is not split (user's choice), so a villa project gets an apartment-heavy median.
  - → The remark gives P25–P75, and the internal sheet lists each id's value, so the PM can judge.
- **[`ESC1` / `ESC2` stand-ins]**
  - The guideline wants count × price, so a per-m² figure can be far off for a project with a different event plan.
  - → The remark and the analysis flag both lines as stand-ins.
- **[NFA match leaves out the wrong project]** Two projects within 0.5% NFA is possible but rare.
  - → The sheet names the reason and the key that matched, and the PM can see it.
- **[Store staleness]** New budgets reach the range only when the scan and the build are re-run.
  - → `README.txt` records the build date and file count. `RUNNING.md` gives the rebuild commands.
- **[VAT taken out at one factor per sheet]** The store's report §6 notes approximations, for example internal
  transfers.
  - → The codes in scope are services billed with VAT, where the approximation holds. Insurance is out of scope.

## Migration Plan

1. Run the build once and commit the data file in the outer repository. The store stays in Savills-local.
2. Implement behind the existing pipeline. No flag is needed, because only zero lines change.
3. Measure the standard sample and one Existing sample before and after. Present the figures to the user for the Head
   of PM's sign-off. Re-record the baseline once.
4. **Rollback:** delete the data file. Every code then falls back to 0 with the reason "no usable range", and the
   tool still runs.

## Open Questions

- The exact wording of the reason on a line left at 0 because fewer than 10 projects remain is settled during
  implementation, against the internal-wording scan.
  - Settled (lane C, 2026-10-18): "Để ở mức 0: chỉ <n> ngân sách thực tế của dự án do Savills quản lý có dòng này,
    chưa đủ tối thiểu 10 dự án để lập khoảng giá."

## Measured

### Part 2: the pipeline (2026-10-19, lane A session P4)

Runs under `Savills-local\budget-test\2026-10-19-laneA-m2\`: `before` = code `4e06955` (main with groups 0-9 of
`apply-head-of-pm-decisions-2026-10` and change `fix-cleaning-staffing-ratio`, from a snapshot), `after` = this
change merged on it. A first round on `f8238ea` (folders `*_f8238ea`) gave the same line, contingency and expense
movements on every case, both on the standard sample, the
regression clone and the Existing, lump and operating fixtures. Figures are Excel-recalculated (`m2_check.py`,
`ab_table.py`, `ab_m2.json`); every cell as written is compared by row (`compare_cells_rows.out`).

**Built.**
- `generate_project_budget.py`: `REAL_BUDGET_RANGE_ROWS`, `real_budget_range_results` (shared with the analysis),
  `_inhouse_pool_staff`, `_row_has_figure` and `_write_real_budget_range_lines`, called once from
  `fill_management_fund_sheet` just before the `_FLAGGED_NO_METHOD` loop, which skips the codes it wrote. No other
  function changed; `resolve_product_rates` and the staffing functions are untouched.
- `real_budget_ranges.py`: `self_keys` (name with and without a trailing "(...)"), `reason_inhouse_pool`,
  `month_values`, and `price_line` / `remark_priced` taking the twelve VAT factors and the VAT clause.
- `generate_project_output.py`: `build_real_budget_ranges_sheet` (summary of the 10 codes, CPI table, every id with
  its value and "used" or why left out); cross-checks show the tool's own figure excl. VAT (ESI1 0; EMH1 the fixed
  fee x 12, or a pointer for a % fee; EMH3 the 'Staff (Roster)' allowance total, or a pointer in Existing mode).
- `verification/checks.py`: `read_real_budget_ranges_sheet`, `real_budget_ranges_problems`,
  `check_real_budget_ranges` (with a negative probe, ESS12 1,000 VND off); `verify.py` runs it on the standard
  sample and on both Existing samples. `EXPECTED_SHEETS['analysis']` gains `Real-Budget Ranges`.

**Measured (VND per year, 10% VAT in every month of 2027 on every case).**

| Case | EMB4 | ESS12 | ESC5 | ESS7 | ESS23 | ESC1 | ESC2 | Seven lines | EM# + ES# | Total expense | Surplus |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Standard sample (54,400 m²) | 40,664,904 | 97,829,064 | 44,297,892 | 155,907,372 | 0 | 49,579,260 | 27,084,612 | +415,363,104 | +8,307,264 | +423,670,368 (12,360,440,748 -> 12,784,111,116) | -421,470,006 (3,514,899,316 -> 3,093,429,309) |
| Regression clone (101,948 m²) | 78,854,388 | 181,966,248 | 83,015,916 | 284,582,760 | 0 | 93,583,836 | 48,071,820 | +770,074,968 | +15,401,496 | +785,476,464 | -780,377,539 |
| Existing fixture | as the standard sample | | | | | | | +415,363,104 | +8,307,264 | +423,670,368 | -421,470,006 |
| Lump fixture | as the standard sample | | | | | | | +415,363,104 | +8,307,264 | +423,670,368 | -421,470,006 |
| Operating fixture | as the standard sample | | | | | | | +415,363,104 | +8,307,264 | +423,670,368 | -420,848,637 (-1,229,525,941 -> -1,650,374,577) |

- Every line was 0 before. The surplus moves by less than the expense because `2.2 Common area Fund` carries its
  share of each line (standard sample 2,200,362), which it recovers as before. On `f8238ea` the surplus moved by
  12 VND more (rounding of that share).
- The contingency lines move with their group: ES# (rate x the ES leaves) +7,493,964 and EM# +813,300 on the standard
  sample.
- `ESS23` is 0 on every case: the standard sample, the clone and the Existing and operating fixtures have in-house
  pool attendants on A1 (2), and the lump fixture's staff cost is an approved lump; each remark says which.
- The client remark gives the median and P25-P75 to one decimal (user's choice), so median x NFA x 12 x VAT
  reproduces the written figure to the rounding of the median.
- Ranges (standard sample; median, P25-P75 in đ/m²/tháng at 2027 prices, projects used): EMB4 56.6, 45.9-78.1, 28;
  ESS12 136.2, 117.3-177.2, 36; ESC5 61.7, 42.2-80.8, 34; ESS7 217.1, 138.9-270.7, 23; ESC1 69.0, 42.5-133.4, 38;
  ESC2 37.7, 22.6-50.5, 29; ESS23 476.5, 332.5-512.1, 15 (not written). The standard sample is invented, so no
  project is left out as itself.
- The regression clone's own budget is in the data file. It is left out by name (its input name carries a trailing
  "(REBUILT AS NEW PROSPECT)"; its NFA differs by 1.9% from the stored one), so each of its ranges has one project
  fewer.
- The analysis workbook's own figures (Summary B19) do not move: the seven lines are deliverable lines only.
- Cells as written (every case): on '2. Budget-Management Fund' only the seven rows change (F, H:S and T; C on ESC1,
  Schedule -> Monthly; T only on ESS23); on '2.2 Common area Fund' only the remark T of six of them (the old zero
  reason goes, ESS23 gets the new one). Totals, EM#/ES# and the `2.2` amounts are formulas and move by recalculation
  only. The analysis workbook only gains the new sheet; the roster is unchanged. Formula cells returning an error: 0
  before and after on every case, both workbooks.
- Every priced figure on `Real-Budget Ranges` equals the sum of its twelve months on the deliverable after Excel
  recalculation (task 2.4), on every case.

**Checks.** 909 unit tests pass on `4e06955` + this change (1 xfail as before; 5 new in `tests/test_real_budget_ranges.py`: the trailing
"(...)", the in-house pool rule, VAT by month, the verification tie / floor / leave-one-out on invented fixtures,
and the name scan). `verify.py` with the two baseline gates opened passes every section (`verify_m2_open3.log`); the
new check passes on the standard, Existing and lump samples. On `f8238ea` its GATE DIFF lines equalled group 7's
except `estimated_surplus_year1` (-421,470,018, `verify_m2_open2.log`); on `4e06955` the only gated figure this change
moves is again `estimated_surplus_year1`, 3,514,899,316 -> 3,093,429,309 (-421,470,006); the other differences are
those of `fix-cleaning-staffing-ratio`. The names-list
scan of the values file ran (store names list present on this PC) and found none.

**Back-test on the regression clone (task 4.2).** The tool's median (with the project left out) against the
project's own budget line at 2027 prices: ESC5 -8%, ESS7 -16%, ESC2 -5% (all three inside P25-P75); EMB4 +27%,
ESS12 -27%, ESC1 +66% (outside). Over the six lines the project carries, the tool is about 9% below its own budget.
The project's own `ESS23` is 0, as the in-house pool rule gives. Cross-checks: ESI1 -30%, EMH1 -5%, EMH3 -11%.
Detail: `Savills-local\budget-test\2026-10-19-laneA-m2\backtest_clone.out`.
- **Sign-off (part 2):** the user, standing in for the Head of PM, accepted these measurements, the back-test, the
  remark wording and the rules recorded on 2026-10-19 (D2, D5, D7, D8) on 2026-10-19 (lane A session P4).
