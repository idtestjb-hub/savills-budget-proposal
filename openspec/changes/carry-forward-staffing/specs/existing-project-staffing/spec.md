## Purpose

Defines how the tool builds the staff cost of a project Savills already manages: it starts from the staff
roster of the previous approved budget, recalculates it under Vietnamese state law for the new budget year,
and explains every change, so that the staff lines of the proposal look like the lines a Property Manager
would write by hand.

Data files read: the input workbook (project mode, Prior-Year Roster), the labour-law parameter table
(`Ref_LaborLawParams.csv`, new), the holiday calendar. Data files written: none besides the output workbooks.
No recorded baseline figure moves in New-prospect mode.

## ADDED Requirements

### Requirement: A project is either a new prospect or an existing project

`Project Info` SHALL carry a project mode with exactly two values, "New prospect" and "Existing project".
A blank mode SHALL be treated as "New prospect", so every workbook filled in before this change keeps its
present result.

#### Scenario: A workbook filled in before this change is run

- **WHEN** an input workbook with no project mode is run
- **THEN** the staff lines SHALL come out exactly as before this change

#### Scenario: An unknown mode value is rejected

- **WHEN** the project mode holds any value other than the two allowed ones
- **THEN** the run SHALL stop and name the field and the allowed values

### Requirement: The prior-year approved roster is the baseline in Existing-project mode

In Existing-project mode the input workbook SHALL carry a Prior-Year Roster block with, per row: position,
shift, headcount, monthly gross salary per head (VND, before any employer contribution), and the budget
year of the approved budget it comes from. The tool SHALL use that roster as the starting headcount and
salary of every position it lists. The roster SHALL come from the approved budget, not from a draft.

#### Scenario: A listed position starts from last year's figures

- **WHEN** the project is an existing project and the roster lists a position with 3 heads at 12,000,000 VND
  monthly gross
- **THEN** the position SHALL start at 3 heads and 12,000,000 VND monthly gross per head
- **AND** the budget SHALL show that these figures come from the approved budget of the stated year

#### Scenario: Existing-project mode with neither a roster nor an approved amount stops

- **WHEN** the mode is "Existing project", the Prior-Year Roster has no rows and no approved prior-year EMH2 is given
- **THEN** the run SHALL stop and name both fields, rather than fall back silently to estimates

#### Scenario: A roster position beyond the template's rows is kept

- **WHEN** the roster gives a code more heads than the `A1` sheet has rows for that code
- **THEN** the extra heads SHALL be priced on the additional rows below the table, with the same formulas, and SHALL
  be included in EMH2

### Requirement: Without a roster, the approved line amounts are the baseline

When the Prior-Year Roster is empty but the PM gives the approved prior-year amounts of EMH2, EMH3 and EMH4 (VND per
year), those amounts SHALL be the baseline and SHALL be carried forward unchanged unless the PM overrides a line with a
reason code. Because no per-head salary is known, the tool SHALL NOT compute a law effect on EMH2 in this case, and the
Staff bridge SHALL say so.

#### Scenario: A project with only an approved EMH2

- **WHEN** the roster is empty and the approved prior-year EMH2 is 1,200,000,000 VND
- **THEN** the budget-year EMH2 SHALL be 1,200,000,000 VND
- **AND** the Staff bridge SHALL state that the law effect could not be computed without a roster

#### Scenario: A PM uplift on a lump-sum line

- **WHEN** the PM overrides EMH2 with 1,260,000,000 VND and the reason code "Thay đổi quy định pháp luật"
- **THEN** EMH2 SHALL be 1,260,000,000 VND and its remark SHALL state the old and new amounts and that reason

### Requirement: Each staffing line equals its detail sheet

In Existing-project mode EMH2, EMH3 and EMH4 on '2. Budget-Management Fund' SHALL each be a formula into its detail
sheet ('A1. Staff cost', 'A1.1 Allowance', 'A5. Trợ cấp PCCC'), never a typed amount. A carried-forward approved amount
SHALL appear on the detail sheet as its own row ("… đã duyệt NS <năm> mang sang"), and a PM override SHALL appear as its
own row ("Điều chỉnh của PM") equal to the override minus the computed figure, with its reason. When EMH4 is carried
forward, the template's default fire-team head counts on A5 SHALL be set to zero. An A1 row with no salary SHALL cost
zero. No figure changes, except that a roster without a PM no longer carries the template's PM-row insurance for an
empty row.

#### Scenario: A lump-sum project with a PM uplift

