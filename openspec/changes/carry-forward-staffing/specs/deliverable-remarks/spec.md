## ADDED Requirements

### Requirement: A changed staffing line states its adjustment after the original remark

In Existing-project mode, on every staffing line whose figure differs from the baseline (rows of `A1. Staff cost`,
EMH2, EMH3, EMH4), the remark SHALL keep the guideline's original remark first and SHALL append one Vietnamese
sentence beginning "Điều chỉnh so với NS <năm>:" that gives the previous figure, the new figure, the difference
in VND, and the reason (the generated reason or the PM's code and note). A line that did not change SHALL keep its
original remark only. The sentence SHALL use no internal wording and SHALL follow the existing rules on Vietnamese
text, unit labels and VAT sentences.

Data files read: none beyond the baseline roster. The change moves remark text only.

#### Scenario: A line changed by law

- **WHEN** EMH2 rises because the regional minimum wage rose
- **THEN** its remark SHALL read the original guideline remark, then "Điều chỉnh so với NS 2026:" with the old and
  new amount, the VND difference and the reason "điều chỉnh theo lương tối thiểu vùng"

#### Scenario: A line changed by the calendar

- **WHEN** EMH3 rises because the budget year has one more paid public holiday
- **THEN** its remark SHALL end with "Điều chỉnh so với NS <năm>:" and a reason naming the added holiday

#### Scenario: A line that did not change

- **WHEN** a staffing line equals its baseline
- **THEN** its remark SHALL be the original guideline remark, with no adjustment sentence

#### Scenario: The sentence is Vietnamese and clean

- **WHEN** the remark content check runs on the client deliverable
- **THEN** the adjustment sentence SHALL pass the same Vietnamese-only and no-internal-wording checks as every other remark
