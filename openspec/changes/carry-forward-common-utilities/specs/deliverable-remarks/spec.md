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

The months named for the actual average SHALL be the first and last month actually used, not the 12-month window
they sit in: 8 months from 01 to 08 of the prior year read "8 tháng (01/<năm>–08/<năm>)". When the approved amount
was entered on a different VAT basis from the deliverable's, the sentence SHALL quote it as approved, with its VAT
basis, followed by its equivalent on the deliverable's basis, and the difference SHALL be measured from that
equivalent. *(Both added after the 7.2 back-test, 2026-10-12.)*

Data files read: none beyond those of `existing-project-utilities`. No recorded baseline figure moves.

#### Scenario: A changed line

- **WHEN** an existing project's `EEE.C` moves from an approved 300,000,000 VND to 288,000,000 VND
- **THEN** the remark SHALL hold the guideline's remark followed by "Điều chỉnh so với NS <năm>: …" giving both amounts,
  the difference of −12,000,000 VND and its causes

#### Scenario: Fewer than 12 months, and an approved amount excluding VAT

- **WHEN** a project has actuals for 01–08/2026 only, an approved 2026 `EEE.C` of 300,000,000 VND excluding VAT, and
  a deliverable that includes VAT (8% throughout 2026)
- **THEN** the remark SHALL read "bình quân 8 tháng (01/2026–08/2026)", not "(09/2025–08/2026)"
- **AND** the sentence SHALL begin "Điều chỉnh so với NS 2026: NS đã duyệt 300,000,000 VND/năm (chưa gồm VAT), tương
  đương 324,000,000 VND/năm gồm VAT →"

#### Scenario: The text checks still pass

- **WHEN** the Existing-project sample is verified
- **THEN** the remark-content check and the internal-wording scan SHALL pass on `EEE.C` and `EEW.C`
