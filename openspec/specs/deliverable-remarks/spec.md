## Purpose

Defines how the client deliverable explains the reasoning behind its figures: a composed section
narrative on the grand-total sheet (`1. Summary`) built to the AI Guideline's own recipe, in the
guideline's own wording style, with the mandatory VAT-treatment sentence — so a PM can hand the
budget to a client and every total says where it came from.

**Generation**: this capability governs the **Generation A** deliverable-writing pipeline only
(`generate_project_budget.py`, with the shared VAT helper also used by the analysis-facing
`_opex_remark`). It reads only what the pipeline already reads, modifies no Generation A or
Generation B table, and changes no Fact/Dim join key — the Copilot Studio package's live data is
unaffected. No budgeted figure changes; remarks are text.

## Requirements

### Requirement: The grand-total sheet composes a narrative for every section total it reports

For every PART-1 total on `1. Summary` that carries a non-zero figure, the deliverable SHALL write a
composed remark in the sheet's Remarks column, generated from the project's own data — not left
blank, and not a copy of a single line item's remark. A total that is zero MAY be left without a
narrative.

#### Scenario: A non-zero section total has a narrative

- **WHEN** the deliverable is generated and a PART-1 total on `1. Summary` is non-zero
- **THEN** that total SHALL have a composed remark in the Remarks column
- **AND** the remark SHALL be derived from this project's inputs, not a fixed string that ignores
  the project

#### Scenario: A blank pull is replaced

- **WHEN** the standard template ships a `1. Summary` Remarks cell that pulls a single line's remark
  from the detail sheet, or leaves it blank
- **THEN** the pipeline SHALL overwrite it with the composed section narrative

### Requirement: An aggregate total's narrative names every child line that has a figure

Where a `1. Summary` total sums a group of detail lines (for example other operating income,
administrative expense, bank and audit, M&E operation, accreditation, repairs and maintenance), its
narrative SHALL enumerate, by item name, every child line the pipeline wrote a figure to, as a
bulleted list (one child per line, matching the AI Guideline's own worked-example format). It SHALL
NOT list a line that carries no figure.

#### Scenario: Every funded child is listed

- **WHEN** an aggregate `1. Summary` total is composed and the pipeline wrote figures to some of its
  child lines
- **THEN** the narrative SHALL name each of those child lines
- **AND** SHALL omit the child lines that carry no figure

### Requirement: A computed total's narrative follows the guideline recipe for that code

Where the costing catalogue records a composition recipe for a `1. Summary` row, the narrative for
that row SHALL contain each part the recipe lists, filling the guideline's own note text (its
`....` placeholders) with this project's own data rather than a generic paraphrase. In particular:

- the management-fee total SHALL state the chargeable area by product, the applied fee rate by
  product with its VAT status, and the developer pre-collection assumption — including how many
  months of the fee the developer collects on handover when that figure has been entered for the
  project, and describing the mechanism without a month count when it has not;
- the security and cleaning totals SHALL state the staffing positions broken out by role and the
  unit rate;
- the water, electricity and diesel totals SHALL state the assumed consumption, the tariff with the
  legal reference the catalogue names, and the occupancy basis;
- where the recipe names a fixed legal sentence, the narrative SHALL include it.

A recipe part with no corresponding project data SHALL be described qualitatively rather than
filled with an invented number.

#### Scenario: A recipe part is missing

- **WHEN** a `1. Summary` total's catalogue recipe lists parts and one is absent from the composed
  narrative
- **THEN** verification SHALL fail and name the total and the missing part

#### Scenario: A code with no recipe

- **WHEN** a non-zero `1. Summary` total has no catalogue recipe
- **THEN** the aggregate-listing requirement above SHALL still apply, and no additional part check
  SHALL be imposed

#### Scenario: A recipe part has no project data behind it

