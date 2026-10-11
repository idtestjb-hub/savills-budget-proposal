## Context

See `proposal.md` for the reason. Facts about the code today that shape the approach (all read 2026-10-10):

- The staff cost is not one number. `EMH2` is a formula reference into the sheet `A1. Staff cost 08.2026 (VN)`,
  which prices each rostered position as gross salary, 13th month, employer social/health insurance 20.5% and
  unemployment insurance 1% (both capped at 20 times a base), trade union 2% (same cap), then Savills' 10% admin
  markup. Positions the roster does not place are added as a top-up inside EMH2. `EMH3` comes from the sheet
  `A1.1 Allowance`, `EMH4` from `A5. Trợ cấp PCCC`.
- The legal numbers are written into the code and into the template's hidden reference rows: insurance base
  2,530,000 VND (`A1!I4`), unemployment base 5,310,000 VND (`A1!I5`), cap multiple 20, rates, markup. They are labelled
  "2026" and drift from the law when the law changes (`generate_project_output.py`, `STATUTORY_*_2026`).
- Headcount for a role with a portfolio ratio is computed from the ratio unless the PM typed a real number; a zero typed
  there is still replaced by the ratio, and a genuine zero is expressed by deleting the row (spec
  `portfolio-derived-staffing-defaults`). This is documented behaviour and stays.
- Fields are found by label, not by cell address (spec `input-workbook-reading`). The input-form builder refuses to
  overwrite a filled workbook.
- Back-test on a managed low-rise project ("project X"): the tool ratio-estimated 20 positions and overshot EMH2 by about
  1.8 times the real line (the tool came to about 2.8 times it); the real 2027 file carried EMH2 forward from the approved 2026 budget (about +5.0%) and stated the reason.
- Sources of law found 2026-10-10: Decree 293/2025/NĐ-CP (regional minimum wage from 2026-01-01: I 5,310,000; II 4,730,000;
  III 4,140,000; IV 3,700,000 VND/month; previous 4,960,000; 4,410,000; 3,860,000; 3,450,000), the employer contribution rates
  (social and health insurance 20.5%, unemployment 1%), the insurance ceiling of 20 times the base (2,340,000 VND to 2026-06-30,
  2,530,000 VND from 2026-07-01). No regulation for 2027 was found.

## Goals / Non-Goals

**Goals:**
- Existing-project mode that carries last year's approved roster forward and recomputes it under law, with a reason on
  every change, in the remark and on an internal bridge.
- No change at all in New-prospect mode.
- Legal numbers in one dated, sourced table instead of the code.

**Non-Goals:**
- Management-fee rate, electricity, outsourced contracts, other rates (later changes).
- Any merit or inflation percentage chosen by the tool. A PM who wants one overrides the amount and gives a reason code.
- Building the link to C&B payroll or PM timesheet data (only the optional field).
- Any Power Automate or Power Apps part.

## Decisions

### D1. A mode field and a new sheet, not new columns on existing sheets

`Project Info` gets a labelled field "Project Mode" with a dropdown. The roster is a new sheet "Prior-Year Roster" (position,
shift code, headcount, monthly gross salary per head in VND, source budget year, note), plus the optional sheet block "Actual
Headcount (optional)". Alternative considered: extra columns on `Staffing Demand`. Rejected because `Staffing Demand` holds
formulas and the ratio override logic, and a baseline is a different kind of input (a record of last year, not an assumption).
Reason code and note for a PM change go in two new labelled columns on `Staffing Demand`, with a dropdown for the code.

### D2. Baseline stored as salary per head, not as total cost

The PM enters gross salary per head because that is what `A1` consumes; the employer cost is then computed by the same chain
as today. Alternative: store each position's total employer cost. Rejected because insurance caps and the minimum-wage floor act
on the salary, and a total cannot be split back reliably. Cost: the PM needs last year's `A1` salary column, which the approved
budget file already has.

### D3. One labour-law parameter table, read by month

`data/generation_B_verified/Ref_LaborLawParams.csv`, columns: parameter, region, value, unit, effective_from, effective_to,
legal_basis, source_url, checked_on. The loader returns, for each month of the budget year, the values in force. The constants
in `generate_project_output.py` and the hidden reference cells of `A1` (insurance bases, cap multiple, rates, markup) are written
from the table for the budget year; the formula chain of `A1` is not edited. Alternative: edit the template formulas to read
the table. Rejected because the standard template belongs to the template owners. The markup (10%) and the 13th month are
Savills policy, not law: they stay as template values and are listed in the table as "template" rows with no legal basis, so
the Staff bridge can show them.

