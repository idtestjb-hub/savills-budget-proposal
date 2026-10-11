## Context

See `proposal.md` (Why) for the 2026-10-07 rebuild of the stable-operation reference project. Its
data stays outside this repository, under `Savills-local\budget-test\`, in the comparison folder
dated 2026-10-07. That folder holds:
- the comparison workbook (8 sheets, including the line-by-line comparison and the "real rates" run);
- the clone that was run (`run\`);
- the input-filling script and the original `fill_curve.py`.

The folder's name identifies the client, so it is not written here.

The current code paths these proposals touch:
- **Rate derivation.** In `generate_project_budget.py`:
  - Apartment, in `build_budget()` (~3131), which falls back to the blended `derive_mgmt_rate`
    when no comparable has an Apartment rate. Apartment again in `fill_management_fund_sheet()` (~1952).
  - Non-Apartment products in three places: the fund-sheet loop (~1989), the `0. Info` fee table
    (~3217) and the complete-total note for products the table has no row for (~3253).

  In `generate_project_output.py`, Apartment at ~231 and the other products at ~298. That file has
  no blended fallback. The comparison run had to patch four of these sites, and missed the analysis
  generator. Its analysis workbook still shows the comparable-derived Apartment rate.
- **Fill-up.** `fill_curve.py` holds `MONTH_ANCHORS` (0% → 50% → 70% → 90% → 100% over 48 months)
  as a constant. Both generators import `year1_fills`, `year1_electricity_fills`, `parking_fills`
  and `monthly_fill_path`. `_anchor_note_vi()` in the deliverable generator hard-codes the "0% → 50%"
  narrative.
- **Parking.** `PARKING_FEE_CAR_MONTHLY` / `PARKING_FEE_MOTO_MONTHLY` are constants in
  `generate_project_output.py`, imported by the deliverable generator. `RP1`/`RP2` are written as
  bays × rate × parking fill. The `1. Summary` narrative quotes the per-bay rate from `_UNIT_RATES`.
  `BM11` (monthly-parking allocation weight) is set to the full monthly parking revenue, and `BN11`
  is set to 0.
- **Collect-on-behalf.** The template carries revenue rows `RO3.A/T/O/M/R/S/L` (water) and
  `RO4.A/T/O/M/R/S/L` (electricity). It also carries expense rows `EEW.A` / `EEE.A` (residents' own
  use) and per-zone common-area rows `EEW.AA/T/O/M/R/S/P` and `EEE.AA/T/O/M/R/S/P`. The catalogue
  marks `RO3.A`, `RO4.A` and `RO23` "not-estimated" ("the VPC budget does not estimate thu-hộ
  revenue") and has no entry for the other `RO3.*`/`RO4.*` rows. The pipeline writes none of them.
- **Input reading.** `read_input()` in the deliverable generator is shared by both generators. It
  reads product rows by label (columns B–D). An absent product row reads as zero. An absent scalar
  label fails, except optional ones guarded by `L.has()` (`Operating Years to Budget`).

## Goals / Non-Goals

**Goals:**
- One place decides each product's rate. An entered rate then needs one code path, and both
  workbooks cannot disagree.
- An operating project can be described honestly on the form: real rates, stable occupancy,
  recorded parking revenue and collect-on-behalf amounts.
- With the new fields blank, every figure is byte-for-byte what it is today.

**Non-Goals:**
- **Expense-side inputs** the reference rebuild lacked: garden area, internal road area, insured
  asset value. These are input completeness, not code.
- **Lines the pipeline has no source for** (most `RO*` income, many `ESS*`/`ER*` contracts) and
  the staff-cost gap on `EMH2`.
- **Developer parking scenarios:** `RP8`, `ESS38`, `RM.PA`.
- **`RI1` and the `2.2 Common area Fund` allocation basis**, which is already pending with the PM.
- **VAT conversion** of any entered figure (PM-1 below).
- **The product-code mapping** of a commercial area that the master list calls retail and the form
  calls officetel. On the reference project the same area sits on `RM.RE` in the real budget and on
  `RM.OT` in the tool's output.
- **Excluding a real project from its own comparable set** when its name in the input differs from
  the master list (see Risks).

## Decisions

### D1 — One rate resolver, called once per generator run (P5)

A function next to the existing rate functions in `master_comparables.py` takes the project as read
from the input. For each product with area it returns the applied rate, the source kind (`entered`,
`comparable`, `apartment-fallback`, `blended-fallback`), the comparables used, the note and the
VAT basis. It also returns the ranking that the `Comparison` sheets show.
- `build_budget()` calls it once and passes the result to `fill_management_fund_sheet()`, the
  `0. Info` table, the complete-total note and `add_comparison_sheet()`.
- The analysis generator calls it once in its `Management Fee` section.
- No site derives a rate on its own any more.

*Alternatives:*
- Compute the rates inside `read_input()`, which both generators already share. Rejected: that mixes
  derivation into input reading, and the reading spec says reading must not change any figure.
- Compute once in `run.py` and hand the result to both generators. Rejected: each generator must
  still run on its own (RUNNING.md).

P5 lands before P1. It is accepted only if the before/after deliverable and analysis agree in every
formula and number, on the standard synthetic project and on the existing three-product test copy
in `Savills-local\budget-test\`. The analysis generator gains the blended fallback. The synthetic
sample does not reach that path, so the A/B shows no difference there; a unit-level test covers it.

### D2 — Entered rate: two columns on the product rows (P1)

The product mix block gains two columns: `Actual Rate (VND/m²/month)` and `Rate VAT Basis`, the
latter a list of `incl. VAT` / `excl. VAT`. Both are found by their header text in the block's header
row, not by column letter. A form without the columns reads every rate as blank (D6).
- Inside the resolver, an entered rate ranks first and is not passed through
  `derive_product_rate_capped`'s swing cap.
- When Apartment's rate is entered, it is also the fallback for products with neither an entered
  rate nor a comparable rate. "The project's Apartment rate" then means the rate actually applied.
  This moves a fallback-priced product along with Apartment, and the sign-off covers it.
- The `Comparison` sheet keeps the comparables. Its benchmark clause compares the entered rate with
  them and labels it as the PM's figure.

Draft remark, to be approved by the user before it is written:
> = Đơn giá {sản phẩm} thực tế do PM nhập ({rate} VND/m²/tháng, {đã gồm / chưa gồm} VAT) x Diện tích
> tính phí {sản phẩm} ({nfa} m²) = … VND/tháng ({annual} VND/năm).

When the entered basis differs from the deliverable's basis, this sentence is added:
> Lưu ý: đơn giá nhập {chưa gồm} VAT, số liệu ngân sách này trình bày {đã gồm} VAT; chưa quy đổi.

*Alternatives:*
- Use the project's own row in `Dim_Property_Residential.csv` automatically; the code already finds
  it as `own_real`. Rejected: all 105 rows carry the same VAT tag (docs/22 D8), so the basis is
  unknown. The list can be stale. And a rate that appears from the master list is less auditable
  than one the PM typed.
- An environment-variable override, as in the comparison run. Rejected: a PM cannot use it.

### D3 — Stable-operation switch as an explicit parameter of the curve (P3)

A `Stable Operation?` Yes/No label sits beside `Operating Years to Budget`, read through `L.has()`.
The four `fill_curve` functions take a `stable` argument. With it, every month returns 1.0, the
electricity fraction returns 1.0, and parking fill returns 1.0. Every caller passes
`project['stable_operation']`. A module-level switch was rejected: the same process could run two
projects.
- `_anchor_note_vi()` gains the stable wording: *"Dự án đang vận hành ổn định: tính lấp đầy 100% cả
  12 tháng theo lựa chọn tại Project Info, không dùng đường cong lấp đầy của dự án mới."*
- `RM.0A` is written as zeros, with *"Dự án đang vận hành, không còn căn chờ bàn giao nên chủ đầu tư
  không đóng phí thay."*
- The two fill-up sheets show 100% and carry the same reason.
- **Existing-project mode wins for `EEE.C`/`EEW.C`** (added 2026-10-11, session P14, as the
  `carry-forward-common-utilities` design's Risks section requires). In Existing mode those two lines
  already come from actual spend, flat, with no curve and no electricity floor; the switch does not
  change them or their remarks. It still applies to every other ramped line.

*Alternative:* make the curve's anchors an input (fill % at the end of years 1–4). It is more
general, but it asks the PM for a curve nobody has. It can follow later (PM-4).

### D4 — Recorded parking revenue, not a per-bay rate (P2)

Two labels go in the parking section: `Actual Car Parking Revenue (VND/month)` and
`Actual Motorbike Parking Revenue (VND/month)`.
- **Entered figure, stable switch Yes.** The line is the figure × 12, written flat. `_UNIT_RATES`
  for that line is replaced by the monthly figure, so the `RPa` narrative quotes it as a recorded
  monthly average.
- **Entered figure, stable switch not Yes.** The run stops (PM-3).
- **`BM11`.** It takes the entered monthly total, and `BN11` stays 0, so the split stays 100/0 and
  the 351 allocation rows keep their proportions. If both entered figures are 0, `BM11` falls back
  to bays × default rate (only the ratio matters), so the divide-by-zero guard is not tripped.

*Alternative:* a real per-bay rate field. Rejected on evidence. On the reference project, bays ×
the real per-bay car rate overshoots the real car parking revenue by 49%, because not every bay is
rented. The recorded average already carries the bay occupancy.

### D5 — Collect-on-behalf pairs, written only where the PM entered an amount (P4)

A block `COLLECT ON BEHALF (THU HỘ CHI HỘ)` gets one row per product and two amounts per row: water
and electricity, in VND/month. Each entered amount becomes the revenue row plus its paired expense
row, both flat × 12.
- **Revenue row mapping:** Apartment → `.A`, Officetel → `.T`, Office → `.O`, Shopping Mall → `.M`,
  Retail → `.R`, Shophouse → `.S`. Villas → `.L` (Landed house) is unconfirmed (PM-5). Shop Apartment
  and Nursery have no row, and an amount entered for them stops the run.
- **The expense pairing is PM-2.** The reference budget paired water with the per-zone common-area
  row (`EEW.AA`) and shophouse electricity with `EEE.S`. Those rows are labelled common-area
  consumption, not residents' own use (`EEW.A` / `EEE.A`). The specs only require "the expense line
  the approved pairing names", so either answer leaves them unchanged.
- **Catalogue.** The pairing and the guideline departure go into `Costing_Method_Catalogue.csv`,
  under a new method name for the `RO3.*` / `RO4.*` entries and their paired expense rows. `RO23`
  (a separate water-bill row) stays "not-estimated". `verification/method_coverage.py` learns the
  new method and treats an approved departure as expected. With no amount entered, an entry keeps
  the guideline's "not estimated" behaviour and remark. The standard sample therefore sees the same
  method-fidelity figure (99.9%) and the same remark assertions after the catalogue edit.
- **Template.** The pipeline does not set `2. Budget-Management Fund!F7` ("Mô hình tài chính"),
  so the template's VAT/CIT rows stay 0. The synthetic project checks they still do once
  collect-on-behalf revenue is present.

### D6 — Optional fields are read through `L.has()`, and the run lists them

Every new label is read only when present, as `Operating Years to Budget` already is. Each run
prints a block `Operating-project inputs:` listing every optional field as filled, blank or not on
the form. Labels that existed before this change keep their fail-loudly behaviour.

### D7 — The form builder gains the fields; the live form is never rewritten

`build_project_input_form.py` adds the new labels and columns to freshly built forms. It still
refuses to overwrite `Project_Budget_Input.xlsx` (input-form-protection). Its tests rebind
`OUT_DIR` / `FINAL_OUT` / `OUT` to a temp folder. An existing project's form gets the fields only
when the PM adds the labels by hand. `RUNNING.md` will say how.

### D8 — Regression on the reference project runs on a clone outside SharePoint

Use the same method as the 2026-10-07 comparison folder:
1. Copy `source_code`, `data` and the template to a new dated folder under `Savills-local\budget-test\`.
2. In the clone, delete the reference project's rows from `Dim_Property_Residential.csv` and
   `Fact_ProjectLocation.csv`. Otherwise the pipeline picks the project as its own comparable.
3. Fill the scale fields with the project's known values. A blank scale field crashes the run, a 0
   zeroes the related staffing, and only the 9 ratio-based staffing rows estimate themselves.
4. Run once per proposal, then once with all approved proposals together.
5. Compare by line code with the real budget's scanned lines (`budget_scan.sqlite`, `fact_line`).

Record the live `Project_Budget_Input.xlsx` hash before and after: it must not change. The env-var
patches of the 2026-10-07 clone are not reused. The regression runs the real code.

### D9 — Interaction with `add-multiyear-preopening-budget-phases`

That change (0/30, not started) MODIFIES the occupancy-ramp curve and fill-up-sheet requirements,
while this change only ADDS one. The two deltas do not collide at archive. Whichever change is
applied second adds the combined rules to its own specs:
- stable switch Yes with several operating years → 100% in every year;
- stable switch Yes with a pre-opening phase → contradictory input, and the run stops with a message.

### D10 — Order and approval gates

1. **P5 first.** It moves no figure and needs only the user's go-ahead to start code.
2. **P3 next.** P2 and P4 depend on the switch.
3. **P1, P2 and P4** follow in any order.

Each of P1–P4 starts only after the Head of PM approves it. P4 also needs the AI Guideline owner.
- **A rejected proposal** is removed from this change with `/opsx:update` (its delta, its tasks and
  its line in the proposal) before apply.
- **If P3 is rejected but P2 or P4 approved,** the "requires stable operation" rule in their specs
  changes with that update.

The change is archived only after every remaining proposal is implemented, measured on the reference
clone and signed off.

## Expected movement

**Standard synthetic project, all proposals:** no movement. The new fields stay blank, so the 24
analysis figures and the 8 ramped deliverable figures keep their recorded baselines. The new
operating-project fixture gets its own baseline.

**Reference project, tool output against the real budget.** "Today" means the 2026-10-07 run at 100%
occupancy unless stated otherwise:

| # | Lines that move | Today | After | Effect on the tool's totals |
|---|---|---|---|---|
| P5 | none | — | — | 0 cells change (A/B) |
| P1 | `RM.AP`; fallback-priced products such as `RM.OT` | `RM.AP` is 60% of real | equals real within rounding (< 0.01 million VND/year) | revenue from 51% to about 76% of real |
| P2 | `RP1`, `RP2` | `RP1` 48%, `RP2` 78% of real | equal to real (recorded average × 12) | revenue +about 5 points of real (to about 81% with P1) |
| P3 | `RM.0A`, collected `RM.*`, `RP*`, `EEE.C`, `EEW.C` | new-building curve: revenue 45%, expense 37% of real | revenue 51%, expense 41% of real; `RM.0A` 0 and collected fee up by the same amount | revenue +13%, expense +12% of the tool's own new-building figures |
| P4 | `RO3.A`/`RO4.S`/`RO3.S` and their paired expense rows (3 pairs on this project) | 0 | equal pairs, about 6% of real revenue and of real expense | revenue and expense each +about 6 points of real; surplus 0 change |

With every proposal and the existing Savills-fee field filled, the tool's revenue is about 87% of the
real budget's and its expense about 50%. Most of the remaining expense gap is in the non-goals.
Each row is re-measured on the regression clone (D8) before sign-off. The figures above come from
the 2026-10-07 comparison, not from the implemented code.

**Measured on the regression clone, 2026-10-11 (session P16, code `081b9bc`; ratios only, in
`clone-ratios-2026-10-11.txt` beside this file):**

| # | Measured | Against "After" above |
|---|---|---|
| P1 | `RM.AP` / real = 1.0000003 (+8,280 VND/year); revenue 51.1% → 75.9% of real | as expected |
| P2 | With the 2025 recorded averages from the real budget's remarks: `RP1` 96.7%, `RP2` 85.0% of real. With the real budget's own monthly figures: equal to real, but that is the line being compared, so it only proves the pass-through. `RP8`, `ESS38`, `RM.PA` unchanged | not equal to real: the real budget projects above its 2025 averages. The tool applies the entered figure × 12 exactly |
| P3 | revenue 45.1% → 51.1%, expense 36.6% → 41.0% of real; tool +13.2% / +12.2%; `RM.0A` → 0, collected `RM.*` up by the same amount (0 VND residual) | as expected |
| P4 | three pairs each = real; surplus change 0.0000 VND on both funds; pairs 6.2% of real revenue, 6.3% of real expense | as expected |
| All | revenue 85.3% of real with the 2025 parking averages (87.5% with the real budget's own parking figures); expense 47.4%; the tool fills 24 of the real budget's 127 lines (was 21) | expense 47.4% vs "about 50%": the Savills-fee field (EMH1) was left blank; filled, it adds about 2.8 points |

A default run of the clone (no new field) is unchanged cell for cell. Notes from the measurement:
- P1 and P2 also lower `RI1` (by about 65 million VND with every proposal on), because higher fund revenue
  shrinks the `2.2` revenue share. That is how the template works, so the surplus effect of P1/P2 is not
  exactly the revenue they add.
- With every proposal on, the surplus is still 18.5 times the real one: revenue is close to real but expense is
  not. The gap sits in the non-goals (contracts, staffing at scale fields 0, EMH1 blank, `RI1`).

## Decisions awaiting the Head of PM

| # | Question | Options | Specs written for |
|---|---|---|---|
| PM-1 | VAT basis of entered rates and recorded figures (ties to docs/22 D8) | (a) apply as entered and disclose a mismatch; (b) convert to the deliverable's basis at a VAT rate the PM states | (a) |
| PM-2 | Expense row paired with each collect-on-behalf revenue row | (a) residents' own-use rows `EEW.A` / `EEE.A`; (b) per-zone rows `EEW.AA…` / `EEE.AA…` as in the reference budget | neutral (catalogue holds the pairing) |
| PM-3 | Do recorded parking and collect-on-behalf amounts require the stable-operation switch? | (a) yes, otherwise the run stops; (b) allowed for any project, written flat | (a) |
| PM-4 | Stable operation is 100% occupancy, or an entered stable occupancy (e.g. 95%)? | (a) 100%; (b) entered % | (a) |
| PM-5 | Villas → Landed-house collect-on-behalf rows (`.L`)? | yes / no | stop for unmapped products |
| PM-6 | Depart from the AI Guideline's "not estimated" rule for collect-on-behalf lines (P4)? Who signs for the guideline? | approve / reject | approve, gated |

If PM-1 (b), PM-3 (b) or PM-4 (b) is chosen, the specs are updated with `/opsx:update` before apply.

### Answers recorded 2026-10-11 (session P13)

The user decided in place of the Head of PM, and for P4 in place of whoever signs for the AI Guideline, as
they did for `new-prospect-paid-holidays`. The user asked that the choices stay easy to change later.

| # | Answer | Note |
|---|---|---|
| P1–P4 | Approved, all four | P1–P3 are optional fields or a switch: left blank, a run equals today's |
| PM-1 | (a) apply as entered and disclose a mismatch | No `/opsx:update` needed |
| PM-2 | (a) `EEW.A` / `EEE.A` | Chosen by the session, not the user. The template labels these rows "(chi hộ)". It is one catalogue entry to change |
| PM-3 | (a) the switch is required, otherwise the run stops | |
| PM-4 | (a) 100% | |
| PM-5 | Not mapped | Chosen by the session. A Villas collect-on-behalf amount stops the run until the mapping is confirmed |
| PM-6 | Approved by the user in place of the guideline owner | Departs from the guideline's "not estimated" rule for collect-on-behalf lines |

### Answers recorded 2026-10-11 (session P14)

The user approved, in one round before any remark was written:

| # | Question | Answer |
|---|---|---|
| W1 | P3 wording (tasks 3.3): ramped-line note, `RM.0A`, `RP1`/`RP2` note, `EEE.C`/`EEW.C` stable sentences, `1. Summary` points 3/4 and parking line, the fill-up sheets' reason | Approved as drafted (texts in D3 and in the code, `operating_inputs.py`) |
| W2 | P1, P2 and P4 wording (tasks 4.4, 5.2, 6.4): entered-rate remark, VAT-mismatch sentence, fallback note, `1. Summary` rate text, `Comparison` label; recorded-parking remark, zero remark, `1. Summary` parking line; collect-on-behalf revenue and expense remarks | Approved as drafted |
| D11 | The template allocates a share of `EEW.A`/`EEE.A` to `2.2 Common area Fund` (`F = XLOOKUP(…AL…) × F8`), `RI1` reads that fund's expense total back as revenue, and `F8`'s denominator is the whole `2. Fund` revenue, `RO3`/`RO4` included. A collect-on-behalf pair would therefore move the `2. Fund` surplus through `RI1` | **Keep collect-on-behalf out of `2.2`.** Only when an amount is entered: the `2.2` rows of the paired expense lines get no allocation (frequency left blank, so the template's own `E` = 0) and a remark saying the line is paid on residents' behalf and not shared; `2.2!F8`'s denominator leaves out the `RO3`/`RO4` revenue rows. Both funds' surpluses then equal the run without the amounts |
| A1 | Analysis workbook with the switch Yes: the "Fill-up Scenarios" table (50/70/90/100%) and the "Year 1 Strategy" sheet | Keep both as sensitivity tables, each with one English line saying the project is at stable operation, the budget uses 100%, and the table is for reference |

### Answers recorded 2026-10-11 (session P15)

| # | Question | Answer |
|---|---|---|
| W1a | With the switch Yes, `check_remark_content` failed on `1. Summary` `EEW`: the W1 water sentence ("…với tỷ lệ lấp đầy 100% …") lacks the required part "lấp đầy cư dân" | **Amend the wording, keep the check.** The sentence now reads "Chi phí hạng mục này dự ước tại năm {năm} với tỷ lệ lấp đầy cư dân 100% (dự án đang vận hành ổn định)." (`operating_inputs.water_stable_vi`) |

### Answers recorded 2026-10-11 (session P16)

| # | Question | Answer |
|---|---|---|
| Sign-off | The five measured movements on the clone (3.4, 4.5, 5.4, 6.5, 8.1) | **Approved** by the user, standing in for the Head of PM and the guideline approver |
| PM-2 | Pair collect-on-behalf with one expense line per utility (`EEW.A`/`EEE.A`), or per product as the reference budget does | **Keep one line per utility** (now the user's choice, was the session's) |
| W3 | On an entered-rate line the approved PM-1 note ("…chưa gồm VAT…; chưa quy đổi.") was followed by the generic "Chi phí hạng mục này đã bao gồm VAT…", which contradicts it and calls revenue a cost | **Fix in this change.** The line ends with "Doanh thu hạng mục này dự ước tại năm {năm}." (`operating_inputs.entered_rate_year_vi`); the generic sentence is not appended; `check_remark_content` enforces both; delta spec `deliverable-remarks` |


## Risks / Trade-offs

- **[A typo in an entered rate moves revenue a lot]** → The `Comparison` sheet still shows the
  comparable rates, and the benchmark clause states the gap. The printed summary shows entered and
  derived rates side by side, with the % difference.
- **[A misspelt optional label is read as blank]** → The `Operating-project inputs:` printout lists
  every optional field as filled, blank or not on the form (D6).
- **[The real project is its own comparable]** → For an operating project the master list usually
  holds its own row. If the input name differs, name-based exclusion misses it. With P1 the applied
  rate is unaffected, but the other products and the `Comparison` sheet are not. Left as a
  follow-up; the regression clone removes the row (D8).
- **[Collect-on-behalf inflates the totals]** → Any ratio computed on total revenue or expense
  includes the pairs. The surplus is unchanged by construction, and the remarks name both sides.
- **[New remarks trip the existing remark scans]** → Wording is approved first, then checked by
  `check_remark_content` and the VAT-sentence rule on the operating-project fixture.
- **[Overlap with the multi-year change]** → See D9. Neither change modifies the other's requirement.