- **WHEN** the roster is empty, the approved EMH2 is 1,200,000,000 VND and the PM overrides it with 1,260,000,000 VND
- **THEN** A1 SHALL show a carried row of 100,000,000 VND/month and a PM adjustment row of 5,000,000 VND/month
- **AND** EMH2 SHALL be a formula into A1 that evaluates to 1,260,000,000 VND/year

#### Scenario: A roster without a property manager

- **WHEN** the roster has no PM position
- **THEN** A1's PM row SHALL cost zero, so A1 equals the Python replica

### Requirement: Source priority for a position's headcount

In Existing-project mode a position's headcount and salary SHALL come from the Prior-Year Roster when its `A1` code
has a roster row; the PM changes them in the "New Headcount" and "New Monthly Gross" columns of that roster row, with a
reason code. `Staffing Demand` rows for a code the roster covers SHALL be ignored for `A1`. An in-house position whose
code has no roster row is a new position: its headcount SHALL come from the PM's typed value on `Staffing Demand`, else
from the portfolio ratio, it SHALL be labelled "ước tính" (estimated) on its `A1` row, and it SHALL need a reason code
on `Staffing Demand`, because it is a change from a baseline of zero.

#### Scenario: A position not in last year's roster is estimated and labelled

- **WHEN** a position is on `Staffing Demand` but its code has no row in the Prior-Year Roster
- **THEN** its headcount SHALL come from the PM's typed value if there is one, otherwise from the ratio
- **AND** the row SHALL be labelled as estimated, not as carried forward

#### Scenario: A carried-forward salary goes in unchanged

- **WHEN** a roster row gives 12,000,000 VND monthly gross per head
- **THEN** each of its `A1` rows SHALL carry 12,000,000 VND in the gross-salary column, without any daily-rate conversion

### Requirement: Pay changes follow Vietnamese state law only

The tool SHALL recalculate the baseline for the budget year using only values from a labour-law parameter
table: regional minimum wage per region, the base and ceiling on which social, health, unemployment insurance
and trade-union contributions are charged, and the employer contribution rates. Each row of the table SHALL
carry its effective-from date, effective-to date when one is known, the legal document that sets it, and the
date it was last checked. For each month of the budget year the tool SHALL use the values in force that month, for the project's
minimum-wage region (a `Project Info` field; blank means Region I, the region the template assumes).
The tool SHALL NOT apply any percentage increase that is not set by the table. A salary below the regional
minimum wage in force SHALL be raised to that minimum, with an automatic reason. A salary above it SHALL stay
unchanged by law.

The table SHALL include at least the regional minimum wage (regions I to IV) effective 2024-07-01 and
2026-01-01 (Decree 293/2025/NĐ-CP), the insurance base (2,340,000 VND until 2026-06-30, 2,530,000 VND from
2026-07-01), the ceiling multiple (20 times), and the employer rates (social and health insurance 20.5%,
unemployment insurance 1%, trade union 2%).

#### Scenario: A budget year after the latest published rule uses the rule in force

- **WHEN** the budget year starts after the latest effective date in the table
- **THEN** the tool SHALL use the latest values in force
- **AND** the Staff bridge SHALL state that no newer rule was available for that year

#### Scenario: A new rule is added to the table

- **WHEN** a row with a later effective date is added to the table and the tool is run again
- **THEN** the months of the budget year on or after that date SHALL use the new values, with no code change

#### Scenario: A salary below the new regional minimum wage is raised

- **WHEN** a position's baseline salary is 4,900,000 VND and the regional minimum wage in force is 5,310,000 VND
- **THEN** its salary SHALL be 5,310,000 VND and the line SHALL carry the reason "điều chỉnh theo lương tối thiểu vùng"

### Requirement: Holiday and night-shift allowance is recalculated from the calendar

The allowance for night shifts and public holidays (EMH3) SHALL be its own line in Existing-project mode, priced on
the `A1.1` sheet and excluded from EMH2 so it is not counted twice. Its staff counts (per normal night, per holiday
night, on day shift per holiday) and the gross salary they are paid on SHALL be the prior year's, entered by the PM
in a "Holiday and Night Duty" block; the tool SHALL NOT decide which positions work on holidays. The days SHALL come
from the paid-holiday calendar of each year, under the law in force on 1 January of that year. When the number of
paid public holidays differs from the baseline year, the tool SHALL generate the reason itself, naming the added or
removed holiday. When the block is empty, EMH3 SHALL be the approved prior-year amount carried forward.

