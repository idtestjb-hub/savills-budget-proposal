## ADDED Requirements

### Requirement: Verification exercises the operating-project path

Verification SHALL also run the full pipeline on a second synthetic project, isolated in the same
way as the standard sample so that it cannot read or write production data. That project's intake
SHALL fill the operating-project fields:
- the stable-operation switch set to Yes;
- an actual rate with its VAT basis for at least two products, and at least one product left to
  comparables;
- actual car and motorbike parking revenue;
- collect-on-behalf amounts for at least two products.

All of its values SHALL be fictional. It SHALL NOT carry any real project's figures.

On that project, verification SHALL fail and name the figure, giving each workbook's value in VND,
when any of these holds:
- a product with an entered rate is not priced at that rate in both workbooks;
- the product left to comparables is not priced as it would be without the new fields;
- any month's resident or parking fill is not 100%;
- `RM.0A` is not zero;
- `RP1` or `RP2` is not the entered figure × 12;
- the collect-on-behalf revenue lines and their paired expense lines do not sum to the same amount
  within 1 VND.

The second project's figures SHALL be recorded as a baseline of their own. The standard synthetic
project's recorded baseline SHALL NOT move.

This reads one new fixture intake workbook under `verification/fixtures/` and writes a new baseline
file for it under `verification/baselines/`. No existing baseline figure moves.

#### Scenario: The operating-project path passes

- **WHEN** verification runs and each operating-project figure is as entered
- **THEN** the operating-project section SHALL record a pass

#### Scenario: An entered rate that one workbook ignores fails verification

- **WHEN** one workbook prices a product at the comparable-derived rate although a rate was entered
  for it
- **THEN** verification SHALL fail
- **AND** SHALL name the product with both workbooks' revenue in VND

#### Scenario: An unbalanced collect-on-behalf pair fails verification

- **WHEN** the collect-on-behalf revenue lines and their paired expense lines differ by more than 1 VND
- **THEN** verification SHALL fail
- **AND** SHALL name the pair that does not balance

#### Scenario: The standard sample is unaffected

- **WHEN** verification runs after this change
- **THEN** every figure recorded for the standard synthetic project SHALL match its recorded
  baseline without a re-record
