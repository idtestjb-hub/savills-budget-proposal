## Purpose

How often a budget line is spent or collected in the year, and in which months: the six frequencies of the 2027 form,
what each writes on the fund sheets, the default frequency of each code in a new budget, and how the remark states it.

## ADDED Requirements

### Requirement: A budget line takes one of the form's six frequencies

Every line the tool writes on `2. Budget-Management Fund` or `2.2 Common area Fund` SHALL carry one frequency in
column C, taken from the form's own list: Monthly, Quarterly, Half a Year, Yearly, Optional or Schedule. The fund row
SHALL be filled the way a PM fills the form by hand:

| Frequency   | C           | D (times)  | F                        | H:S                                     |
|-------------|-------------|------------|--------------------------|-----------------------------------------|
| Monthly     | Monthly     | blank      | amount per month (VND)   | blank                                   |
| Quarterly   | Quarterly   | blank      | amount per time (VND)    | the 4 months of payment                 |
| Half a Year | Half a Year | blank      | amount per time (VND)    | the 2 months of payment                 |
| Yearly      | Yearly      | blank      | amount per time (VND)    | the month of payment                    |
| Optional    | Optional    | 1 to 11    | amount per time (VND)    | the D months of payment                 |
| Schedule    | Schedule    | blank      | blank                    | the amount of each of the 12 months     |

A month of payment SHALL be written as the form's own month header of the budget period (row 8 of the sheet), so the
form's month spread (columns AQ:BB on `2. Budget-Management Fund`, AL:AW on `2.2 Common area Fund`) places the amount in that month. On every written line the form's check of the number of times
(column U) SHALL be 0 and its check of the total (column V) SHALL be TRUE after Excel recalculates.

#### Scenario: A quarterly line
- **WHEN** ESM25 is written as Quarterly at 3,500,000 VND per time with first month T3 of a January-to-December
  budget period
- **THEN** C SHALL read "Quarterly", F 3,500,000, H:S the month headers of March, June, September and December
- **AND** the form's total G SHALL be 14,000,000 VND, U SHALL be 0 and V TRUE

#### Scenario: An optional line
- **WHEN** a line is Optional, 3 times, in T2, T7 and T11, at 8,000,000 VND per time
- **THEN** D SHALL be 3, F 8,000,000, H:S the three month headers, and G 24,000,000 VND

### Requirement: Cyclic months repeat from a first month inside the budget period

For Quarterly, Half a Year and Yearly the months of payment SHALL be the first month and then every 3, 6 or 12 months
after it, counted on the 12 months of the budget period (T1 is the period's first month, so a July-start period has
T1 = July). The first month SHALL be T1 to T3 for Quarterly, T1 to T6 for Half a Year and T1 to T12 for Yearly. With
no first month given the first month SHALL be T1.

#### Scenario: A half-yearly line in a July-start period
- **WHEN** the budget period starts in July 2027 and a Half a Year line has first month T6
- **THEN** its months of payment SHALL be December 2027 and June 2028

#### Scenario: A first month out of range
- **WHEN** a Quarterly line is given first month T5
- **THEN** it SHALL be refused with "Tháng đầu của Hàng quý phải là T1, T2 hoặc T3"

### Requirement: A new budget takes each code's default frequency

When a new budget is generated, each written line SHALL take the frequency, number of times and first month listed
for its code in `Budget_Agent/data/generation_B_verified/Ref_LineFrequency.csv` (columns: code, frequency, times,
first_month, source, note). Every cyclic line of the table starts in T1, as the form's own cyclic rows do (user's
choice 2026-11-07). A code not listed SHALL be Monthly, except a line the tool writes as Schedule (12 month
amounts, for example a ramped line or a one-time capex amount in month 1), which SHALL stay Schedule. The table SHALL
be built from the template's own column C and from the counts the tool already prices with, each row stating its
source; it SHALL list no project name. A defaulted line SHALL keep the annual amount the tool computed: the per-time
price SHALL be that amount divided by the number of times. A code whose template frequency differs from the table
SHALL take the table's value, and the table row SHALL say so in its note. A line whose amount varies by month (a
ramped revenue or occupancy-driven line) SHALL NOT be defaulted to a cyclic frequency. Recorded baselines: annual
figures SHALL NOT move; the per-time price (F) and the month figures of the defaulted lines move and are re-recorded
once after the user's sign-off.

#### Scenario: A defaulted quarterly line
- **WHEN** the table lists ESM25 as Quarterly, 4 times, first month T1, and the tool prices ESM25 at 14,000,000 VND a
  year
- **THEN** the new budget SHALL write ESM25 as Quarterly at 3,500,000 VND per time in T1, T4, T7 and T10
- **AND** ESM25's annual amount on `1. Summary` SHALL be 14,000,000 VND, as before this change

#### Scenario: A code not in the table
- **WHEN** a code is not listed and the tool writes it as a monthly amount
- **THEN** it SHALL be written as Monthly, as before this change

### Requirement: The remark states a frequency other than Monthly

The Vietnamese remark of a line whose frequency is not Monthly SHALL state it in one sentence: "Hàng quý" (Quarterly),
"6 tháng/lần" (Half a Year), "Hàng năm" (Yearly), "<n> lần/năm" (Optional), with the number of times, the price per
time in VND (thousands separated as on the other remarks) and the months of payment as T-numbers of the period; for Schedule, "Chi theo lịch từng tháng" and the
months that carry an amount. A Monthly line's remark SHALL NOT gain this sentence. A Schedule line the tool writes
itself (a ramped or one-time amount) keeps its own remark; the Schedule sentence is written when the PM sets Schedule
on the web, and the stale-remark note applies to lines whose frequency is cyclic, Optional or set on sheet 4. The sentence SHALL follow the
remark rules already in force (Vietnamese units, no internal wording, no project name).

#### Scenario: A quarterly remark
- **WHEN** ESM25 is Quarterly, 4 times at 3,500,000 VND per time in T3, T6, T9, T12
- **THEN** its remark SHALL contain "Hàng quý, 4 lần/năm × 3,500,000 VND/lần, chi vào T3, T6, T9, T12"
