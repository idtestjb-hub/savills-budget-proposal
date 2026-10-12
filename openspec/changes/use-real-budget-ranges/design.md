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

### D8. Which projects a line applies to
- `ESS23` only when "Has Swimming Pool?" is Yes.
- `ESS7` (façade cleaning): only 16 of the 50 usable budgets carry it.
  - **Approved by the user on 2026-10-12:** apply it only when the input has at least one tower ("Tower Count" ≥ 1).
  - Without a tower it stays at 0 with a stated reason.
- Every other code in scope applies to every project.

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
