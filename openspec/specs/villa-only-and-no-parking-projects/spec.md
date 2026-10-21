# villa-only-and-no-parking-projects Specification

## Purpose

Lets a project with no apartments (villas only) or with no parking bays run end to end: the total-NFA gate, the villa allocation column, defined parking formulas at 0 bays, and a fee sentence that names only products with area (change `support-villa-only-and-no-parking`, signed off 2026-10-19).

## Requirements

### Requirement: A project without apartments runs

The tool SHALL accept an input form whose Apartment NFA is blank or 0 when the total NFA over all products is above 0.
It SHALL refuse a form whose total NFA is 0, with a message that names the Product Mix.

#### Scenario: Villas only
- **WHEN** the Product Mix has NFA only on the Villas row
- **THEN** the run SHALL finish, `RM.VI` SHALL carry the villa fee and `RM.AP` SHALL be 0

#### Scenario: No product area at all
- **WHEN** every product row has NFA 0
- **THEN** the run SHALL stop with an error that names the Product Mix

### Requirement: Villas take the apartment allocation column when there are no apartments

When the Apartment NFA is 0, the apartment allocation weight SHALL be the Villas NFA in `2. Budget-Management Fund`
BG10, `A2` M7, `A3` P7 and `A4` P7, each with a note saying villas are counted in the apartment column. `'0. Info'!D8`
SHALL stay empty. When the Apartment NFA is above 0, these cells SHALL be as before.

#### Scenario: Villas only, with car bays
- **WHEN** a project has Villas NFA 40,000, no apartments and 50 car bays
- **THEN** `A2` M7 SHALL be 40,000 and `A2` P7 SHALL be 50

#### Scenario: A project with apartments
- **WHEN** a project has Apartment NFA above 0
- **THEN** BG10 SHALL keep `='0. Info'!$D$8`, and the row 7 cells of A2-A4 SHALL be as before

### Requirement: A project without parking bays has no undefined parking formula

When a project has no monthly parking revenue weight, BM11 SHALL be 1 and BN11 SHALL be 0, with a note. On
`Tiến độ lấp đầy bãi xe`:
- D6 SHALL be the total units of all products when there are no apartment units;
- a vehicle type with 0 bays SHALL have every fill formula that divides by its bay count written as 0, with a note.

#### Scenario: Zero car and motorbike bays
- **WHEN** a project has 0 car bays and 0 motorbike bays
- **THEN** the run SHALL finish, BM11 SHALL be 1, and the recalculated deliverable SHALL have no `#DIV/0!` cell

### Requirement: The fee sentence leaves out products without area

The `RM` sentence on `1. Summary` SHALL leave out a product whose NFA is 0 and that has no recorded unit rate.

#### Scenario: Villas only
- **WHEN** a villa-only project is run
- **THEN** the sentence SHALL name the villa area and rate, and SHALL NOT name the apartment
