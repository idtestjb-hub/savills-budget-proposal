## ADDED Requirements

### Requirement: Changed common-area utility lines explain the change from last year

In "Existing project" mode, the remark on `EEE.C` and on `EEW.C` SHALL keep the guideline's original remark first. It
SHALL then add one Vietnamese sentence beginning "Điều chỉnh so với NS <năm>:" that states, in VND per year:
- the approved prior-year amount, when given;
- the budget-year amount;
- the difference;
- what moved it: actual consumption over the stated months, unit price and its legal basis, VAT rate, the PM override
  with its reason.

The sentence SHALL also name any flag: months missing, zero months, or fewer than 12 months used. Units SHALL be
Vietnamese ("kWh/tháng", "m3/tháng", "đ/kWh", "đ/m3"), and the sentence SHALL carry no internal wording. When the
approved prior-year amount is not given, the sentence SHALL state the actual basis without a difference.

Data files read: none beyond those of `existing-project-utilities`. No recorded baseline figure moves.

#### Scenario: A changed line

- **WHEN** an existing project's `EEE.C` moves from an approved 300,000,000 VND to 288,000,000 VND
- **THEN** the remark SHALL hold the guideline's remark followed by "Điều chỉnh so với NS <năm>: …" giving both amounts,
  the difference of −12,000,000 VND and its causes

#### Scenario: The text checks still pass

- **WHEN** the Existing-project sample is verified
- **THEN** the remark-content check and the internal-wording scan SHALL pass on `EEE.C` and `EEW.C`