#### Scenario: One more public holiday than last year

- **WHEN** the budget year has one paid public holiday more than the baseline year
- **THEN** EMH3 SHALL rise by the cost of that day for the staff counted in the block
- **AND** the line SHALL carry an automatic reason naming the holiday

#### Scenario: The allowance is not counted twice

- **WHEN** EMH3 is priced from `A1.1`
- **THEN** EMH2 SHALL equal the `A1` payroll without the `A1.1` allowance

### Requirement: The fire-fighting team allowance follows the regional minimum wage

In Existing-project mode, when the approved prior-year EMH4 is above zero, the budget-year EMH4 SHALL be that amount
times the ratio of the average regional minimum wage of the budget year to that of the prior year, with the reason
"điều chỉnh theo lương tối thiểu vùng" when the ratio is not 1. An approved prior-year EMH4 of zero SHALL stay zero.
When the field is blank, EMH4 SHALL be priced as in New-prospect mode.

#### Scenario: The line was not used last year

- **WHEN** the approved prior-year EMH4 is 0
- **THEN** the budget-year EMH4 SHALL be 0 and the line SHALL keep its original remark

### Requirement: Every changed staffing line carries a reason

A staffing line is a row of `A1. Staff cost`, EMH2, EMH3 or EMH4. When any of them differs from the baseline in
headcount, salary or amount, the line SHALL carry a reason. The reason is generated by the tool when the
change comes from law or from the calendar. Otherwise the PM SHALL pick one code from the approved list below
and MAY add a note; the code "Khác" SHALL require a note. A change without a reason SHALL stop verification.

The approved list of reason codes (Vietnamese) is: "Mở dịch vụ hoặc tiện ích mới"; "Thay đổi mô hình ca hoặc
giờ làm việc"; "Thay đổi quy định pháp luật"; "Bàn giao hoặc bổ sung khu vực quản lý"; "Chuyển đổi giữa nhân
sự trực tiếp và thuê ngoài"; "Theo yêu cầu của cư dân hoặc chủ sở hữu"; "Vị trí trống, không tuyển bổ sung";
"Khác (bắt buộc ghi chú)". The Head of PM approves the final list before this change is archived.

#### Scenario: A PM raises a headcount without giving a reason

- **WHEN** the PM changes a position's headcount versus the baseline and gives no reason code
- **THEN** verification SHALL fail and name the position

#### Scenario: A PM overrides a salary with the code "Khác" and no note

- **WHEN** the reason code is "Khác" and the note is empty
- **THEN** verification SHALL fail and name the line

### Requirement: The Staff bridge ties prior year to this year

The internal analysis workbook SHALL contain a Staff bridge sheet that walks from the baseline staff cost to
the budget-year staff cost in steps: wage and insurance effect, headcount and salary changes, allowance effect
(EMH3 and EMH4), PM line overrides, then the budget-year total. Each step SHALL be in VND per year. The bridge SHALL
equal EMH2 plus EMH3 plus EMH4 of the client deliverable exactly, SHALL list every changed line with its reason
record (code, text, source), and SHALL NOT appear on the client deliverable. After an Existing-project run the
run command SHALL report any changed line without a reason as a failure naming the line.

#### Scenario: The bridge adds up

- **WHEN** the bridge is built
- **THEN** baseline plus the effects SHALL equal the budget-year total, and the total SHALL equal EMH2 plus EMH3 plus EMH4

### Requirement: The baseline reproduces last year's approved staff cost

Before the tool applies any change, it SHALL recompute the previous year with the parameter-table values in
force that year and compare the result with the previous approved EMH2 when the PM supplies that figure. A
difference above the stated tolerance SHALL be flagged on the Staff bridge, not silently absorbed.

#### Scenario: The recomputed prior year does not match the approved figure

- **WHEN** the recomputed prior-year staff cost differs from the approved EMH2 by more than the tolerance
- **THEN** the Staff bridge SHALL flag the difference with both numbers

### Requirement: Actual headcount may be shown beside the baseline

The input workbook SHALL offer an optional block for the actual headcount per position taken from C&B payroll
and PM timesheet data. When it is filled, the Staff bridge SHALL show it beside the baseline and SHALL state
which positions differ. The block SHALL NOT change any figure and SHALL NOT be required.

#### Scenario: The optional block is empty

- **WHEN** the optional block is empty
- **THEN** the run SHALL succeed and the Staff bridge SHALL not mention actual headcount
