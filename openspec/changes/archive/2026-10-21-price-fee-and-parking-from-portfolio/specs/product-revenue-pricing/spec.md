## MODIFIED Requirements

### Requirement: Each product's applied rate is decided once per run and shared by both workbooks

For each product a project prices, the pipeline SHALL decide the applied management-fee rate (VND
per m² per month) and the source of that rate exactly once per run. Every figure, remark and table
in either workbook that uses or shows a product's rate SHALL take it from that one decision. This
covers:
- the revenue rows on `2. Budget-Management Fund`;
- the `0. Info` fee table and its complete-total note;
- the `Comparison` sheet;
- the analysis workbook's `Management Fee`, `Comparison` and `Summary` sheets.

The order of sources SHALL be the same in both workbooks:
1. a rate the PM entered on the Product Mix row (not capped, applied as entered);
2. for Apartment, the median apartment management-fee rate of the real budgets of Savills-managed
   projects (the real-budget range for `RM.AP`: the project itself left out, IQR outliers dropped, at
   least 10 projects, 2027 prices), converted from its excluding-VAT basis to the deliverable's basis
   at the VAT rate of the budget period's first month;
3. the comparable-derived rate, with the existing location rate-swing cap — for Apartment only when
   the range cannot be formed (fewer than 10 projects, or no values file), and for every other product
   as its own source;
4. for a non-Apartment product with no comparable rate, the project's applied Apartment rate;
5. for Apartment, when neither the range nor a comparable Apartment rate exists, the blended
   whole-property rate. Both workbooks SHALL use the same one.

The two nearest comparables SHALL still be selected and shown on both `Comparison` sheets and SHALL
still drive the proposal benchmark verdict; when the Apartment rate comes from the range, those sheets
SHALL also show the comparable-derived rate the range replaced, labelled as such.

Data files read: `Budget_Agent/data/real_budget_ranges/Ref_RealBudgetValues.csv` (the `RM.AP` rows),
`Budget_Agent/data/generation_B_verified/Ref_CPI_VN.csv`, and the comparable tables already read. No
data file is written. The recorded baseline figure `derived_apartment_rate` and every revenue figure it
feeds move on the standard sample; verify runs with the baseline gates open until group 10 re-records them.

#### Scenario: Every place that shows the Apartment rate shows the same value

- **WHEN** both generators run against the same input
- **THEN** the Apartment rate SHALL be identical, in VND per m² per month, in each of these places:
  `0. Info` (Apartment fee cell), the `RM.AP` remark, the deliverable's `Comparison` sheet, and the
  analysis workbook's `Management Fee`, `Comparison` and `Summary` sheets

#### Scenario: Consolidation moves no figure

- **WHEN** the deliverable and the analysis workbook are generated before and after the one-decision-point
  consolidation (change `use-operating-project-actuals`, P5) is implemented, from the same input, for the
  standard synthetic project and for one more project with at least three priced products
- **THEN** every formula and every number SHALL be identical between the before and after copies
- **AND** the comparison SHALL be recorded cell by cell
- **AND** the range source added by this change is measured separately, as its own before/after

#### Scenario: The Apartment rate comes from the range

- **WHEN** no Apartment rate is entered and at least 10 real budgets remain in the `RM.AP` range
- **THEN** the applied Apartment rate SHALL be the range's median × (1 + the VAT rate of the budget
  period's first month) when the deliverable includes VAT, else the median as it is
- **AND** the `RM.AP` remark SHALL quote the number of projects, the median and the P25–P75 band and
  SHALL name no project

#### Scenario: The range cannot be formed

- **WHEN** fewer than 10 real budgets remain in the `RM.AP` range, or the values file is absent
- **THEN** the applied Apartment rate SHALL be the comparable-derived rate exactly as before this change
- **AND** the remark SHALL say the rate comes from the reference projects

#### Scenario: An entered Apartment rate still wins

- **WHEN** the PM enters an Apartment rate
- **THEN** that rate SHALL be applied unchanged, and the range SHALL be shown on the internal analysis only

#### Scenario: Other products follow the new Apartment rate as their fallback

- **WHEN** a product has neither an entered rate nor a comparable rate
- **THEN** it SHALL be priced at the applied Apartment rate, which is the range median when that is the
  Apartment source

#### Scenario: The no-comparable fallback agrees across workbooks

- **WHEN** no comparable in the master table carries an Apartment rate and the range cannot be formed
- **THEN** both workbooks SHALL apply the same blended fallback rate
- **AND** both SHALL say that the rate is a fallback