- **WHEN** a recipe part depends on a project fact the intake form has not captured (for example the
  developer's handover pre-collection term)
- **THEN** the narrative SHALL describe the underlying mechanism without a fabricated figure
- **AND** SHALL state the real value once the project's own data provides it

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

### Requirement: `0. Info` states each priced product's area basis

For every product row `0. Info` prices (Apartment/Officetel/Office/Shophouse and any other product
with a fee-table row), the deliverable SHALL write a remark stating the area's basis and the year
it was last confirmed, using the project's own "Area basis / drawing reference" intake field when
the PM has supplied one. When that field is blank, the remark SHALL say the area is PM-supplied
without inventing a drawing or legal citation.

#### Scenario: A PM-supplied area basis is shown

- **WHEN** the deliverable is generated and the PM has entered an area basis / drawing reference
  for a priced product
- **THEN** that product's `0. Info` remark SHALL state the basis text and the confirmation year
  entered

#### Scenario: No area basis was supplied

- **WHEN** a priced product has no area basis / drawing reference entered
- **THEN** its `0. Info` remark SHALL state the area is PM-supplied, without a fabricated drawing
  or legal citation

### Requirement: `A2`/`A3` carry every canonical position's duty description

The standard deliverable template already carries the AI Guideline's full duty description for
every canonical Security (`A2`) and Cleaning (`A3`) position, as its own shipped content — the
pipeline SHALL NOT overwrite it, and SHALL NOT need to write it. The deliverable SHALL still carry
that description, unmodified, for every canonical position the template defines.

#### Scenario: A canonical position keeps its template description

- **WHEN** the deliverable is generated
- **THEN** every canonical position defined on `A2`/`A3` SHALL still carry the template's own duty
  description, exactly as shipped

### Requirement: The composed summary narratives are Vietnamese

Each composed `1. Summary` narrative SHALL be written in Vietnamese, matching the language and
wording style of the AI Guideline's own note text and the worked sample's demonstrated usage. Every
line-level remark on the detail sheet (`2. Budget-Management Fund`/`2.2 Common area Fund`, column T)
that the pipeline writes SHALL also be written in Vietnamese — both a computed cost/revenue narrative
(where the pipeline priced the code from this project's own data) and a flagged-zero / no-method
remark (where the pipeline explains why a code was left at zero). A flagged-zero remark's Vietnamese
text SHALL describe the reason in plain terms and SHALL NOT name an internal source file (for example
`Costing_Method_Catalogue.csv`) or other engineering artifact; that citation MAY be kept in a code
comment for engineering reference but not in the cell text. The VAT-treatment sentence SHALL also be
Vietnamese, as before.

#### Scenario: A composed narrative is Vietnamese

- **WHEN** a `1. Summary` narrative is composed
- **THEN** it SHALL be written in Vietnamese
- **AND** SHALL NOT require an English counterpart to be understood

#### Scenario: A computed line-level remark is Vietnamese

- **WHEN** the pipeline writes a line-level remark on the detail sheet for a code it priced from this
  project's own data
- **THEN** that remark SHALL be written in Vietnamese
- **AND** SHALL NOT require an English counterpart to be understood

#### Scenario: A flagged-zero remark is Vietnamese and names no internal file

- **WHEN** the pipeline writes a remark stating that a code has no pricing method and was left at zero
- **THEN** that remark SHALL be written in Vietnamese
- **AND** SHALL NOT name an internal source file or other engineering artifact in the cell text

### Requirement: Unit labels inside a Vietnamese remark are Vietnamese

A consumption figure quoted in a Vietnamese remark (on `1. Summary` or a fund sheet's column T)
SHALL carry its unit in Vietnamese: "m3/tháng" for water, "kWh/tháng" for electricity, "lít/tháng"
for diesel. The unit's source data and the internal analysis workbook MAY keep their English units;
only the client-facing Vietnamese text changes.

#### Scenario: The water remark quotes monthly consumption

- **WHEN** the pipeline writes the water (EEW) remark
- **THEN** the consumption figure SHALL read in "m3/tháng", not "m3/month"

#### Scenario: The electricity and diesel remarks quote monthly consumption

- **WHEN** the pipeline writes the electricity (EEE) or diesel (EED) remark
- **THEN** the consumption figure SHALL read in "kWh/tháng" or "lít/tháng" respectively

#### Scenario: A remark still carrying an English unit fails verification

- **WHEN** verification runs and a composed energy narrative on `1. Summary` lacks its Vietnamese
  unit ("m3/tháng" for water, "kWh/tháng" for electricity, "lít/tháng" for diesel)
- **THEN** verification SHALL fail and name the narrative and the missing part

### Requirement: Verification confirms remark content on every run

Verification SHALL open the generated deliverable, and fail when: a non-zero `1. Summary` PART-1
total has no composed narrative; an aggregate total's narrative omits a child line that has a
figure; a total's catalogue recipe part is absent from its narrative; a composed narrative carries
no Vietnamese content; a non-blank line-level remark carries no Vietnamese content; a line-level
remark names an internal source file or artifact in its text; or, on an inclusive-of-VAT run, a
written remark for a figure lacks the VAT-treatment sentence. This check SHALL run on every
verification run and SHALL NOT depend on a recorded numeric baseline.

#### Scenario: A missing narrative fails the run

- **WHEN** verification runs and a non-zero PART-1 total on `1. Summary` has no composed narrative
- **THEN** verification SHALL fail and name the total

#### Scenario: An unlisted funded child fails the run

- **WHEN** an aggregate total's narrative does not name a child line that carries a figure
- **THEN** verification SHALL fail and name the total and the omitted child

#### Scenario: A non-Vietnamese line-level remark fails the run

- **WHEN** verification runs and a non-blank line-level remark carries no Vietnamese content
- **THEN** verification SHALL fail and name the code and the row

#### Scenario: A line-level remark naming an internal file fails the run

- **WHEN** verification runs and a line-level remark's text names an internal source file or artifact
- **THEN** verification SHALL fail and name the code, the row, and the artifact named

#### Scenario: Remarks are not a baselined figure

- **WHEN** a verification run compares the deliverable to its recorded baselines
- **THEN** the remark-content check SHALL run independently of that comparison, and changing a
  remark's wording SHALL NOT move any baselined figure

### Requirement: Verification confirms the extended remark coverage

Verification SHALL open the generated deliverable, and fail when: a priced `0. Info` product has no
area-basis remark; or a canonical `A2`/`A3` position (per the recorded canonical-position reference)
does not carry its duty description. This check SHALL run on every verification run and SHALL NOT
depend on a recorded numeric baseline, matching the existing remark-content check's independence
from baseline comparison.

#### Scenario: A missing `0. Info` remark fails the run

- **WHEN** verification runs and a priced product on `0. Info` has no area-basis remark
- **THEN** verification SHALL fail and name the product

#### Scenario: A missing canonical description fails the run

- **WHEN** verification runs and a canonical `A2`/`A3` position does not carry its recorded duty
  description
- **THEN** verification SHALL fail and name the position

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

### Requirement: A line priced from real Savills budgets says how

The remark on a line priced from the real-budget range SHALL say, in Vietnamese:
- the median in đ/m²/tháng, excluding VAT, at 2027 prices;
- the P25–P75 range;
- the number of Savills projects it comes from;
- the fee-paying NFA and the 12 months it is multiplied by;
- the VAT added.

It SHALL name no project. For `ESC1` and `ESC2` it SHALL also say that the figure stands in for the number of
events × the price per event, until the PM enters them. The remark SHALL pass the internal-wording scan, and its
units SHALL be Vietnamese.

Data files read: none beyond those of `real-budget-ranges`. Recorded baseline figures: see that capability.

#### Scenario: Pest control

- **WHEN** `ESS12` is priced from a range of 30 projects with median 120 đ/m²/tháng on 36,679 m²
- **THEN** its remark SHALL state the median 120 đ/m²/tháng, the P25–P75 range, "30 dự án do Savills quản lý", the
  36,679 m² and the 12 months, and the VAT 10% added for 2027

#### Scenario: Events

- **WHEN** `ESC1` is priced from the range
- **THEN** its remark SHALL also say that the figure stands in until the number of events and the price per event
  are entered

### Requirement: A revenue unit rate taken from the portfolio states its range without naming a project

Where `RM.AP`, `RP1` or `RP2` is priced from a portfolio range, the line's remark on `2. Budget-Management Fund`
SHALL say, in Vietnamese, that the unit rate is the median of the real figures of N Savills-managed projects,
SHALL quote the median and the P25–P75 band in the rate's own unit (VND per m² per month for `RM.AP`, VND per
vehicle per month for `RP1`/`RP2`), SHALL state the VAT basis of the quoted figures and, for `RM.AP`, the price
year, and SHALL name no project (decision D3). The `1. Summary` narratives and helper sheet B5 SHALL quote the
same applied unit rates. The former wording "theo đề xuất giữ xe của một dự án tham chiếu" SHALL appear only when
the range could not be formed and the former constant is used.

Where the unit rate is one the PM entered, the remark SHALL say so and SHALL name no portfolio statistic, in the
wording already used for an entered management-fee rate.

Data files read: none beyond the pricing itself. No data file is written. No baseline figure moves on account of
the wording.

#### Scenario: `RM.AP` priced from the range

- **WHEN** the Apartment rate is the range median
- **THEN** the `RM.AP` remark SHALL contain the number of projects, the median and the P25–P75 band in
  đ/m²/tháng, the words "chưa VAT" for the quoted figures and the applied rate after VAT, and the price year 2027
- **AND** verification's client-wording scan SHALL find no project name in it

#### Scenario: `RP2` priced from the range

- **WHEN** the car price is the master-list median
- **THEN** the `RP2` remark SHALL read, in Vietnamese, that the price is the median monthly car parking price of
  N Savills-managed projects, with the band, "đã gồm VAT", × the number of bays
- **AND** the `RPa` narrative on `1. Summary` SHALL quote the same price

#### Scenario: `RP1` priced from an entered price

- **WHEN** the PM enters a motorbike price
- **THEN** the `RP1` remark SHALL say the price is the one the PM entered and SHALL contain no "trung vị"

#### Scenario: Verification covers the new remarks

- **WHEN** verification runs on the standard sample
- **THEN** its remark assertions SHALL include the `RM.AP`, `RP1` and `RP2` range wording
