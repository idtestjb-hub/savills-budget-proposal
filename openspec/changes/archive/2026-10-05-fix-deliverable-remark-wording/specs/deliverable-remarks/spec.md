## ADDED Requirements

### Requirement: A narrative quotes the unit prices the lines are priced at

When a `1. Summary` narrative states a rate, the rate SHALL be the unit price the corresponding lines
are priced at (a monthly fee per square metre, a monthly price per parking slot), not a figure derived
by dividing a year's revenue by area or slots. A year-1 amount that reflects an occupancy ramp MAY be
quoted as an amount, but not as a rate.

#### Scenario: The fee narrative quotes the priced rate
- **WHEN** the management-fee narrative is composed for a product priced at 15,900 VND per square metre per month, with revenue ramped over the year
- **THEN** the narrative states 15,900 VND/m²/tháng for that product
- **AND** it does not state the ramped year-1 average as the fee

#### Scenario: The parking narrative quotes the priced monthly price
- **WHEN** the parking narrative is composed for slots priced at 110,000 VND (motorbike) and 1,100,000 VND (car) per month
- **THEN** the narrative states those two prices, and the year-1 revenue separately as an amount

### Requirement: A listed breakdown adds up to the total it follows

When a narrative states a count or amount and then lists the items that make it up, the listed items
that are counted SHALL sum to the stated figure. An item that is listed but not counted (for example a
supervisor that is not priced in that line) SHALL be marked as not counted.

#### Scenario: A supervisor is listed but not priced
- **WHEN** the cleaning narrative lists three priced posts and a supervisor whose cost is not in that line
- **THEN** the stated total is three posts
- **AND** the supervisor is shown as a separate post that is not included in the priced total

### Requirement: A staff count states what it counts

A staff count in client-facing text SHALL say whether it counts positions on duty each day or people
employed, so that two counts of the same group in different places cannot read as a disagreement.

#### Scenario: Two counts of the management office staff
- **WHEN** the staff narrative and the drinking-water remark both state a number for the management office
- **THEN** each states its basis (positions on duty per day, or people including the rest-day rotation)

### Requirement: A remark gives one source for a unit price

A line-level remark SHALL NOT attribute one unit price to two different sources. When the price is an
example taken from the costing guideline, the remark SHALL say so and SHALL NOT also say the price was
taken from comparable projects.

#### Scenario: The water price is a guideline example
- **WHEN** the water remark quotes a unit price that comes from the costing guideline's worked example
- **THEN** the remark names that as the source, with its date
- **AND** it does not state that the price comes from projects of the same size

### Requirement: Client-facing text carries no internal wording on any sheet

Text in any cell of the client deliverable that the pipeline writes SHALL NOT contain internal wording:
file names or function names of the tool, the name of the programming language it is written in,
phrases describing a software change ("this change"), another project's measured figures used to
justify a method, or the name of an internal working document. Text that comes from the standard form
itself is exempt, and each exempt cell SHALL be listed explicitly. A caveat that a figure rests on a
single reference project, or on a price from an earlier year, SHALL be kept and SHALL be worded for the
Developer reading it.

#### Scenario: A function name in `0. Info`
- **WHEN** a remark on `0. Info` names a function of the tool
- **THEN** verification fails and names the sheet and cell

#### Scenario: Another project's figure in a remark
- **WHEN** a line-level remark on a fund sheet quotes a figure measured on a different project to justify the method
- **THEN** verification fails and names the sheet and cell

#### Scenario: A caveat survives in client words
- **WHEN** the electricity remark states that consumption rests on one reference project and the unit price is dated
- **THEN** both caveats are present, without change-process wording or an internal document name

### Requirement: Verification scans every client-facing text cell for internal wording

Verification SHALL, on every run, scan the text of every sheet of the generated client deliverable for
the internal wording the previous requirement forbids, not only column T of the two fund sheets. The
list of forbidden words and the list of exempt template cells SHALL each be kept in one place.

#### Scenario: Whole-workbook scan
- **WHEN** verification runs against the synthetic sample
- **THEN** every text cell of every deliverable sheet is scanned
- **AND** the run reports how many cells were scanned and how many were exempt

#### Scenario: An unlisted template phrase fails the scan
- **WHEN** a forbidden word appears in a cell that is not on the exempt list
- **THEN** verification fails and names the cell
