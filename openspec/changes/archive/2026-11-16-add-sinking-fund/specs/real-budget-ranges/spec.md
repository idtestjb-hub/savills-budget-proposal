## ADDED Requirements

### Requirement: The build also writes an anonymous sinking-fund reference

The range build SHALL also write one anonymous data file of sinking-fund values, with one row per project and code.
It SHALL use the same project choice, the same checked fee-paying NFA and the same CPI as the management-fund values.
For each expense code on the project file's sinking-fund budget sheet, the row SHALL hold:
- the anonymous project id;
- the budget year;
- the driver: m² of fee-paying NFA, or lifts for ERLM1–ERLM4 and ESA1;
- the value per driver unit per month, excluding VAT, before and after bringing it to 2027 prices.

The sheet SHALL be read under these rules:
- **Amount:** the line's Total Price (column H, unit price × times, or the schedule sum), not the column the store
  guessed from its header.
- **Budget year:** a sinking-fund sheet whose budget year differs from the file's is left out. Hidden sheets are read:
  the template ships the sheet hidden.
- **Several sheets of the same year** (for example two blocks A and B) are summed.
- **Placeholders:** a sheet whose expense lines all carry the same amount (5 lines or more) is a placeholder and is left
  out.
- **VAT** is taken out at each line's own date-based factor.
- **Lifts:** the lift count comes from the master list by folded project name, one row only. A project without it
  gives no value for the lift codes.

The file SHALL contain no project or file name. The build SHALL refuse to write if one would land in it, as for the
management-fund file. Its README SHALL give, per code, the number of projects and the median.

#### Scenario: Form variant with the prior year in the read column

- **WHEN** a sinking-fund sheet's store column is the prior year's approved budget
- **AND** column H holds the budget year
- **THEN** the reference value SHALL come from H

#### Scenario: Placeholder sheet

- **WHEN** all 198 expense lines of a sheet carry the same amount
- **THEN** that project SHALL give no sinking-fund values
- **AND** the README SHALL count it as "placeholder, left out"