### D4. The bridge is computed in fixed order

Order: (1) baseline recomputed with the parameters in force in the baseline year (the back-cast); (2) wage and insurance effect:
same headcount and salaries, new parameters and the minimum-wage floor; (3) headcount effect: changes in headcount, priced at
the new parameters; (4) allowance effect: EMH3 and EMH4 change. The order is fixed because effects interact (a new head is
priced at the new floor); the sheet says so. The bridge is internal.

### D5. Reasons are data, remarks are rendered from data

Each changed line has a reason record: code, text, source ("tool" for law and calendar, "PM" otherwise). Remarks and the
verification check both read that record, so the remark and the check cannot disagree. Generated reasons: "điều chỉnh theo lương
tối thiểu vùng và mức đóng bảo hiểm" and "thay đổi số ngày lễ: <tên ngày>". PM codes are the approved list in the spec.
The guideline's original remark is produced as today and the sentence "Điều chỉnh so với NS <năm>: …" is appended.

### D6. Staffing lines in scope

All rows of `A1. Staff cost` in the roster, EMH2 (derived from `A1`), EMH3 (`A1.1`), EMH4 (`A5`). EMH1 (fixed fee) stays out: it is a
contract term and is entered as today.

### D7. Acceptance measured, not argued

Two checks. (a) Back-test on project X in a clone outside SharePoint, as in the 2026-10-10 back-test: feed the approved 2026
EMH2, EMH3 and EMH4 amounts (EMH4 was 0; project X has no roster, see D8) and the 2026 holiday-duty counts
(one code, 2 staff on day shift per holiday, with that position's gross from the 2026 holiday sheet; the salary stays in the
clone, not in the repository), and compare EMH2 and EMH3 for 2027 with the real 2027 file. The proposed
tolerance is plus or minus 5% on EMH2, to be confirmed by the Head of PM. Because the tool applies law only and the real file
applied a PM-chosen +5%, the tool may land below the real figure by design; the Staff bridge must explain the gap and a PM override
with a reason code must be able to close it. (b) New-prospect regression: the standard sample before and after must show zero
cell differences. Only one project in the scanned data has two consecutive approved budgets, so the second case is an invented
fixture with a multi-region wage floor and a headcount change; this is stated as a limitation.

## Decisions added during apply (2026-10-10)

Reading the code and the two real files of project X changed five premises above. The user chose each option below on
2026-10-10. They replace D1 (where PM changes go), D6 (EMH3/EMH4 mechanics) and D7(a) (what the acceptance feeds) where
they disagree.

