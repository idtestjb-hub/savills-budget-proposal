## Context

See `proposal.md` for the motivation. The approved rule for each decision is in `PM/Project/docs/30-quy-tac-ap-dung-quyet-dinh-pm-2026-10-11.md`
(outer repository, Vietnamese). This design records how each rule is built. Two names matter throughout:
- `generate_project_budget.py` (GPB) writes the client deliverable and the roster;
- `generate_project_output.py` (GPO) writes the internal analysis.

Current state that shapes the approach (code survey 2026-10-11):

- **Budget period.** `2. Budget-Management Fund!AH6/AL6` keep the template's 01/09/2026–31/08/2027, and no code writes
  them. `1. Summary!H4/H5` say 01/01/2027–31/12/2027. Existing mode prices calendar months 1–12 of the budget year.
- **Two price sources.**
  - New prospects read water 19,786 and diesel 19,260 from `Fact_OPEX.csv` (`estimate_opex.py`).
  - Existing mode reads `Ref_UtilityTariffs.csv` through `utility_tariffs.py`: electricity and water only, with VAT rows
    for both, and a dated `LineTariff.month` helper.
- **VAT.** `ESC12`, `ESM25` and `ESS9` are flat Monthly lines priced excl. VAT. `EEE.C` is ramped and excl. VAT. Every
  remark is closed by `_append_vat`, which says "đã bao gồm VAT".
- **Staffing.**
  - New prospects leave `A1.1` blank, and `EMH3` is a zero-reason line.
  - `EMH2 = A1!AC96/12` already includes `AC90 = A1.1!S13`.
  - `fill_group` writes only as many rows as the template group has.
  - The analysis uses 317 days a year and a ×1.3 loaded night factor. It omits the A1 extras and four position
    categories.
- **Contingency.** `EM#`, `ES#` and `EE#` are template rows inside their group `SUBTOTAL`s, at 0 with reasons.
- **`ESI2`.** It is 0 with a reason, and there is no input for it.
- **Comparables.**
  - `DISTANCE_COMPARISON_ENABLED = False`.
  - The ±20% cap covers the Apartment rate only.
  - Every `MgmtFeeVAT` tag says `incl_VAT`.
- **Other projects' names on the deliverable.** About 20 remark cells name them, the `Comparison` sheet carries names
  and rates, and two fill-up sheets carry template text with names.

## Goals / Non-Goals

**Goals:**
- Build every approved decision so that each one can be measured on its own (an A/B per decision group).
- Keep one source for every rate: one dated tariff and VAT file, one working-day count, one rate resolver and one set
  of `A1` cost constants.
- Re-record the three baselines once, at the end.

**Non-Goals:**
- Changing the template file. Its own defects (the `1. Summary!K42` mis-pointer, the `A5` formulas, C1–C7) go to the
  form owner.
- Changing Existing mode's staffing method, beyond flagging a blank duty table.
- Widening the utility usage basis beyond the one source property (`R-D02`), or resolving "water about 3.3× high".
- Pricing `ERCS`, which waits for residential quotes.

## Decisions

**D1. The budget period is one object, computed once per run.**
- A helper returns the twelve `(year, month)` pairs from the budget start month (default 01/2027).
- GPB writes `AH6`/`AL6` and `1. Summary!H4/H5` from it.
- Every month-dated lookup takes a month from it, never a column index.
- Alternative rejected: fix the period at calendar 2027. A start-month input costs one field and serves pre-opening
  and mid-year budgets.

**D2. One dated rate file, with VAT as its own rows.**
- `Ref_UtilityTariffs.csv` gains rows for:
  - diesel (listed price incl. VAT, with the VAT rate it carries);
  - water, business and administrative base prices;
  - the general VAT rate (8% to 31/12/2026, 10% from 01/01/2027);
  - insurance VAT (10%).
