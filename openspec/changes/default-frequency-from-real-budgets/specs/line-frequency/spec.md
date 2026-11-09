## MODIFIED Requirements

### Requirement: A new budget takes each code's default frequency

When a new budget is generated, each written line SHALL take the frequency, number of times and first month listed
for its code in `Budget_Agent/data/generation_B_verified/Ref_LineFrequency.csv` (columns: code, frequency, times,
first_month, source, note). Every cyclic line of the table starts in T1, as the form's own cyclic rows do (user's
choice 2026-11-07). A code not listed SHALL be Monthly, except a line the tool writes as Schedule (12 month
amounts, for example a ramped line or a one-time capex amount in month 1), which SHALL stay Schedule.

The table SHALL be built from the frequency column of the 55 real budgets mapped in `real_budget_ranges_map.csv`
(user's rules 2026-11-09):
- one vote per file and code, from the Management Fund budget sheets only, on lines with a non-zero amount; Schedule
  is not counted; a file whose MF sheets give two frequencies equally often votes for nothing;
- a code takes a non-Monthly frequency when at least 5 files carry it and that frequency has more than half of the
  votes; otherwise it is Monthly and is not listed;
- ESC12 (Yearly), ESM2 (Half a Year), ESM5 (Quarterly) and ESM25 (Quarterly) keep the frequency their costing counts,
  as an exception the row's note states;
- a code not on the 2027 form's Management Fund sheet SHALL NOT be listed.

Each row SHALL state its source as counts (for example "real budgets: Yearly 22 of 39 MF files") and SHALL list no
project name, file name or path. The raw read of the real budgets stays on the office machine and is not committed.

A defaulted line SHALL keep the annual amount the tool computed: the per-time price SHALL be that amount divided by
the number of times. A line left for the PM SHALL take the table's frequency and months of payment with no price
until the PM types an annual figure. A line whose amount varies by month (a ramped revenue or occupancy-driven line)
SHALL NOT be defaulted to a cyclic frequency. Data files: reads the mapped real budgets (office only),
`real_budget_ranges_map.csv` and the 2027 template; writes `Ref_LineFrequency.csv`. Recorded baselines: annual
figures SHALL NOT move beyond the per-time rounding; the per-time price (F), the month figures and the remark of the
newly defaulted priced lines move, and RO2a's row returns to Monthly; they are re-recorded once after the user's
sign-off.

#### Scenario: A defaulted quarterly line
- **WHEN** the table lists ESM25 as Quarterly, 4 times, first month T1, and the tool prices ESM25 at 14,000,000 VND a
  year
- **THEN** the new budget SHALL write ESM25 as Quarterly at 3,500,000 VND per time in T1, T4, T7 and T10
- **AND** ESM25's annual amount on `1. Summary` SHALL be 14,000,000 VND, as before this change

#### Scenario: A code the real budgets pay once a year
- **WHEN** 22 of the 40 real budgets that carry ESC5 on their MF sheets pay it Yearly and the tool prices ESC5 at
  36,000,000 VND a year
- **THEN** the table SHALL list ESC5 as Yearly with source "real budgets: Yearly 22 of 40 MF files …"
- **AND** the new budget SHALL write ESC5 once, 36,000,000 VND in T1, with the annual amount unchanged

#### Scenario: A template default the real budgets do not follow
- **WHEN** RO2a is Monthly in all 22 real budgets that carry it
- **THEN** RO2a SHALL NOT be listed and SHALL be written as Monthly

#### Scenario: A code not on the 2027 form
- **WHEN** ESA1 passes the threshold but is not on the 2027 form
- **THEN** ESA1 SHALL NOT be listed

#### Scenario: A code not in the table
- **WHEN** a code is not listed and the tool writes it as a monthly amount
- **THEN** it SHALL be written as Monthly, as before this change
