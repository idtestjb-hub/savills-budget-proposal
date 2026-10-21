## MODIFIED Requirements

### Requirement: Every remark for an inclusive-of-VAT figure carries the VAT-treatment sentence

When the workbook's VAT-treatment switch (`2. Budget-Management Fund!F7`, the "Mô hình tài chính"
selector — `KHOÁN` / `KHÔNG KHOÁN` / `THU HỘ CHI HỘ`) is set so that figures include VAT, every
remark the pipeline writes for a cost or revenue figure — line-level and composed — SHALL contain
the guideline's VAT-treatment sentence, naming that the figure includes VAT and the budget year it
was estimated for. When the switch is set to the exclusive-of-VAT option (`KHOÁN`), the sentence
SHALL NOT be added. A single shared helper SHALL produce this sentence for both the line-level and
the composed remarks, keyed on the same switch.

One exception (decision W3, 2026-10-11): a management-fee line priced from a rate the PM entered
already states that rate's own VAT basis. Its line-level remark SHALL end with the sentence
"Doanh thu hạng mục này dự ước tại năm <budget year>." and SHALL NOT carry the generic VAT-treatment
sentence, which would contradict an entry made excluding VAT.

A second exception (decision K14, 2026-10-11): the management-fee narrative on `1. Summary` (`K14`)
describes revenue and states each product's VAT basis inside its text. It SHALL end with
"Doanh thu hạng mục này dự ước tại năm <budget year>." on every run, and SHALL NOT carry the generic
VAT-treatment sentence.

#### Scenario: Inclusive-of-VAT run

- **WHEN** `2. Budget-Management Fund!F7` selects an inclusive-of-VAT treatment (`KHÔNG KHOÁN` or
  `THU HỘ CHI HỘ`) and the pipeline writes a remark for a figure
- **THEN** that remark SHALL contain the VAT-treatment sentence with the budget year, unless one of the
  two exceptions applies to it

#### Scenario: Exclusive-of-VAT run

- **WHEN** `2. Budget-Management Fund!F7` selects the exclusive-of-VAT treatment (`KHOÁN`)
- **THEN** no remark SHALL carry the VAT-treatment sentence

#### Scenario: A line priced from an entered rate

- **WHEN** a management-fee line (`RM.*`) is priced from a rate the PM entered, in any VAT treatment
- **THEN** its line-level remark SHALL state the entered rate's VAT basis
- **AND** SHALL end with "Doanh thu hạng mục này dự ước tại năm <budget year>."
- **AND** SHALL NOT contain the generic VAT-treatment sentence

#### Scenario: The summary fee narrative

- **WHEN** `1. Summary!K14` is written, whether its products use entered or comparable rates
- **THEN** it SHALL state each priced product's VAT basis
- **AND** SHALL end with "Doanh thu hạng mục này dự ước tại năm <budget year>."
- **AND** SHALL NOT contain the generic VAT-treatment sentence

## ADDED Requirements

### Requirement: The client deliverable names no other project

No text on any sheet of the client deliverable, including text inside a formula, SHALL name a project other than this
one. Where a remark draws on another project's figures, it SHALL say "dự án tham chiếu" and MAY state how many reference
projects were used. A figure this project applies SHALL still be shown even when it equals a reference project's own
figure; only the attribution goes. Text the standard form ships that names other projects SHALL be overwritten with
neutral text, and recorded for the form owner. The internal analysis SHALL keep every name.

Verification SHALL scan every deliverable sheet, cell text and formula text, against names drawn from the data:
- the comparable projects;
- the hand-checked comparables, including the excluded ones;
- the projects that cost and capital-expenditure ratios come from.

This project's own name SHALL be excluded from the scan. Any match SHALL fail the check.

#### Scenario: A remark priced from a reference project's ratio

- **WHEN** a cost line is priced from a reference project's VND/m² ratio
- **THEN** its remark SHALL say "dự án tham chiếu" and SHALL NOT name that project

#### Scenario: Analysis keeps names

- **WHEN** the internal analysis is generated for the same project
- **THEN** its remarks and comparison sheet SHALL still name the reference projects

#### Scenario: Scan catches a name in a formula

- **WHEN** a deliverable formula contains a reference project's name as a text literal
- **THEN** verification SHALL fail and name the cell

### Requirement: A remark cites an input by its label

A remark or run message that points the PM to an input SHALL name the input's label on the form, not a cell address,
so that a change to the form's layout cannot make it point at the wrong field.

#### Scenario: Savills' fee inputs

- **WHEN** `EMH1`'s remark points to the fee inputs
- **THEN** it SHALL name the "Fixed Monthly Fee" or "% of Collected Management Fee" label, and SHALL NOT contain a cell
  address

### Requirement: The clearance and suction line says a residential quote is awaited

`ERCS1` SHALL stay at 0 until a sourced residential unit price exists. Its reason SHALL say that residential quotes are
being requested.

#### Scenario: ERCS1 reason

- **WHEN** the deliverable is generated
- **THEN** `ERCS1` SHALL be 0 and its remark SHALL say residential quotes are awaited