- The existing electricity and drainage VAT rows are replaced by references to the general rate, so the 8%/10% rule
  is stated once.
- `utility_tariffs.py` gains `vat_rate(month, kind)` and a price lookup by line, category and month. New prospects call
  it in place of `Fact_OPEX.csv`'s `UnitPrice`.
- Alternative rejected: a separate `Ref_VATRates.csv`. It would split one rule across two files that must stay in step.

**D3. Usage stays; only the price moves.** New-prospect water and diesel usage per m² keep their stored values. The
water remark's source sentence is chosen from the tariff row's category, not from a substring of `PriceAsOf`. Today a
new date string flips that sentence to a false claim.

**D4. VAT is applied by month at the line, not by switching the line's frequency.**
- `ESC12`, `ESM25` and `ESS9` stay evenly spread. Their month cells become `excl. × (1 + VAT of that month)`.
- `EEE.C` keeps its ramp and gets the same factor.
- When every month carries the same rate, the line can stay `Monthly`. Otherwise it is written per month (`Schedule`).
- Remarks state the rate or rates. The ESS9 remark check reads the month cells, not `F`.

**D5. `A1.1` for a new prospect reuses Existing mode's writer.**
- Duty counts come from Staffing Demand. 24/7 means 7 coverage days and a D or 24H row. Holiday staff = the day shift's
  staff per day. Night staff = the night shift's staff per day.
- A qualifying position with no `A1.1` row gets an inserted row inside the `S12` total, found by label.
- `EMH2` takes Existing mode's form, `(AC96 − AC90 × AC95 + …)/12`.
- `existing_detail_ties` also runs on the standard sample, so a double count fails.

**D6. One working-day function.**
- `vn_holidays` gains a count of a person's working days in a period by coverage pattern. It returns 302 for 2027,
  6-day.
- It replaces `WORKDAYS_PER_MONTH = 25` (new-prospect `A1`), `A1.1!E7:E11` (new prospect), the input form's ÷26 defaults
  and the analysis's 317-day roster.
- Existing mode keeps its own constants, so its staff lines do not move (G2-a).

**D7. `A1` overflow is general.** Every group writes its extra heads into one contiguous block from row 98, together with
the unplaced Reception rows, using `A1`'s own row formulas. `EMH2`'s SUM range and check (d)'s regex keep working on one
block. Zero-pay rows are listed in the run output.

**D8. The analysis matches `A1`.**
- The per-person extras come from `existing_staffing.a1_row_cost`'s constants.
- Night and holiday allowance are priced per shift, as on `A1.1`, and the ×1.3 night factor on loaded cost is
  removed.
- `STAFF_MARKET_KEYWORDS` gains the four missing categories.
- The stale "under 1%" note and the dead `full_payroll_annual_cost` are removed.

**D9. Contingency is a live formula per month.**
- Each month cell (columns `H:S`) of `EM#`, `ES#` and `EE#` is
  `=ROUND(rate × (SUBTOTAL(9, <first leaf>:<row above the contingency row>) − <excluded leaf cells>), 0)`.
- `SUBTOTAL` is used, not `SUM`, because each group holds sub-group header rows that are themselves `SUBTOTAL`s (EMH,
  EMA and EMB inside EM; EEW and EEE inside EE). `SUBTOTAL` skips them, so every leaf counts once.
- The range stops at the row above the contingency row. Because the contingency row is the last row of its group's
  `SUBTOTAL`, a range that included it would be a circular reference.
- Excluded leaf cells: `EMH1` in EM; `EEW.A` and `EEE.A` in EE.
- `2.2 Common area Fund` uses the same pattern with its own rows.
- The rate is written as a literal from the input and stated in the remark.
- Verification asserts that no contingency cell is among its own precedents.
- The analysis adds one contingency row equal to the deliverable's annual sum.

