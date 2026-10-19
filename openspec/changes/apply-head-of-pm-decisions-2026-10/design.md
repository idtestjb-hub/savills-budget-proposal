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
- `STAFF_MARKET_KEYWORDS` gains the four missing categories (built as `NEW_PROSPECT_STAFF_MARKET_KEYWORDS`, new
  prospects only, with the assistant and supervisor positions split out; see "Measured", task 5.6).
- The employer caps apply per person (added 2026-10-18 at the user's choice).
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
- **As approved by the user on 2026-10-18 (group 6 rules), these points replace the wording above:**
  - The base is read from the template's month-allocation columns, `AQ:BB` on `2. Budget-Management Fund` and `AL:AW`
    on `2.2 Common area Fund`, not from `H:S`. The contingency row is written `Schedule`, with `H:S` holding
    `=ROUND(rate*(SUBTOTAL(9,AQ<first leaf>:AQ<row above>)-AQ<excluded>),0)` and so on per month. Measured on the
    recalculated standard sample: on the fund sheet 1 of 161 leaves (`EMH4`) has `SUM(H:S)` = 0 against a year total of
    10.6M, and on `2.2` 20 of 161 do (its share rows are `Monthly` on `F` only). Yearly and quarterly rows hold a date in
    `H:S`.
  - The rate is the Project Info field "Contingency Rate (EM#, ES#, EE#)" (row 60, read by label). Blank, or an older
    form without the field, gives 2%. 0 gives 0 on all six rows, with a reason that names the field. Text, a negative
    rate or a rate above 10% stops the run and names the field.
  - The energy exclusions are `EEW.A`, `EEE.A` and any other expense line the catalogue pairs as collect-on-behalf.
  - Every mode carries the contingency: new prospect, Existing and operating.
  - On `2.2` the same rule runs over its own rows. `RI1` reads `2.2!AH40`, so it rises by `2.2`'s contingency.
  - The analysis computes its own contingency: the rate times its own costs in the same scope (in-house staff per the
    cost-basis toggle, plus OPEX less repairs), at full occupancy, as a live formula inside Total Profit Value. It
    does not equal the deliverable in VND, because the deliverable is year 1 on the fill-up curve and includes the
    outsourced services.
- **The user's choices of 2026-10-19 (made while building group 6):**
  - "In-house staff" is the analysis's staff cost under the toggle less the Security, Cleaning and Landscape vendor
    contracts (the Service sheet's contract figures, the deliverable's `ESS1`/`ESS4`/`ESS16`).
  - The analysis's contingency is a cost in every total built from staff, OPEX and profit, not only Total Profit
    Value: the fill-up table and the markup on the Summary, the Year 1 Strategy breakevens and deferred cost, Owner
    Operating Position's recurring cost, and a Contingency Reimbursement line on Savills Fee Position, so its full
    package still equals revenue at 100% fill.

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

**D9c. Group 7 rules (B1, B7, B10, K14), as approved by the user on 2026-10-19 (the docs/30 ★ options).**
- `EMH1` keeps its two bases: fixed fee = the monthly fee × 12, even; % fee = the % × the full annual management fee
  (residents plus the developer's top-up), even. Both filled stops the run; both blank leaves 0 with its reason.
- The fixed fee is entered excluding VAT (B1-a) and the tool adds each budget month's VAT (none under KHOÁN). The %
  fee gets no added VAT: its base, the management-fee revenue, already includes it.
- Every `EMH1` remark and the both-filled message name the inputs by label, never by cell address. The `1. Summary`
  `EMH` narrative names the basis actually used (fixed, or the % of the management fee) instead of always "cố định".
- The analysis shows the entered fee on `Savills Fee Position` beside the profit it computes, or "chưa nhập" (B1-b).
- `METHOD_VERDICTS` records the % basis; the catalogue edit goes to the coordinator (shared data folder).
- `ERCS1` stays 0 with the reason "đang chờ báo giá dịch vụ cho chung cư", keeping that no sourced unit price exists.
- `BK507` = `IF(N(BK10)=0,"N/A",-BK505/BK10)`, `BK511` = `IF(ISNUMBER(BK507),BK507+BK509,"N/A")`, found by their
  column-BG labels; a missing label stops the run.
- `1. Summary!K14` always ends with "Doanh thu hạng mục này dự ước tại năm <năm>." (K14-a) and is exempt from the
  generic VAT-sentence check.

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


### Group 2: dated rates, VAT by month, diesel, water, waste (2026-10-18, session P21)

Runs under `Savills-local\budget-test\2026-10-18-p21-g2\` (`r3` = current code on the standard sample and on the City
Garden clone; `ab\` = the Existing and operating fixtures before and after, each on its own tree). Default period
(01/2027), so every month carries 10% VAT. Line totals are the twelve month values of the deliverable.

- **Standard sample, per line (deliverable year 1, VND):**

  | Line | Before | After | Change |
  |---|---|---|---|
  | `EEW.C` water (business group, 29,394 VND/m³) | 82,876,033 | 123,120,293 | +40,244,260 |
  | `EEE.C` electricity (2,226 × 1.10) | 1,837,973,526 | 2,021,770,879 | +183,797,353 |
  | `EED.C` diesel (29,710 ÷ 1.08 × 1.10 = 30,260) | 60,994,764 | 95,831,412 | +34,836,648 |
  | `ESS9` waste (1,087 VND/kg × 1.10) | 512,286,984 | 563,780,208 | +51,493,224 |
  | `ESC12` | 14,000,004 | 15,399,996 | +1,399,992 |
  | `ESM25` | 14,000,004 | 15,399,996 | +1,399,992 |

  Year-1 surplus 4,730,929,441 → 4,419,504,195 (−311,425,246). The six lines add up to +313.2M; the 1.8M difference is
  the common-area charge-back share (`RI1`), which follows the costs. Analysis workbook (full occupancy): water
  306.0 → 454.6M (the 452.6M quoted in docs/30 is the 2026 price; 2027 is 454.6M), diesel 61.0 → 95.8M (94.1M at 2026
  prices), electricity 2,669.4 → 2,936.3M (+266.9M, exactly ×1.10). Total profit value −450.4M; margin 35.7% → 31.7%.
- **City Garden clone:** water +278.5M (573.5 → 851.9M), electricity +500.3M, diesel +65.3M, `ESS9` +95.9M, `ESC12` and
  `ESM25` +1.4M each; year-1 surplus 7,338.4M → 6,401.9M (−936.5M). Completeness against the real budget unchanged:
  42% (50/118 Required lines with a figure above 0). Revenue and the other lines do not move.
- **Existing samples (`Sample_Existing_Input`, `Sample_Existing_Lump_Input`):** `EEE.C` and `EEW.C` do not move at
  equal prices (0 VND), and no staff line moves. They do take the new diesel, `ESC12`, `ESM25` and `ESS9` figures
  (same amounts as the standard sample), because those lines are priced for both modes. Choosing business or
  administrative water for an Existing project moves only water (unit tests on invented prices).
- **Operating sample:** `EEE.C` +266.9M and `EEW.C` +148.6M (it prices these two from the tool, not from actuals);
  its own 38-figure baseline: 9 figures differ, all through these two lines.
- **Mid-period VAT step:** a period starting 10/2026 prices 3 months at 8% and 9 at 10% for water, electricity,
  diesel, `ESC12`, `ESM25` and `ESS9`. Unit tests cover water, diesel and the VAT-by-month list; the per-month write of
  `ESC12`, `ESM25` and `ESS9` when the rate steps is not separately tested (not run on a real period starting 10/2026).
- **Decisions taken in this group:**
  - A new prospect outside Ho Chi Minh City, or with a blank "City / Province", uses the SAWACO (TP.HCM) water prices
    and the remark says to check the local bill (the user's choice, 2026-10-18).
  - Diesel grade label is the price source's, "DO 0,05S-II, Vùng 1" (the user's choice, 2026-10-18); the remark-model
    check for `EED` now requires "DO 0,05S" in place of "0.005S".
  - Diesel has no price before 01/10/2026: a budget period that starts earlier stops with a message naming the month.
- **Open, stated:** QĐ 65/2026/QĐ-UBND is dated 01/09/2026–30/06/2027 (docs/22 A3); a period running past 06/2027
  still uses its price. SAWACO water prices are read from the 2025 page and understood to continue into 2026–2027
  (the same unverified continuation as the drainage charge row). Diesel price source is secondary (a news report of the
  Petrolimex 01/10/2026 listing), not the Ministry notice.
- **Checks:** 704 unit tests pass (1 xfail as before). `verify.py` with the two baseline gates opened (a driver in the
  run folder; baselines are re-recorded once, in group 10): every other check passes on all sections, including
  139 remark assertions, 506 summary reconciliations, 118 Required lines and the Existing and operating samples. With the
  gates closed, it fails only on the 7 OPEX figures above (each equals the A/B).
- **Sign-off (group 2):** the user, standing in for the Head of PM, accepted these measurements on 2026-10-18.

### Group 3: building insurance `ESI2` (2026-10-18, session P21)

Runs under `Savills-local\budget-test\2026-10-18-p21-g3\` (`r1` = standard sample and City Garden clone; `clone_log` =
City Garden with the run log). Both inputs blank (the defaults).

- **`ESI2` on both samples:** 0 → 28,809,000 VND a year (1,000 USD × 26,190 × 1.10; 2,400,750 VND a month). No other
  line of the deliverable moves between group 2 and group 3 (line-by-line comparison, one changed line).
- **Year-1 surplus:** standard sample 4,419,504,195 → 4,390,855,832 (−28.6M); City Garden 6,401,868,441 →
  6,373,246,455 (−28.6M). The surplus falls by a little less than 28.8M because the common-area charge-back follows the
  cost. The analysis workbook carries no insurance line, so its OPEX and total profit value do not move.
- **City Garden completeness against the real budget:** 42% (50/118) → 44% (52/118): `ESI2` now has a figure on both
  fund sheets.
- **Remark** (read from the output): names the 1,000 USD premium and says it is the default for a 1,000,000 USD
  liability limit, the 26,190 VND/USD rate and its date 05/10/2026 (Vietcombank selling rate), the amount before VAT, the
  10% insurance VAT (outside the reduction to 8%) and the total.
- **Rules built:** a blank premium takes 1,000 USD and says so; an entered 0 leaves the line at 0 with a reason that
  names the field (the user's choice, 2026-10-18); text, a negative premium or a zero or negative rate stop the run and
  name the field. Insurance VAT is read from the dated file (10% in every month, also in 2026). Under the KHOÁN model
  (VAT excluded) the line is the amount before VAT, like the other lines.
- **Method records:** `ESI2` leaves the flagged no-method list; a verdict ("matches") is added to the method registry and
  the catalogue row says it is priced.
- **Not measured:** the Existing and operating samples take `ESI2` too (the line is priced in both modes); their
  `verify.py` sections pass, but no separate before/after table was made for them.
- **Checks:** 715 unit tests pass (1 xfail as before). `verify.py` with the two baseline gates opened: every other check
  passes on all sections (139 remark assertions, 506 summary reconciliations, 118 Required lines, method verdicts).
- **Sign-off (group 3):** the user, standing in for the Head of PM, accepted these measurements on 2026-10-18.

### Group 4: comparables, distance cap and VAT basis (2026-10-18, session P21)

Runs under `Savills-local\budget-test\2026-10-18-p21-g4\` (`r1` = standard sample and City Garden clone, default period).

- **VAT basis table `Ref_ComparableVATBasis.csv` (8 rows), confirmed by the user on 2026-10-18 before the tool read it:**
  excl. VAT: Lumi Prestige & Elite, Lumi Signature, Fiato F Zone MF (Apartment, from the hand-verified tags) and
  Rivergate Residence (Apartment, Officetel, Shophouse, Retail, from the raw text "chưa VAT"); incl. VAT: Green Skyline
  (Apartment). Left out on purpose: Hoang Anh Riverview (raw text "(VAT)", meaning unclear) and MT Eastmark (only its
  shop-office rate is stated). Any comparable not in the table is used as including VAT and flagged.
- **Standard sample (no coordinates):** derived Apartment rate 17,175 → 18,892 VND/m²/month (+1,717; docs/30 expected
  about 18,893). Management-fee revenue at full occupancy 11,432.3M → 12,522.3M (+1,089.95M a year, the +1.09 bn docs/30
  quoted). Year-1 deliverable lines: `RM.AP` +290.2M, `RM.KG` +5.0M, `RM.0A` developer top-up +794.8M; no other line moves
  between group 3 and group 4. Year-1 surplus 4,390.9M → 5,476.8M.
- **City Garden clone:** no figure moves. Its comparables are not in the table, so their rates are used as before and the
  analysis flags them ("VAT basis NOT verified", Apartment: two comparables; Officetel: two); the PM-entered rate
  (23,000, excl. VAT) is not converted.
- **Distance (B12):** `DISTANCE_COMPARISON_ENABLED` is on. Neither measured project has coordinates, so no figure moves
  from the distance step here. The cap now covers every product's rate and the blended fallback. Proven on invented
  comparables with coordinates (unit tests and a new `verify.py` section 5i, 8 checks): a within-1 km comparable ranks
  first; a Shophouse, an Apartment and a blended rate that distance would move by 200% are capped at +20%; a 10% move is
  left alone; without coordinates the ranking and every rate equal the no-distance result.
- **Where the effect shows:** the analysis `Comparison` sheet gets a "Comparable VAT basis" line and one "VAT basis NOT
  verified" line per product with the comparables concerned. The client deliverable shows no name (group 9 removes the
  names the older derivation notes still carry).
- **Not covered:** the blended-fallback conversion uses the table's Apartment entry for the comparable. Distance has no
  A/B on a real project (none carries coordinates); the note in `measured-effect.md` of
  `rank-comparables-by-location` says the older figures are out of date.
- **Checks:** 727 unit tests pass (1 xfail as before). `verify.py` with the two baseline gates opened: every other check
  passes on all sections, including the new 5i (139 remark assertions, 506 summary reconciliations, 118 Required lines).
- **Sign-off (group 4):** the user, standing in for the Head of PM, accepted these measurements on 2026-10-18.

### Group 5: new-prospect staff cost (2026-10-18, session P22; measured cluster by cluster, signed off once)

Runs under `Savills-local\budget-test\2026-10-18-p22-g5\` (`a` = tasks 5.1-5.2 on the standard sample and the City
Garden clone, against group 4's `2026-10-18-p21-g4\r1`; `ab\` = the Existing and operating fixtures on `tree_before`
(commit `0acd603`) and `tree_after`). Default period (01/2027). Figures are Excel-recalculated.

**D4, working days (tasks 5.1-5.2).**
- **Count:** Mondays to Saturdays minus the paid holidays of the period, under the law in force on its first day:
  302 for 2027 (by month 25, 20, 27, 24, 25, 26, 27, 26, 24, 26, 25, 27), 302 for 09/2026-08/2027, 303 for 2026 (11
  holidays: 24/11 was not yet in force on 01/01/2026; the user's choice, 2026-10-18). A 7-day position counts 6 days per
  person; 5 days counts Mondays to Fridays (252 in 2027); fewer days count Monday to the N-th weekday (the user's
  choice). One function (`vn_holidays.working_days`, through `generate_project_budget.period_workdays`) for A1, the
  unplaced rows, A1.1 and the analysis.
- **Standard sample:** every A1 gross moves by exactly 302/300 (25 → 25.17 days a month; e.g. Technician 8,125,000 →
  8,179,167). `EMH` staff year 1 4,940,513,881 → 4,971,816,901 (+31,303,020, +0.63%: the per-person extras do not
  scale). Year-1 surplus 5,476,845,924 → 5,445,705,478 (−31,140,446). Analysis: every `Staff (Roster)` row moves by
  exactly 302/317 (−4.7%); staff cost 3,923,305,125 → 3,812,563,147 (−110,741,978); total profit value 4,717.0M →
  4,827.7M; margin 37.67% → 38.55%; markup 60.43% → 62.74%.
- **City Garden clone:** `EMH` staff +60,835,332 (+0.63%); year-1 surplus 6,373,246,455 → 6,312,806,036 (−60,440,419);
  analysis staff cost −243,549,075; total profit value 6,635.7M → 6,879.3M. No other line moves.
- **Existing samples (`Sample_Existing_Input`, `Sample_Existing_Lump_Input`):** 0 figures move and no A1 gross cell
  changes (Existing keeps 25 days a month and the analysis's coverage estimate). The operating sample is a new
  prospect: it moves exactly as the standard sample (`EMH` +31.3M, surplus −31.1M).
- **`A1.1!E7:E11`** now read `=302/12` on a new prospect; no figure moves until `A1.1` is filled (task 5.3).
- **Input form defaults:** every default daily rate with a stated monthly source is now monthly ÷ (302/12) for the default
  period, Security included (the user's choice), e.g. Technician 325,000 → 336,000, Accountant 522,000 → 539,000. The
  sample fixtures were not rebuilt, so the A/B above is the count alone. Not changed: Reception and Cleaning
  (340,000 / 480,000, no monthly source stated) and the older roster-only form `build_roster_input_form.py` (still ÷ 26).
- **Not yet in these figures:** the night ×1.3 loading and the missing A1 extras still separate the two workbooks
  (tasks 5.4 and 5.6), so the 318M gap docs/30 quotes for Diamond Skyline is not re-measured here.
- **Checks (5.1-5.2):** 749 unit tests pass (1 xfail as before). `verify.py` with the two baseline gates opened passes
  every other check on all sections (`verify_a_open.log`).

**B2 + D5, `A1.1` for a new prospect (task 5.3; run `b` against `a`).**
- **Rules built (docs/30 B2 + D5 and the user's choices of 2026-10-18):** night work (30% on the period's non-holiday
  nights, 390% on its holiday nights) = staff per day on D and 24H shifts, for any in-house position with a night shift;
  holiday day work (300%) only for a position on 7-day coverage that has a night shift, with the staff per day of every
  shift that is not a night shift (morning + afternoon; 24H staff count for both day and night). Outsourced Security /
  Cleaning / Landscape are not on A1.1. `H6/L6/P6` come from the period (353 / 12 / 12 for 2027), `D7` (CS) takes the
  same A1 lookup as `D8:D11`, `E7:E11` = 302/12.
- **Built differently from D5's wording:** a qualifying code with no template row (CS, BE, TDS, TN, AA only) gets its own
  row below the table from row 15, with A1.1's own formula chain and a total row (`T` = `S13` + the rows), the same
  place Existing mode's extra rows use, instead of a row inserted inside the `S12` total; inserting rows would shift the
  cells `A1!AC90` and other formulas point at. `EMH3` then points at that total row. Neither sample has such a code; the
  path is covered by unit tests and the widened detail-sheet tie.
- **`EMH2`** takes Existing mode's form, `(AC96 − AC90 × AC95 + unplaced rows × 12) / 12`, so the allowance A1 already
  holds at `AC90` is counted once, in `EMH3`. `check_existing_detail_ties` now also runs on the standard sample (it
  fails on a forced double count, unit test), and counts formula rows below `A1.1`'s table too.
- **Standard sample:** `EMH3` 0 → 172,794,300 a year (Technician 73,027,503, Shift Leader 99,766,800; read back from
  the recalculated `A1.1` and worked by hand). By decision: **D5** night work 117,426,302 (30%: 81,437,101; 390%:
  35,989,201); **B2** holiday day work 55,368,001. `EMH2` unchanged (4,961,249,184), so `EMH` staff year 1
  4,971,816,901 → 5,144,611,201 and the year-1 surplus 5,445,705,478 → 5,273,808,594 (−171,896,884).
- **City Garden clone:** `EMH3` 0 → 423,844,812 (Technician 4 night / 8 holiday-day staff 292,110,012; Shift Leader
  131,734,800). D5 266,308,808 (30%: 184,689,606; 390%: 81,619,202); B2 157,536,004. Year-1 surplus 6,312,806,036 →
  5,891,712,619 (−421,093,417).

**M4-a, the analysis on A1.1's method (task 5.4; run `c` against `b`).**
- The analysis no longer loads night rows by ×1.3 (new prospects; Existing keeps it). A "Night and holiday allowance"
  block on `Staff (Roster)` prices each A1.1 code per shift on the same counts and daily wage, and its rows join the
  category of their positions (Technician, Shift Leader), plain (no insurance or markup, as `A1!AC90`).
- **Tie:** analysis annual allowance 172,794,303 against 12 × `EMH3` 172,794,300 (3 VND: `S13` is rounded to the
  month); City Garden 423,844,812 against 423,844,812 (`allowance_tie.py`).
- **Standard sample:** staff cost 3,812,563,147 → 3,800,190,335 (−12,372,812 = +172,794,303 allowance − 185,167,115
  night loading removed); total profit value 4,827.7M → 4,840.1M; margin 38.55% → 38.65%.
- **City Garden clone:** staff cost +86,226,037 (+423,844,812 − 337,618,775); total profit value 6,879.3M → 6,793.1M.
- **Existing samples:** still 0 figures moved across group 5 so far (`ab\`, tree after 5.4). Operating sample (a new
  prospect): `EMH` staff +204.1M, analysis staff −123.1M, as the standard sample.
- **Checks (5.3-5.4):** 760 unit tests pass (1 xfail). `verify.py` with the baseline gates opened passes every other
  check, including the new detail-sheet tie on the standard sample (`verify_c_open.log`).
- **M4 (for 5.8):** the PM saw +214.4M for D5 on Diamond Skyline on the analysis's loaded basis; on A1.1's method the
  standard sample's D5 is 117.4M. Diamond Skyline itself is not re-run here.

**D6, every head reaches A1 (task 5.5; run `d` against `c`).**
- Each A1 row-group (the Property Manager included) fills its own template rows; the heads beyond them go into the one
  block below the table from row 98, after the unplaced positions (Reception), each with A1's own row formulas and a
  label "<group label> (thêm n)". `EMH2`'s SUM range spans the whole block. A staffed in-house position whose gross is 0
  is printed as a WARNING in the run output and written at 0, not skipped.
- **Fixture (2 Property Managers, 2 Accountants, invented, `overflow\`):** A1 rows 98-99 Reception, 100 "Trưởng Ban
  Quản Lý (thêm 1)", 101 "Kế toán (thêm 1)" (13,564,833 = 539,000 × 302/12); `EMH2` = `(AC96 − AC90 × AC95 +
  SUM(AC98:AC101) × 12) / 12`; the detail-sheet tie and the summary reconciliation (check d, `1. Summary!H22`) pass.
- **Standard sample:** 0 figures move (no group has more heads than template rows).
- **City Garden clone:** 6 heads were being dropped and now reach A1 (a second Property Manager, Chief Engineer,
  Assistant Property Manager and Accountant, and pool attendants 11-12): `EMH` staff year 1 10,118,622,937 →
  12,284,418,889 (+2,165,795,952); year-1 surplus 5,891,712,619 → 3,739,975,963 (−2,151,736,656). Detail-sheet tie and
  summary reconciliation pass on this run. The analysis does not move: it already counts every head, but leaves the
  Accountant / Assistant categories out of its staff cost (task 5.6). docs/30 quoted +239.2M for Diamond Skyline (its
  second Accountant only); not re-run.
- **Checks (5.5):** 765 unit tests pass (1 xfail). `verify.py` with the baseline gates opened passes every other check
  (`verify_d_open.log`).

**D6-b + D7, the analysis costs every in-house head on A1's components (task 5.6, session P23; run `e` against `d`).**
- **Built (the user's choices of 2026-10-18):** new prospects only (Existing keeps its categories and figures, G2-a).
  Every in-house position takes exactly one staff category: Accountant, Cashier, Operations Manager and Technical
  Secretary are added, and Assistant Property Manager, Assistant Chief Engineer and Customer Service Supervisor leave
  the Property Manager, Chief Engineer and Customer Service categories for their own. Necessity: Accountant, Assistant
  Property Manager and Assistant Chief Engineer Must-Have (the assistants as before the split, the user's choice at
  sign-off), Cashier, Operations Manager, Technical Secretary and Customer Service Supervisor Optional. Each category has its market rate (the rows the input form takes its defaults from).
- **A1's per-person extras** on `Staff (Roster)` columns AB:AF, in-house rows only, before the markup: team building
  (1,000,000 a month for the Property Manager, A1 code `PM`; 300,000 for others), training 1.3%, health check 1,350,000
  a year, accident insurance on A1's column X, uniform 300,000 a month. The constants, the accident formula included,
  are one source in `existing_staffing` (`a1_accident_monthly` / `a1_accident_formula`; `a1_row_cost` unchanged).
- **Caps per person** (the user's choice, 2026-10-18): the employer SI/HI, UI and union caps now apply to each person's
  pay (`$AA/12 × $R`), as A1 does, instead of to the row's total of several people. The standard sample has no row
  above the cap; on City Garden the Customer Service (10), Property Manager (2) and Chief Engineer (2) rows were.
- The stale "under 1%" note and the dead `full_payroll_annual_cost` are removed.
- **Deliverable:** 0 figures move (sample, City Garden, the Existing / lump / operating fixtures).
- **Standard sample:** analysis staff cost, Must-Have basis (the headline), 3,800,190,335 → 3,911,986,483
  (+111,796,148); full basis 6,697,061,863 → 6,981,001,356 (+283,939,493, the extras alone); total profit value 4,840.1M
  → 4,728.3M; margin 38.65% → 37.76%.
- **City Garden clone:** Must-Have 14,224,379,747 → 15,128,320,714 (+903,940,967, run `e2`: Accountant +481.4M in,
  extras and caps on the rest; run `e`, with the assistants Optional, read 14,530,008,242); full basis 20,124,434,815 → 21,849,703,854
  (+1,725,269,039; Accountant 481.4M and Cashier 361.0M now costed); total profit value 6,793.1M → 6,487.4M.
- **The two workbooks now agree:** analysis in-house staff cost (full basis less Security / Cleaning / Landscape)
  against the deliverable's `EMH2 + EMH3` for the year: standard sample −283,939,621 (−5.53%) → −128 VND; City Garden
  −1,725,269,357 (−14.06%) → −318 VND (rounding: A1 rounds each row's gross and total).
- **Existing samples:** 0 of 32 figures move, analysis included (`ab\prev_*_after` against `ab\*_after`). Operating
  sample (a new prospect): as the standard sample (+111.8M).
- **Checks (5.6):** 795 unit tests pass (1 xfail), 30 of them new (`tests/test_analysis_staff_categories.py`).
  `verify.py` with the baseline gates opened passes every other check (`verify_e_open.log`).

**Blank duty table in Existing mode (task 5.7, session P23; `blank_duty\`).**
- An Existing input whose 'HOLIDAY AND NIGHT DUTY' block is empty prints a WARNING in the run output, adds a note on
  the Staff Bridge sheet, and opens `EMH3`'s remark with "Bảng trực ca đêm/ngày lễ … để trống: công cụ không tự suy số
  người trực từ mã ca" (`existing_staffing.BLANK_DUTY_TEXT`). With an approved prior-year amount `EMH3` keeps it, as
  before; without one `EMH3` is 0 and its reason asks the PM to fill the table (it used to show the new-prospect
  sentence). The tool never derives duty counts from shift codes.
- **Checked on:** the lump fixture (empty table, approved 30.0M + PM override 31.5M) and a copy of it with the EMH3 line
  cleared (`blank_duty\lump_no_emh3_input.xlsx`); two unit tests in `tests/test_existing_staffing.py`, one with a night
  shift in Staffing Demand that must not become duty counts. No figure moves (text only). 796 unit tests pass (1 xfail);
  `verify.py` with the baseline gates opened passes every other check (`verify_f_open.log`).

**Group 5 per decision, for sign-off (task 5.8).** Diamond Skyline (the docs/30 project) was re-run from its
2026-10-05 input copy on the code before group 5 (`tree_before`, commit `0acd603`) and after task 5.6 (`ds\`), so each
decision lines up with docs/30's figure. Deliverable movements are VND/year on `EMH`; they add up exactly to the
+449,390,016 total.

| Decision | docs/30 (Diamond Skyline) | Diamond Skyline, measured | Standard sample | City Garden clone |
|---|---|---|---|---|
| D4 working days (deliverable `EMH2`) | — | +35,881,692 | +31,303,020 | +60,835,332 |
| D5 night work (`EMH3`) | +214.4M on the analysis's ×1.3 basis | +117,426,302 (A1.1 method) | +117,426,302 | +266,308,808 |
| B2 holiday day work (`EMH3`) | — | +55,368,001 | +55,368,001 | +157,536,004 |
| D6 every head reaches A1 (`EMH2`) | +239.2M (second Accountant) | +240,714,024 (`Kế toán (thêm 1)`) | 0 | +2,165,795,952 (6 heads) |
| D6-b + D7 analysis extras (full basis) | +337.5M | +332,352,104 (AB:AF × 1.1) | +283,939,493 | +684.0M, incl. Accountant / Cashier extras |
| Per-person caps (analysis, full basis; the user's choice) | — | 0 | 0 | +245,926,890 |
| Workbook gap (analysis in-house − `EMH2 + EMH3`) | 318M (docs/24) | −223,375,752 → −106 | −283,939,621 → −128 | −1,725,269,357 → −318 |

- **Deliverable totals:** Diamond Skyline `EMH` +449,390,016, year-1 surplus 4,845,354,962 → 4,398,941,042
  (−446,413,919). Standard sample `EMH` +204,097,320. City Garden `EMH` +2,650,476,096 (D4 + D5 + B2 + D6).
- **Analysis headline (Must-Have basis, final, assistants Must-Have):** Diamond Skyline 4,685,985,778 → 5,154,605,780
  (+468,620,002, `ds\after2`); standard sample +111,796,148; City Garden +903,940,967 (`e2`). Full basis, Diamond
  Skyline 7,731,371,800 → 8,404,137,462 (+672,765,662, of which Accountant 481.4M and Cashier 180.5M now costed). The
  sign-off question first offered the assistants as Optional, which would have taken them out of the headline
  (−299.2M Diamond Skyline, −598.3M City Garden); the user chose Must-Have.
- **Why D5 differs from the +214.4M:** the PM's figure loaded every night row by ×1.3 and then added 13th month,
  insurance and markup; A1.1 pays 30% / 390% / 300% of the daily wage per shift, plain, as the template does (M4-a).
- **Sign-off (group 5):** the user, standing in for the Head of PM, accepted these measurements on 2026-10-18 (session
  P23), with the two assistant categories Must-Have.

### Group 6: contingency `EM#`, `ES#`, `EE#` (2026-10-19, lane A session P2)

Runs under `Savills-local\budget-test\2026-10-18-laneA-g6\`: `before` = code `239bbf3` (standard sample, the City Garden
clone, the Existing, lump and operating fixtures); `after2` = group 6 on the same inputs, plus the variants built by
`make_variants.py` (operating fixture with its collect-on-behalf amounts cleared; standard sample with the rate at 0%,
3%, a text value and 11%). Figures are Excel-recalculated (`cont_check.py`, `ab_table.py`, `ab_g6.json`). Default
rate 2% (no fixture has the new field).

**Built (rules of 2026-10-18 and the user's choices of 2026-10-19).**
- New module `contingency.py`: the rate (`Contingency Rate (EM#, ES#, EE#)`, Project Info row 60, read by label), the
  layout found by code and checked against the approved rows, the month formulas and the remarks. GPB writes the six
  lines (`_write_contingency_lines`) and `1. Summary` K25/K35/K42 (`_write_contingency_narratives`); EM#, ES# and EE#
  leave `_FLAGGED_NO_METHOD` and join `MGMT_FUND_ROWS`. Month formula, e.g. `2. Fund!H131` =
  `=ROUND(0.02*(SUBTOTAL(9,AQ82:AQ130)-AQ82),0)`; `2.2!H223` = `=ROUND(0.02*(SUBTOTAL(9,AL190:AL222)-AL190-AL200),0)`.
- Analysis (the user's choices of 2026-10-19): a CONTINGENCY block on `Cost Priority` = rate × (in-house staff, i.e. the
  staff total less the Security / Cleaning / Landscape vendor contracts, + OPEX less Repairs & Maintenance), on the
  Must-Have and Full Cost bases; the Summary's toggle picks one (`Selected Contingency`, on the old spacer row, so
  Total Profit Value stays at B19). It is a cost everywhere costs are summed: Total Profit Value, the fill-up table, the
  markup, Key Figure (10), the Year 1 Strategy breakevens and deferred cost, Owner Operating Position's recurring cost
  and a Contingency Reimbursement line on Savills Fee Position (its full package still equals revenue at 100% fill).
- `verify.py` gains `check_contingency` (sections 8 and 9: the standard, Existing, lump and operating samples).

**Per line, year 1 (VND).**

| Case | `2. Fund` EM# / ES# / EE# | `2.2` EM# / ES# / EE# | Analysis contingency (Must-Have) |
|---|---|---|---|
| Standard sample | 104,565,768 / 51,991,740 / 44,814,453 | 543,072 / 270,024 / 232,752 | 117,458,666 |
| City Garden clone | 249,121,980 / 216,515,208 / 130,685,580 | 1,617,180 / 1,405,512 / 848,352 | 259,717,591 |
| Existing sample | 136,462,812 / 51,991,740 / 26,476,776 | 708,732 / 270,024 / 137,508 | 74,427,055 |
| Existing lump sample | 77,903,544 / 51,991,740 / 20,030,892 | 404,592 / 270,024 / 104,028 | 67,981,169 |
| Operating sample | 104,565,768 / 51,991,740 / 69,734,760 | 696,432 / 346,272 / 464,448 | 117,458,666 |

**Headline movements.** Year-1 surplus moves by −(the `2. Fund` contingency) + (RI1's rise, which equals the `2.2`
contingency, because RI1 reads `2.2!AH40`); total expense (`1. Summary!H20`) rises by exactly the `2. Fund` contingency.

| Case | Year-1 surplus | of which RI1 | Total Profit Value | Margin | Markup |
|---|---|---|---|---|---|
| Standard sample | 5,273,808,594 → 5,073,482,481 (−200,326,113) | +1,045,848 | 4,728,323,743 → 4,610,865,077 (−117,458,666) | 37.76% → 36.82% | 60.67% → 58.28% |
| City Garden clone | 3,739,975,963 → 3,147,524,239 (−592,451,724) | +3,871,044 | 5,889,113,203 → 5,629,395,612 (−259,717,591) | 20.95% → 20.03% | 26.51% → 25.05% |
| Existing sample | 4,599,361,028 → 4,385,545,964 (−213,815,064) | +1,116,264 | 6,879,904,278 → 6,805,477,222 (−74,427,055) | 54.94% → 54.35% | 121.93% → 119.04% |
| Existing lump sample | 7,832,738,452 → 7,683,590,920 (−149,147,532) | +778,644 | 7,202,198,598 → 7,134,217,428 (−67,981,169) | 57.52% → 56.97% | 135.38% → 132.41% |
| Operating sample | 551,544,459 → 326,759,343 (−224,785,116) | +1,507,152 | 3,161,282,143 → 3,043,823,477 (−117,458,666) | 28.86% → 27.78% | 40.56% → 38.47% |

No literal line of `2. Fund` moves in any case (`lines_diff.py`, every twelve-month total); RI1 rises by exactly the `2.2` contingency, so no other `2.2` line moves in total; Total Profit Value falls by exactly the analysis contingency, so revenue, staff, OPEX and capex do not move.

**COM read-back (`cont_check.py`, every case).**
- Each month of the six lines equals ROUND(rate × (the template's group total − the line itself − the excluded
  leaves)), and equals ROUND(rate × the plain sum of the leaf rows − excluded); G = SUM(H:S).
- No circular reference on any sheet of either workbook (Excel's `CircularReference` after a full recalculation), and
  every formula range ends on the row above its line. False negative: Excel names only the first loop per sheet.
- `1. Summary` H25/H35/H42 equal the fund cells they read (AK120 + AK131, AK220 + AK221, AK262); K25/K35/K42 carry the
  contingency item (the template's K42 pulled the diesel remark T251).
- Analysis: same rate as the deliverable; contingency = ROUND(rate × (in-house staff + OPEX less repairs)) on both bases;
  Total Profit Value = revenue − staff − OPEX − capex − contingency; Savills Fee Position package = revenue.
- Only error cells: `2. Fund` BK507/BK511, inherited from the template and present before (task 7.3).
- **Collect-on-behalf:** the operating sample with its pairs (310,000,000 + 455,000,000 + 27,500,000 a month) and
  without them give the same surplus (326,759,343), the same EE# (69,734,760) and the same Total Profit Value.
- **Rate 0%:** all six lines 0 with "Để ở mức 0: ô 'Contingency Rate' trên Project Info là 0%." (the `2.2` lines copy it),
  K25/K35/K42 say so, and the surplus and Total Profit Value equal `before` exactly. **3%:** `2. Fund` contingency
  302,057,946 (1.5 × the 2% run, within the month rounding). **Text / 11%:** the run stops naming the field.

**Checks (6.1-6.2):** 822 unit tests pass (1 xfail as before; 26 new in `tests/test_contingency.py`, including the verify check failing on a range that reaches its own line, on a wrong month and on a second rate). `verify.py` with the two baseline gates opened passes every other check on all sections, the new contingency check included (`verify_g6_open.log`); the gated figures differ from the recorded baseline by groups 1-6 together, and their current values equal the `after2` column above (total profit value 4,610,865,077; year-1 surplus 5,073,482,481).

**Catalogue.** `Costing_Method_Catalogue.csv` is in the shared data folder: the coordinator applies EE# →
`percent-of-section` and adds EM# / ES# with tonight's merge. Until then `method_coverage.METHOD_VERDICTS` records the
three lines as `matches` (Head of PM decision B6).
- **Sign-off (group 6):** the user, standing in for the Head of PM, accepted these measurements and the remark wording
  (the Project Info pointer kept) on 2026-10-19 (lane A session P2).

### Group 7: Savills' fee `EMH1`, `ERCS1`, `BK507`/`BK511`, `1. Summary!K14` (2026-10-19, lane A session P3)

Runs under `Savills-local\budget-test\2026-10-19-laneA-g7\`: `before` = code `761aa37` (main with groups 6 and 8),
`after` = group 7, both on the standard sample, the City Garden clone, the Existing, lump and operating fixtures and
four variants of the standard sample (`make_variants.py`): `fee_fixed` ('Fixed Monthly Fee' = 50,000,000 VND/month),
`fee_pct` ('% of Collected Management Fee' = 10%), `fee_both` (both) and `fee_fixed_1026` (`fee_fixed` with 'Budget
Start Month' = 10/2026, after only). Figures are Excel-recalculated
(`g7_check.py`, `ab_table.py`, `ab_g7.json`); every cell as written is compared by `compare_cells.py`.

**Built (rules D9c).**
- New module `savills_fee.py`: the two labels, the basis, the stop message, the fixed-fee line (entered excl. VAT,
  each budget month's VAT added, none under KHOÁN), the % line (% x the full annual fee at 100% occupancy, RM + RM.0A,
  no VAT added), the zero reason, the `1. Summary` fee clause and the analysis rows. GPB `read_input` (stop message),
  `fill_management_fund_sheet` (EMH1 write and zero reason) and `_recipe_narrative` ('EMH' fee clause; 'RM' revenue
  sentence) call it. No remark or message cites a cell address any more (`Project Info!B36/B37`, `B34/B35`, "hàng 14-22").
- `ERCS1_REASON_VI` (GPB): "Đang chờ báo giá dịch vụ cho chung cư; …chưa có đơn giá nào có nguồn trích dẫn…".
- New module `breakeven_cells.py`: finds the BG labels "Gía dịch vụ quản lý cân bằng" / "… cần tăng / giảm" (once each,
  else the run stops), checks the template's BK expressions and wraps them: `BK507 = IF(N(BK10)=0,"N/A",-BK505/BK10)`,
  `BK511 = IF(ISNUMBER(BK507),BK507+BK509,"N/A")`. Called at the end of `fill_management_fund_sheet`.
- `1. Summary!K14` ends with "Doanh thu hạng mục này dự ước tại năm 2027." on every run; `check_remark_content` checks
  that (new `k14_revenue_sentence_problem`) instead of the generic VAT sentence there.
- Analysis `Savills Fee Position`: a display-only block "SAVILLS' FEE ENTERED ON PROJECT INFO (EMH1)" (basis, entered
  value, fee per year, and the computed profit beside it); "chưa nhập" when blank. Nothing sums it.
- `METHOD_VERDICTS['EMH1']`: `mismatch` -> `matches` (Head of PM decision B1 sets the two bases). Input-form builder
  source: the fixed-fee label and comment say excl. VAT (the builder was not run).

**Measured.**
- **Standard sample, City Garden, Existing, lump, operating (no fee entered):** 0 figure moves (total expense, surplus,
  Total Profit Value, full package, EM# on both sheets). Cells as written: exactly 8 change on each deliverable
  (`1. Summary` K14 and K22, `2. Fund` T82, T480, BK507, BK511, `2.2` T43, T441); on the analysis only
  `Savills Fee Position` changes (the new block shifts the rows below it): 240 cells (196 on the clone and the
  operating sample), per-sheet tally of `compare_cells.py` on all five cases.
- **`fee_fixed`:** EMH1 600,000,000 -> 660,000,000 (55,000,000 a month: 10% VAT in every month of 2027); total expense
  +60,000,000; surplus -59,688,387 (RI1 rises by the `2.2` share, 3,116,131 -> 3,427,744); Total Profit Value, the full
  package and EM# unchanged (EMH1 is outside the EM# base). Analysis block: 50,000,000 / 600,000,000 excl. VAT.
- **`fee_fixed_1026`** (VAT changes inside the period): EMH1 is written month by month (C = Schedule, G = SUM(H:S)):
  10-12/2026 at 54,000,000 (8%), 01-09/2027 at 55,000,000 (10%), 657,000,000 a year; the remark says "cộng VAT 8% đến
  hết tháng 12/2026 và 10% từ tháng 01/2027 theo từng tháng = 657,000,000 VND/năm" and the K22 clause quotes the same
  657,000,000; EM# unchanged; no error cell.
- **`fee_pct`:** EMH1 1,252,229,160 before and after (10% x 12,522,291,600, no VAT added); the analysis block shows
  the same 1,252,229,160 from `'Management Fee'` at 100% fill, so the two workbooks agree.
- **`fee_both`:** the run stops: "Project Info 'Fixed Monthly Fee' and '% of Collected Management Fee' are BOTH filled
  in…" (was "Project Info!B34 … B35").
- **BK507/BK511 (every case):** "N/A" at parking area 0; after typing 1,000 m2 into `'0. Info'!D12` on a copy, both
  give numbers (standard sample BK507 = -8,400.57 = -BK505 / 1,000; BK511 = BK507 + BK509). Formula cells returning an
  error on the deliverable: 2 -> 0 in every case (Excel `SpecialCells`); BJ untouched.
- **Remarks:** K14 ends with the revenue sentence and has no generic VAT sentence; the EMH narrative names the basis
  used ("cố định" only for a fixed fee); ERCS1 carries the new reason on both fund sheets.

**Checks:** 879 unit tests pass (1 xfail as before; 21 new in `tests/test_savills_fee.py`, including no cell address
in any EMH1 text, the both-filled stop through `read_input`, a changed or doubled break-even label stopping the run,
and the K14 check). `verify.py` with the two baseline gates opened passes every check on all sections
(`verify_g7_open.log`), the remark checks included on the standard, Existing, lump and operating samples; its GATE
DIFF lines are identical to group 6's (`verify_g6_open.log`), so group 7 moves no gated figure. Errors inherited
from the blank template: 5 (group 6) -> 0: the helper sheets' 3 went with group 8, BK507/BK511 with this group.

**Catalogue.** `Costing_Method_Catalogue.csv` (shared data folder): the coordinator applies the EMH1 row with the
lane-a merge (method: fixed fee excl. VAT + monthly VAT, or % of the full management fee, no VAT added; inputs by label).

**Open points (not changed):** a PM-entered RM rate marked excl. VAT makes "the base already includes VAT" untrue for
the % fee. K15 (parking revenue) still ends with the generic VAT sentence. The live input form gets the "excl. VAT"
label only when the coordinator rebuilds it.
- **Sign-off (group 7):** the user, standing in for the Head of PM, accepted these measurements, the remark wording,
  the `EMH1` verdict `matches` and the new input-form label on 2026-10-19 (lane A session P3).

### Group 8: helper sheets A2-A4, B1-B5 (2026-10-19, lane B session P2)

Runs under `Savills-local\budget-test\lanes\B\ab\` (`before2` = commit `239bbf3` from a detached worktree, `g8` = the
lane-B working tree; both on the same data, standard sample and the City Garden clone). The first "before" run
(`before`, 2026-10-18) showed 6 cells moving on the analysis's `Service Levels` sheet: `data/service_levels/
Ref_ServiceLevelProjects.csv` was rebuilt after it (lane C's NFA fix), so `before` was re-run as `before2` on today's
data; `before` and `before2` agree on all 32 baseline figures.

**Rules applied (the 17 rules of the lane-B note, the user's OK of 2026-10-18/19).**
- **A2-A4:** people on an 8-hour shift (E = 8), relief for the weekly day off included (x 7/6, rounded up), at the
  line's post rate x night blend written into the rate cell (`A2!G3 = 17,500,000 x 1.0882`, `A3!J3`, `A4!J3`), all
  recorded once by `contract_cost` and not worked out again. Posts go on their standard row (main gate A4, CCTV A2,
  patrol A6, side gate A5, FCC A3; cleaning A3 / clubhouse A4 / parking C1; gardener L3); a post with no standard row
  goes on the group's main row with a note (the user's choice, 2026-10-19: the sheets have no blank row); a supervisor
  goes on the unpriced row (A3 A1, A4 L1) or is named in A2's notes. Night and 24h cleaning or landscape people go in
  the standard-shift column with a note (the user's choice). Every other standard row keeps its name and duty text at
  quantity 0. A2's 24h-conversion block counts the 8-hour rows (`E35` 16 -> 8).
- **B1:** the roster month (Roster Setup; blank = the budget's first month; 09/2026 on every sample), real weekdays,
  the roster's rest rule, one row per person; more than five people: five rows and a note (the user's choice). The
  weekly and daily parts say "Chưa áp dụng" and lose their sample codes, `#REF!` included.
- **B2-B5:** B3 garbage = ESS9's units x 100% x kg/unit/day x 30 x 1,087 VND/kg (staff and visitor rows "Chưa áp
  dụng"); B4 = the RA1.A/RA2 devices and rates; B5 part B = RP1/RP2 monthly prices for this project (part A, the
  reference projects, not filled); B2 and B3 consumables "Chưa áp dụng" with the sample quantities and prices cleared,
  norms kept. The form's `#REF!` cells (B1 `B42`/`C42`, B3 consumables `Q13`) are removed; they go on the form-owner
  list.

**Measured.**
- **Fund figures:** 0 of the 32 baseline figures move, on both samples (`compare_runs.py before2 g8`).
- **Every cell outside the helper sheets** (formulas and constants as written, all three workbooks): 0 differences on
  both samples (`compare_cells_lane.py before2 g8`; 756,531 + 756,759 deliverable cells). Helper-sheet cells changed:
  448 (standard sample), 402 (City Garden).
- **Excel read-back (`helper_read.py`):**

| | Standard sample | City Garden clone |
|---|---|---|
| `A2` x 12 / `ESS1` | 1,294,958,000 / 1,294,958,004 (17 people) | 4,367,853,000 / 4,367,853,000 (57) |
| `A3` x 12 / `ESS4` | 288,000,000 / 288,000,000 (3 + 1 supervisor unpriced) | 4,416,000,000 / 4,416,000,000 (46 + 1) |
| `A4` x 12 / `ESS16` | 264,000,000 / 264,000,000 (2) | 792,000,000 / 792,000,000 (6) |
| `B4` x 12 / `RA1.A + RA2` | 82,545,456 / 82,545,456 | 222,181,824 / 222,181,824 |
| `B3` garbage x 12 / `ESS9` (incl. VAT) | 512,527,457 / 563,780,208 | 954,042,073 / 1,049,446,284 |
| `EMH4` | 10,567,717, unchanged | 10,567,717, unchanged |
| Error cells on the helper sheets | 3 -> 0 | 3 -> 0 |
| `B1` reception | 2 people, 09/2026 | 4 people, 09/2026 |

  Before group 8 the sheets showed the form's samples: `A2` x 12 = 4,550,000,000 and `A3` x 12 = 1,530,000,000 on both
  samples.
- **Checks:** `check_helper_sheet_ties` (new; ESS9 compared before VAT, tolerance 12 VND a year) passes on the standard
  sample, both Existing samples and the operating sample inside `verify.py`. 814 unit tests pass (18 new in
  `tests/test_helper_sheets.py`), 1 xfail as before.
  `verify.py` with the two baseline gates opened (`lanes/B/ab/verify_gate_open.py`, log `verify_g8.log`) passes every
  other check on all sections; the gates report the same 11 / 6 / 0 / 10 baseline differences as at the end of group 5
  (`2026-10-18-p22-g5/verify_g_open.log`), so group 8 moves no recorded figure.
- **Sign-off (group 8):** the user, standing in for the Head of PM, accepted these measurements on 2026-10-19
  (lane B session P2).

### Group 9: client wording, `Comparison` split, name scan (2026-10-19, lane B sessions P2-P3)

Runs under `Savills-local\budget-test\lanes\B\ab\`: `g9before` (main `761aa37`, groups 1-8 and lane A's group 6) and
`g9` (group 9), on the standard sample and the City Garden clone (`run_lane.py`). Rules the user approved on
2026-10-19 (lane B session P2): every GPB site that names a source project says "dự án tham chiếu"; strings the
analysis shares keep the names; the fill-up sheets' template names are overwritten by coordinate; the deliverable's
`Comparison` keeps this project's column only and the peer columns move to the analysis; the name list is built from
the data (NFC, casefold, word boundaries, names of 4 or more characters, generic-word-only names dropped), formula text
is read, and this project's own name is excluded.

**Built.**
- **9.1:** remarks `ESS1/4/16`, `RM.*`, `RP1/RP2`, `EEW.C/EEE.C/EED.C`, `EMA15`, `ERM`, `EMB1/EMB4` (and their copies
  on `2.2 Common area Fund` T76/T79), `EN1`-`EN4` say "dự án tham chiếu"; `ESM4` takes the new
  `method_client`/`source_client` of `estimate_opex._pool_salt`. The four fill-up cells are overwritten (form-owner
  list below).
- **9.2:** `add_comparison_sheet` writes columns A-B only: this project's overview, the rate and how it is set (no raw
  derivation note: it can name a comparable or quote its rate), fee per apartment, year-1 revenue, the
  income-cost-surplus block and the verdict. The sheet states which line is the peer comparison (drawn from the
  reference projects' real rates, listed in the analysis) and which is an internal check. `build_comparison_sheet`
  (analysis) gains a PEER BENCHMARK block: each comparable's rate on one VAT basis, fee per apartment (approximation,
  upper bound), year-1 revenue re-priced at its rate (labelled a projection), the range and the client verdict text.
  `_benchmark_fee_clause` names no project and quotes no peer rate or range end; the basis stays the Apartment rate
  (user, 2026-10-19; spec `proposal-benchmark` amended). `check_benchmark_reconciles` fails on any value past column B
  of the deliverable's `Comparison`, and reads the projections from the analysis, failing when a rated comparable has
  none. `EXPECTED_SHEETS` is unchanged (both workbooks keep `Comparison`).
- **Found and fixed in 9.2:** the verdict compared the VAT-converted average (group 4) with the comparables' rates as
  quoted. `resolve_product_rates` now returns `apartment_rates_on_basis`, and the verdict and projections use it.
  Standard sample: "5% above the higher comparable" became "within the range" (18,892 against 17,985-19,800 on one
  basis). City Garden: "37% above" is unchanged (PM-entered 23,000 against 11,000-16,800).
- **9.3:** `checks.project_names_from_data` (179 names), `scan_internal_wording` reads formula text and the name list,
  `check_remark_content` passes the list and this project's name (`2. Budget-Management Fund`!AH5).

**Form-owner items from group 9 (template text the generator overwrites, D13).** The rest of the form-owner list: `1. Summary!K42`, `A5` and C1-C7 (Non-Goals, Open Questions) and the `#REF!` cells of group 8. `Tỷ lệ lấp đầy cư dân`!AO27, AO28, A38 and
`Tiến độ lấp đầy bãi xe`!B42 ship text naming other projects (AO27 with a misspelt name found in no data file); the
generator writes neutral text there (`_FILLUP_NOTE_*` in GPB). The form owner should remove the names from the
template.

**Measured.**
- **Fund figures:** 0 of the 32 baseline figures move, on both samples (`compare_runs.py g9before g9`).
- **Every cell** (formulas and constants as written, all three workbooks, `compare_cells_g9.py g9before g9`): 0
  differences outside the expected places on both samples. Expected places: deliverable `Comparison` (96 cells
  standard sample, 99 City Garden), remark column T (21 / 20 cells), fill-up sheets (4 / 4), analysis `Comparison` (36
  / 36).
- **Names in the deliverable** (`name_scan.py`): 27 -> 0 cells (standard sample), 26 -> 0 (City Garden). The analysis
  still names the comparables (`analysis_names.py g9`: 22 cells standard sample, 29 City Garden; `Comparison`,
  `OPEX`, `Capex`, `Management Fee`, `Additional Revenue` and others).
- **Excel read-back (`cmp_read.py`):** the deliverable `Comparison` uses A1:B33 (standard) and A1:B34 (City Garden);
  the verdicts are as above. Standard sample analysis: year-1 revenue 12,522,291,600 VND, re-priced at the two
  comparables 13,088,883,600 and 11,956,323,600; fee per apartment 2,046,633 VND against 2,541,748 and 1,805,491
  (approximations, upper bound).
- **Checks:** 870 unit tests pass (`tests/test_client_wording.py` 10, rewritten `test_fee_clause_*`, 2 new in
  `tests/test_rate_resolver.py`), 1 xfail as before; a name planted in a formula and a value planted in column C
  each fail their unit test. `verify.py` with the two baseline gates opened (`lanes/B/ab/verify_gate_open.py`, log
  `verify_g9.log`) exits 0: 5c reconciles 6 PROPOSAL BENCHMARK figures (4 own cells, 2 analysis projections), 5d and
  sections 8-9 pass remark content with the name scan; the gates report the same 11 / 6 / 0 / 10 baseline
  differences as at the end of group 8, so group 9 moves no recorded figure.
- **Sign-off (group 9):** the user, standing in for the Head of PM, accepted these measurements on 2026-10-19 (lane B
  session P3), and accepted the VAT-basis fix to the verdict as a separate item.
