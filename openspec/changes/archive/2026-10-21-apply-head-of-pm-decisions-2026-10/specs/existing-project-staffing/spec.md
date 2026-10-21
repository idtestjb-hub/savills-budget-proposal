## ADDED Requirements

### Requirement: New-prospect staffing rules do not apply in Existing-project mode

In Existing-project mode, the rules for a new prospect's staff cost (the 24/7 holiday rule, the night-shift rule and
the calendar working-day count) SHALL NOT be applied. The holiday and night allowance SHALL come from the PM's prior-year
holiday and night-duty table, recalculated only as this capability already states. A blank table SHALL be flagged in
the run output and in `EMH3`'s remark, and SHALL NOT be filled by the tool. The dated tariff and VAT rules do apply in
this mode; they belong to the capability `dated-tax-and-tariff-rates`.

#### Scenario: Blank duty table

- **WHEN** an Existing-project input has an empty holiday and night-duty table
- **THEN** the run output and `EMH3`'s remark SHALL say the table is empty
- **AND** the tool SHALL NOT infer duty counts from the shift codes

#### Scenario: Working days unchanged

- **WHEN** an Existing-project budget is generated before and after this change, with the same input and the same prices
- **THEN** its staff lines SHALL be unchanged