Facts found:
- Project X's approved 2026 and 2027 budgets have no per-position staff table. EMH2 is one monthly figure, unchanged from
  2025 in 2026 ("Giữ nguyên so với NS 2025") and +5.0% in 2027 ( "Đề xuất tăng 5%, điều chỉnh do lương cơ sở/lương tối
  thiểu vùng…").
- EMH3 is its own line, computed on a "Lễ Tết <năm>" sheet: 2 technicians on day shift on public holidays × daily rate
  (gross ÷ 25) × 300% × paid holidays. 2026: 11 days. 2027: 12 days, note "Tăng số lượng 1 ngày lễ 24/11".
- In the 2027 template, the `A1.1` allowance does not reach EMH3. It flows into EMH2 through `A1!AC90 = A1.1!S13` and
  `AC91 = SUM(AC89:AC90)`. Today the `A1.1` staff counts are blank, so the allowance is zero, and EMH3 carries a "left at zero"
  reason.
- `A1` has a fixed number of rows per code (PM 1, BE 6, CS 18, TDS 8, TN 19, pool AA 10, gym AA 3, others 1–2). Today,
  heads above that number are dropped silently.
- `A1`'s monthly gross enters column G. The New-prospect path derives it as daily rate × 25. That conversion does not apply to
  a carried-forward salary.

### D8. Two baselines: a roster, or the approved line amounts

Existing-project mode accepts either a Prior-Year Roster, or the prior year's approved amounts for EMH2, EMH3 and EMH4
(VND/year), or both.
- **Roster present:** EMH2 is built from the roster on `A1`, as in D2. The approved EMH2, when given, is the back-cast check.
- **No roster but an approved EMH2:** EMH2 is that amount carried forward. Without per-head salaries the tool cannot compute
  a law effect, so it does not invent one. The bridge says so.
- **Neither:** the run stops and names both fields.

Any amount the PM changes needs a reason code, as everywhere else.

### D9. PM changes are made where the baseline is

- **Carried-forward positions:** the PM types new headcount or new monthly gross in columns next to the roster row on
  "Prior-Year Roster", with the reason code and note in the same row. Headcount and salary there are in heads and
  VND/month, the same units as `A1`. This replaces D1's idea of typing over `Staffing Demand`, which counts staff on duty
  per day, not heads.
- **Positions in no roster row:** these are in-house positions on `Staffing Demand` whose `A1` code has no roster row. They
  are new positions, priced as today (typed, else ratio), labelled "ước tính" on `A1`. They need a reason code in the two
  new `Staffing Demand` columns. `Staffing Demand` rows for a code that the roster covers are ignored for `A1`.
- **Line override:** a PM override of a whole line's budget-year amount (EMH2, EMH3, EMH4) goes in the "Staff Lines" block,
  with its reason code. This is how a lump-sum project records a PM uplift such as the +5% of project X.

### D10. EMH3 is its own line, priced on `A1.1` (Existing-project mode only)

The PM copies the night and holiday duty counts from last year's approved holiday sheet into a block "Holiday and Night
Duty": per code (CS, BE, TDS, TN, AA), staff per normal night, staff per holiday night, staff on day shift per holiday, and
the monthly gross used. The tool writes them to `A1.1` G/K/O and D. It writes the day counts of the budget-year calendar to
H6 (days in year minus paid holidays), L6 and P6. The holiday count is `vn_holidays.paid_holidays(year)` (decision
2026-10-10).

EMH3 = `A1.1!S13` monthly. EMH2 drops the allowance so nothing is counted twice:
`=('A1'!AC96 - 'A1'!AC90*'A1'!AC95 + unplaced*12)/12`. `A1`'s own formulas are not edited.

The gross used for the allowance is taken from the block, not looked up on `A1`. The minimum-wage floor applies to it. This
keeps EMH3 independent of `A1` row order: the template's XLOOKUP takes the first row of a code, and project X's file
carries its own gross.

Nothing derives a policy on who works on holidays (open question Q1 in `05-decisions.md`). The counts are last year's.

If the block is empty, EMH3 is the approved prior amount carried forward (D8). If that is blank too, today's zero reason
stays.

### D11. EMH4 follows the regional minimum wage

The A5 PCCC allowance is linear in the regional minimum wage (template A5: wage ÷ 26 × 30% × days × trainings × people).
- **Approved prior EMH4 > 0:** budget-year EMH4 = that amount × (average regional minimum wage of the budget year ÷ that of
  the prior year). If the ratio is not 1, the line carries the reason "điều chỉnh theo lương tối thiểu vùng".
- **Approved prior EMH4 = 0:** EMH4 stays 0. The line was not used last year (project X: "Không chi do CĐT chưa duyệt Tờ
  trình").
- **Blank:** EMH4 is priced from A5 as today.

The template's 7.8% "expected increase" in A5!C2 is not law and is not used in Existing-project mode.

### D12. A1 overflow goes to the unplaced rows

Roster heads beyond a code's row group go to the unplaced rows from row 98. That mechanism already exists for Reception, and
its formula chain and EMH2 sum already cover those rows. The row keeps the position name and its `A1` code. New prospect is
untouched.

### D13. The bridge covers all staffing lines and tells the PM at run time

- **Total:** the Staff bridge total = EMH2 + EMH3 + EMH4 of the deliverable. D4's allowance effect already includes EMH4.
- **Reason records:** the bridge lists one row per changed line or position (baseline, new, difference, reason code, text,
  source). `verification/checks.py` reads these records (D5).
- **Run-time report:** `run.py` runs the same reason check after an Existing-project run and reports a missing reason as a
  failure naming the line. PMs never run `verify.py`.
- **Python replica of `A1`:** the bridge computes `A1` in Python with the template's own row formulas: 13th month, team
  building, training 1.3%, capped SI/HI 20.5%, UI 1% and union 2%, the fixed per-head items in W/X/Z, ROUND as Excel does,
  and the 10% markup. Verification confirms the replica against the deliverable that Excel recalculates.

### D14. Legal parameters on `A1` in Existing-project mode only

For the budget year, the tool writes `A1!I4` (insurance base), `I5` (Region minimum wage, the unemployment base) and the
employer rates T8/U8/V8 from the table. It does this only in Existing-project mode. If a value changes within the budget
year, `A1` gets the annual average and the bridge says so.

New prospect keeps the template cells, `I5` formula included, so its cells stay identical. The `STATUTORY_*` constants in
`generate_project_output.py` are read from the table at the parameters in force for the budget year, Region I. That gives
the same values as today: 2,530,000 / 5,310,000 for 2027.

### D15. Each staffing line equals its detail sheet (2026-10-10, session P12)

Running the verification checks on project X's lump-sum output showed that the detail sheets did not support the lines:
A1 showed only the A1.1 allowance plus an empty PM row's insurance, under 2% of the typed EMH2, and A1.1 had no row for
the PM's +5% on EMH3. The workspace rule is that a summary figure equals its visible detail rows and an adjustment is
its own row. The user chose on 2026-10-10:

- **Lines are formulas.** In Existing-project mode EMH2, EMH3 and EMH4 are always formulas into A1, A1.1 and A5. This
  replaces D8's typed carried amount and D9's typed line override. The figures do not change, except for a roster with
  no PM (next point).
- **A1.** Below the table, after any overflow rows of D12: a row "EMH2 đã duyệt NS <năm> mang sang" when there is no
  roster, then a row "Điều chỉnh của PM" when EMH2 is overridden (override minus computed). Both carry the monthly amount
  in AC only, because the amount already includes insurance and the admin markup. EMH2 keeps D10's formula shape:
  `(AC96 - AC90*AC95 + SUM(AC98:AC<last>)*12)/12`.
- **An empty A1 row costs zero.** The template's PM-row accident-insurance formula (X) charges 154,342 VND/month even
  with no salary. In Existing-project mode a PM row without a person gets X = 0. The Python replica already treats an
  empty row as zero, so this also keeps A1 equal to the replica for a roster without a PM. For such a roster EMH2 drops
  by 154,342 × 12 = 1,852,104 VND/year. Neither invented sample has a roster without a PM, so this case is not
  exercised by `verify.py`.
- **A1.1.** Below row 13: "EMH3 đã duyệt NS <năm> mang sang" when the duty block is empty, and "Điều chỉnh của PM" when
  EMH3 is overridden; S = VND/year, T = S/12, U = the reason. A total row adds them to S13, and EMH3 points at it.
- **A5.** When EMH4 is carried forward, the template's default team (G5:G7) is set to 0. Below the table: "EMH4 đã duyệt
  NS <năm> mang sang", "Điều chỉnh theo lương tối thiểu vùng" when D11's ratio moves it, and "Điều chỉnh của PM" when
  overridden; a total row adds them to H8, and EMH4 = that total / 12. An EMH4 left to the template keeps today's
  formula; a PM override on it adds only the adjustment row.
- **Verification.** A new check confirms each line is a formula into its sheet and equals that sheet's total. Section 8
  runs on a second invented sample without a roster: approved EMH2 with a PM override, approved EMH3 with an empty duty
  block and an override, approved EMH4 of 0.

## Risks / Trade-offs

- [Law-only pay uplift is below what PMs do in practice] → the gap is shown on the bridge; a PM override with a reason code is allowed.
- [Writing parameters into the template's hidden cells changes the template per run] → only the generated copy is changed; verify that the template
  file itself is untouched; keep the template read-only.
- [The tool's holiday calendar may lack 24 November as a paid holiday for the budget year] → task 4.1 checks `vn_holidays.py` against the law and the
  project status note (12 holidays) before EMH3 is trusted.
- [Entry burden: the PM must supply last year's salary column] → the form shows the exact source cells; no import tool in this change.
- [Back-cast mismatch flags noise when the prior budget used different assumptions] → tolerance is a parameter, default 1%, and the flag is a warning.
- [Real payroll is confidential] → real figures stay in the back-test clone outside the repository; tests use invented data.
- [Reason codes become a rubber stamp] → "Khác" requires a note, and the Head of PM reviews the list after the first projects.

## Migration Plan

The new labels are optional. A workbook without them runs as "New prospect". To add the new sheets to a project's existing live
input workbook without the builder's refusal to overwrite, a helper appends them to a dated copy and leaves the original untouched.
Rollback: set the mode to "New prospect" or revert the commit; nothing else depends on it.

## Open Questions

- Tolerance values (back-cast 1%, acceptance 5%): confirm with the Head of PM after the first run.
- Whether the optional actual-headcount block should later be filled from C&B and PM timesheet data by a one-click script; decided in a separate change.