**D9a. A line already priced including VAT gets no second VAT.**
- The VAT-by-month factor applies only to amounts the tool prices excluding VAT: a new prospect's `EEE.C`, plus
  `ESC12`, `ESM25` and `ESS9`.
- These are already gross and are left as they are:
  - Existing mode's `EEE.C` and `EEW.C`: an actual average, or the approved amount repriced through
    `MonthPrice.gross`;
  - the operating path's collect-on-behalf pairs;
  - any amount the PM entered as incl. VAT.

**D9b. Overlap with the open change `carry-forward-common-utilities`.**
- That change created the capability `existing-project-utilities` (still unarchived): `Ref_UtilityTariffs.csv`, its
  VAT rows and the Existing default tariff categories. Group 2 of this change rewrites the same file and rows.
- The Existing water default stays household top tier, as that change approved (the user's choice, 2026-10-11, in
  place of B4-c). Existing mode gains the business and administrative groups as choices only.
- Order (the user's choice): that change's back-test (7.2) and sign-off (7.3) finish and it is archived before group 2
  starts. This change then adds a MODIFIED delta on `existing-project-utilities` for the shared VAT rows and the two new
  water groups (task 2.0). Groups 0, 1 and 3 to 9 do not touch those files and can go ahead meanwhile.

**D10. `ESI2` is an input-driven Monthly line.** Annual = USD × FX × 1.10; `F` = annual / 12. Its `_FLAGGED_NO_METHOD`
entry, `METHOD_VERDICTS` entry and catalogue entry are updated.

**D11. Comparable VAT basis is a hand-checked table.**
- New file `Budget_Agent/data/master_list_verified/Ref_ComparableVATBasis.csv`, with columns project key, product,
  basis (`incl`/`excl`), source text and checked date.
- It is seeded from the raw-text evidence and the hand-verified tags. The user confirms the seed before it is used.
- `resolve_product_rates` converts excl. rates with the budget period's first-month VAT before averaging. Missing
  entries count as incl. and are flagged on the analysis.
- The file sits under the git-ignored data folder like the other reference CSVs.

**D12. Distance tie-break with a general cap.**
- Flip the flag.
- Route every product's rate and the blended fallback through the capped path.
- Update the stale comments and `measured-effect.md`.
- A new invented fixture with coordinates makes `verify.py` reach the path.

**D13. Client wording is chosen at the writer, with a scan as the net.**
- Each of the roughly 20 GPB sites that names a source project gets client wording ("dự án tham chiếu"). The shared
  strings used by the analysis are not edited. GPB passes a `for_client` flag where a helper is shared.
- `scan_internal_wording` gains a name list built from the data and reads formula text too.
- Alternative rejected: a regex rewrite of finished text. It would produce broken Vietnamese and could miss names
  inside formulas.

**D14. `Comparison` sheet split.**
- The deliverable sheet keeps this project's fee per apartment, year-one revenue, income–cost–surplus block and a
  verdict without peer figures. `check_benchmark_reconciles` and `EXPECTED_SHEETS` are updated.
- The peer columns move to the analysis's comparison sheet.
- `_benchmark_fee_clause` tests are updated to the new wording.

**D15. Helper sheets.**
- `A2`–`A4` are filled from the `contract_cost` post lists, with the tool's rate and night blend written into the
  sheet's rate cell, so each total equals `ESS1`, `ESS4` or `ESS16`. Verification adds three tie checks. The canonical
  duty texts stay.
- `B1` is filled from the roster's Reception rows.
- `B2`–`B5` take the tool's figures where it has them. Otherwise their sample values are cleared and the sheet says
  "chưa áp dụng".
- `A5` is untouched.

**D16. Measurement and baselines.**
- Each task group ends with an A/B on the standard sample and on the regression clone, run under
  `Savills-local\budget-test\<date>-p17-<group>\`. The VND movement is recorded in this file under "Measured".
- During the change, `verify.py`'s structural, tie and remark checks must pass. Baseline mismatches are expected, and
  each must be explained by a recorded A/B.
- The baselines are re-recorded once, in the last group.

## Risks / Trade-offs

- **[Risk]** The change is large and will run over several sessions.
  → Task groups are ordered so each can be committed with `verify.py`'s non-baseline checks green, and each group
  records its own A/B before the next starts.
- **[Risk]** Baseline failures during the change hide a real regression.
  → Every baseline mismatch must equal the sum of the recorded A/B movements of the groups built so far. Anything else
  is a defect.
- **[Risk]** Moving water to the business rate raises cost by about 48% while "water about 3.3× high" is unexplained.
  → Every water remark states the usage basis (one source property). The design carries the open issue forward, and
  the user sees the A/B before re-record.
- **[Risk]** Existing samples could move through the shared VAT rows, although their staffing must not.
  → Section 8 asserts the staff lines are unchanged. At equal prices the utility lines must not move. Any utility
  movement is measured separately.
- **[Risk]** The name scan raises false positives on common words.
  → The name list holds full project names only. It excludes this project's own name and is tested on every sample.
- **[Risk]** Inserting rows on `A1.1` shifts the cell references that other formulas use.
  → Rows go inside the `S12` total and are found by label. `A1!AC90` is re-pointed and checked.
- **[Trade-off]** The `ESI2` default of 1,000 USD is an example from the logic file, not a quote. It is labelled as a
  default on the remark, and the PM can overwrite it.
- **[Trade-off]** D5's movement will not equal the +214.4M VND the PM saw (that figure used the analysis's loaded
  basis). The new figure is reported to the user before archive.

## Migration Plan

- **Rollout:** no data migration. New input fields are optional and default when absent, so older input workbooks keep
  running.
- **Rollback:** revert the change's commits and restore the three baseline files from git.

## Open Questions

- C7 (form owner): whether `A1`'s team-building and uniform amounts are monthly or annual. Built as `A1` stands today;
  a later answer changes two constants only.
- The diesel grade label ("DO 0,05S" in docs/19 against "DO 0.005S" in code): taken from the price source when the row
  is added.

## Measured

### Group 1: budget period (2026-10-15, session P20)

Runs under `Savills-local\budget-test\2026-10-15-p17-before\` (default period against the "before" record) and
`...-p17-g1-period\` (July 2027 against the default). Excel-recalculated, cell by cell.

- **Default start (blank, January 2027):** all 32 baseline figures of the standard sample and of the City Garden clone
  are unchanged (0 VND). The only cells that differ in the three workbooks are `2. Budget-Management Fund!AH6/AL6`,
  which now say 01/01/2027 and 31/12/2027 instead of the template's 01/09/2026 and 31/08/2027. Through them the fund
  sheet's twelve month headers read 01/27 to 12/27 (they read 09/26 to 08/27 before), `2.2 Common area Fund` follows,
  and the two summary dates already said the same. A value-preserving fix, but a visible one.
- **July 2027 start, new-prospect sample:** only the dates move (period cells, month headers, the K37 date). No figure
  moves: a new prospect has no date-dependent line in this change's scope yet (VAT by month is group 2, working days
  group 5).
- **July 2027 start, Existing sample:** period cells read Jul/2027 to Jun/2028 on the fund sheet, `2.2` and the summary.
  Two figures move, both through the paid-holiday calendar (366 days and a different holiday set in the 12 months):
  `EMH3` +108,000 VND a year, and `RI1` (the common-area share charged back) +602 VND, so the surplus falls by
  107,398 VND. Electricity and water do not move: the tariff table has one price and one VAT rate from 01/2027.
- **Not covered by the period (stated, not hidden):** the labour-law parameters of Existing mode are still taken for the
  period's first calendar year, so a period that straddles a change in the law uses the first year's values.
- **Sign-off (group 1):** the user, standing in for the Head of PM, accepted these measurements on 2026-10-18.

