## Purpose

Keeps a record of every budget the tool generates: which project, how complete the budget is, and what it brings
Savills, so that a dashboard can show the history that the overwritten analysis workbook cannot.

Data files read: the client deliverable and the internal analysis written by the same run (through Excel, read-only
copies), and `data/master_list_verified/AI_Guideline_Required_Classification.csv`. Data written: one new file per run
in `Budget_Agent/reports/run_log/`. No recorded baseline figure moves.

## ADDED Requirements

### Requirement: Every complete run leaves one record
After `run.py` has written the deliverable, the roster and the analysis, and has confirmed that they describe the same
project, the tool SHALL write exactly one record for that run into `Budget_Agent/reports/run_log/`. The record SHALL
be its own file, named from the run time and the project, so that two runs, even from two PCs, never write to the same
file. The tool SHALL NOT overwrite or edit an earlier record.

#### Scenario: A run completes
- **WHEN** a run finishes and both outputs name the same project
- **THEN** one new file appears in the run log folder, and the files of earlier runs are unchanged

#### Scenario: A run stops before the end
- **WHEN** the deliverable is written but the analysis fails, or the two outputs name different projects
- **THEN** no record is written, because the outputs do not describe one budget

#### Scenario: Two runs in the same minute
- **WHEN** two runs of the same project finish within the same minute
- **THEN** each has its own file and neither is overwritten

### Requirement: A record states the project, the time and the mode
A record SHALL state the project name as typed on the input form, the run time in local time, the project mode (New
prospect or Existing project), whether Stable Operation is set, the budget year, the name of the deliverable file, and
the VAT basis of the deliverable (inclusive or exclusive).

#### Scenario: Existing project
- **WHEN** the input form is in Existing project mode
- **THEN** the record says so and gives the budget year of the deliverable

### Requirement: Completeness counts the Required lines
Completeness SHALL be measured on the Required leaf lines of the AI Guideline classification that appear on
`2. Budget-Management Fund` and `2.2 Common area Fund` (group and subtotal rows are not lines). For each such line
the record SHALL classify the annual figure on the finished deliverable as one of:
- **filled:** a figure above 0;
- **zero with a stated reason:** a figure of 0 and a non-empty remark that is not a form placeholder;
- **zero with no reason:** a figure of 0 and no usable remark.

The record SHALL give the three counts, the total number of Required lines, and the completeness percentage, which is
filled lines divided by Required lines. A line that is zero with a stated reason counts as not complete. A Required
line that the deliverable does not contain is listed in the count of missing lines and is not part of the total.

#### Scenario: A mix of lines
- **WHEN** 100 Required lines are measured, 62 carry a figure, 30 are zero with a reason and 8 are zero with no reason
- **THEN** the record shows 62, 30, 8, a total of 100 and a completeness of 62%

#### Scenario: A zero with a reason is not complete
- **WHEN** a Required line is zero and its remark explains why
- **THEN** it counts under "zero with a stated reason" and not under "filled"

### Requirement: Money figures come from the recalculated deliverable
The record SHALL give, in VND per year as the deliverable states them, the revenue (section R), the expense (section E)
and the surplus (revenue minus expense) of `2. Budget-Management Fund`. The figures SHALL be read after Excel has
recalculated the workbook, not from cached values of the file as written. The record SHALL also give the number of
formula-error cells found on the deliverable.

#### Scenario: Surplus is revenue minus expense
- **WHEN** the recalculated revenue is 34,000,000,000 VND and the expense is 27,000,000,000 VND
- **THEN** the record shows a surplus of 7,000,000,000 VND

#### Scenario: Common area fund
- **WHEN** the deliverable also has a `2.2 Common area Fund`
- **THEN** its Required lines count toward completeness, and its money is not added to the Management Fund figures

### Requirement: Profit to Savills is read from the analysis workbook
The record SHALL give the Total Profit Value of the analysis workbook's Summary sheet (Savills' own service fee less the
staff, operating and capex costs it carries), the management fee revenue it is measured on, and the cost basis the PM
selected (Must-Have or Full). It SHALL be shown beside, and never merged with, the fund surplus.

#### Scenario: Both profit figures
- **WHEN** a record is written for a project
- **THEN** it holds the fund surplus and the Savills profit as two separate fields

### Requirement: A figure that cannot be read stays blank and says why
When Excel cannot be driven, or a sheet or a label that the measurement needs is not found, the tool SHALL still write
the record, leave the affected figures blank (never 0), set a status that names the reason, and print a one-line
warning in the run output. The project name, time, mode and file names SHALL still be filled.

#### Scenario: Excel is not installed
- **WHEN** the run happens on a PC without Excel
- **THEN** the record is written with blank money, profit and completeness figures, the status says Excel was unavailable, and the run still ends as successful

#### Scenario: A needed label is missing
- **WHEN** the deliverable has no row for section R
- **THEN** revenue and surplus are blank and the status names the missing row; the other figures are still given

### Requirement: The run log never affects the run
Any failure while measuring or writing the record (a locked or unwritable folder, an Excel error, an unexpected
workbook shape) SHALL be caught, reported as a one-line warning, and SHALL NOT change the exit status of `run.py`
nor alter the deliverable, the roster or the analysis. The measurement SHALL work on copies and SHALL NOT open the
output workbooks for writing.

#### Scenario: The folder cannot be written
- **WHEN** the run log folder is read-only
- **THEN** the run prints a warning that no record was written, ends with the same status as without the log, and the three workbooks are as they would have been

### Requirement: Records carry no information the dashboard should not show
A record SHALL hold figures and names only. It SHALL NOT hold the roster, per-person pay, remarks or any cell text
beyond the project name and the file name.

#### Scenario: Content of a record
- **WHEN** a record is opened
- **THEN** it contains only the fields named in this capability
