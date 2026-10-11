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

#### Scenario: Inclusive-of-VAT run

- **WHEN** `2. Budget-Management Fund!F7` selects an inclusive-of-VAT treatment (`KHÔNG KHOÁN` or
  `THU HỘ CHI HỘ`) and the pipeline writes a remark for a figure
- **THEN** that remark SHALL contain the VAT-treatment sentence with the budget year

#### Scenario: Exclusive-of-VAT run

- **WHEN** `2. Budget-Management Fund!F7` selects the exclusive-of-VAT treatment (`KHOÁN`)
- **THEN** no remark SHALL carry the VAT-treatment sentence

#### Scenario: A line priced from an entered rate

- **WHEN** a management-fee line (`RM.*`) is priced from a rate the PM entered, in any VAT treatment
- **THEN** its line-level remark SHALL state the entered rate's VAT basis
- **AND** SHALL end with "Doanh thu hạng mục này dự ước tại năm <budget year>."
- **AND** SHALL NOT contain the generic VAT-treatment sentence
