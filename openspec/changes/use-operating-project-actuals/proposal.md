## Why

On 2026-10-07 the pipeline rebuilt the budget of a real project that has been operating at stable
occupancy for years ("the stable-operation reference project": its 2026 budget, rates excl. VAT; VN:
*dự án đối chứng vận hành ổn định (2026, chưa VAT)*). It was then compared line by line with that
project's own approved budget. With every input the PM could supply, the pipeline produced:
- 51% of the real revenue and 41% of the real expense on `2. Budget-Management Fund`;
- a figure on 26 of the 127 lines that carry one in the real budget, and on 20 of its 46 Required lines.

Three causes are in the code, not in missing inputs:
- **The management fee comes from comparables even when the real rate is known.** The rate derived
  from the two comparables the pipeline picked was 60% of the project's real Apartment rate. Once
  the real rate was put in, management-fee revenue and Savills' fixed fee (`EMH1`) matched the real
  budget to within rounding.
- **The pipeline assumes every project is new.** Its fill-up curve starts at 0% and reaches 50% at
  the end of year 1. That curve is a constant in `fill_curve.py`, not an input, so an operating
  building is budgeted as if it were half empty.
- **The real budget's parking revenue and collect-on-behalf lines have no path into the pipeline.**
  The real budget uses parking revenue at its recorded monthly average. It also writes "thu hộ / chi
  hộ" (collect-on-behalf) water and electricity pairs. The pipeline has no field for the first and
  no line for the second.

To enter the real rate, the comparison run had to patch the Apartment rate in two places and the
Officetel rate in two more, all in the deliverable generator. The analysis generator derives the
rate a third time, and that was not patched. So on that run the two workbooks disagreed on the rate:
the analysis still showed the comparable-derived figure. One rate, computed once, is the
precondition for an entered rate to be safe.

Most of the expense gap comes from inputs the PM did not have: garden area, internal road area and
insured asset value. It also comes from lines the pipeline has no source for. Neither is in scope here.

## What Changes

This change groups five proposals, P1–P5. Each moves its own figures and is approved on its own.
**No code is written for P1–P4 until the Head of PM approves that proposal** (task group 0). P4 also
needs the AI Guideline owner, because it departs from the guideline. If a proposal is rejected, its
requirements and tasks are removed from this change before `/opsx:apply`.

- **P5. One rate resolver (done first).** Today the Apartment rate is derived twice in the
  deliverable generator and once more in the analysis generator. Non-Apartment rates are derived
  three times in the deliverable generator alone. All of these become one function that both
  generators call once per run. It returns each product's applied rate and where the rate came from.
  **Moves no figure**: the before/after deliverables must agree cell by cell.
- **P1. An entered real rate wins.** The intake form gets an optional per-product field for the
  real management-fee rate (VND/m²/month), with a VAT-basis label beside it. Where a rate is
  entered, it is used for that product in both workbooks, ahead of the comparable-derived rate and
  outside the ±20% swing cap. The remark says it is the PM's entered rate and states its VAT basis.
- **P2. Parking revenue from recorded actuals.** The form gets two optional fields: actual average
  monthly revenue for car parking and for motorbike parking. When the project is declared at stable
  operation, an entered figure replaces bays × default rate × fill for `RP2` / `RP1`. It is written
  flat across the twelve months.
- **P3. A "stable operation" switch.** This is an optional Yes/No field. With Yes, the resident and
  parking fill-up are 100% in every month, so `RM.0A` (developer's fee on unsold units) is zero, and
  electricity runs at full load. The remarks and the two fill-up sheets say the project is budgeted
  at stable operation, not on the new-building curve. With No or blank, nothing changes.
- **P4. Collect-on-behalf (thu hộ / chi hộ) lines.** For a project at stable operation, the form
  gets optional monthly water and electricity amounts collected on behalf, per product. Each amount
  is written twice, on the matching `RO3.*` / `RO4.*` revenue line and on its paired expense line, so
  revenue and expense both rise by the same amount and the surplus does not move. **This departs from
  the AI Guideline**, which today marks these lines "not estimated". The costing catalogue records
  the departure and the approval.
- **Verification** gains a second synthetic project with the operating-project fields filled. It
  checks the entered rate in both workbooks, `RM.0A` at zero, parking at the entered figures, and
  every collect-on-behalf pair netting to zero. A regression run of the reference project, on a
  clone outside SharePoint, measures each proposal's movement against the real budget.

Every new field is optional. A form that predates this change, or leaves the fields blank or the
switch off, produces exactly today's figures. **No recorded baseline moves.** The standard synthetic
project fills none of the new fields, so its 24 analysis figures and 8 ramped deliverable figures
are unchanged. The second synthetic project gets its own new baseline.

## Capabilities

### New Capabilities
- `parking-revenue-actuals`: monthly parking revenue taken from recorded actuals for a project at
  stable operation (P2).
- `pass-through-collections`: collect-on-behalf water and electricity written as equal revenue and
  expense pairs for a project at stable operation (P4).

### Modified Capabilities
- `product-revenue-pricing`: two added requirements, an entered real rate winning over the
  comparable rate (P1) and one shared rate resolver (P5).
- `occupancy-ramp`: an added requirement for the stable-operation switch (P3). This adds a
  requirement. It does not modify the curve requirement that the active change
  `add-multiyear-preopening-budget-phases` also modifies.
- `input-workbook-reading`: an added requirement that the new operating-project fields are
  optional. An absent label is read as blank, as product rows already are, and does not fail the run.
- `costing-method-catalogue`: an added requirement that a method departing from the AI Guideline
  records who approved the departure (P4).
- `budget-workflow-verification`: an added requirement that verification exercises the
  operating-project path on a second synthetic project.

## Impact

- **Code:**
  - `master_comparables.py` (or a new small module beside it): the shared rate resolver.
  - `generate_project_budget.py`: `read_input`, `fill_management_fund_sheet`, `build_budget`, the
    `0. Info` fee table, the parking block and the `1. Summary` narratives.
  - `generate_project_output.py`: the `Management Fee` sheet and the parking section.
  - `fill_curve.py`: a stable-operation path beside today's curve.
  - `build_project_input_form.py`: the new fields, for freshly built forms only.
  - `verification/`: the second synthetic project and its checks.
- **Data files:**
  - Read: the same seven files as today.
  - Written: `Costing_Method_Catalogue.csv` gains or updates the collect-on-behalf entries, and only
    if P4 is approved. No Generation A or B table changes, and no Fact/Dim key changes.
- **Live input form:** never rewritten by this change. New fields reach a project's form only
  when the PM adds the labels or a new form is built. Tests use copies with rebound paths.
- **Figures:** on today's inputs, none. On a project that fills the new fields, the movements are
  measured on the reference project and listed in `design.md` (§ Expected movement). Each needs the
  Head of PM's sign-off before its code is written and again before archive.
- **Interaction:** `add-multiyear-preopening-budget-phases` (not started) also touches `fill_curve.py`
  and `occupancy-ramp`. Whichever change is applied second re-checks the stable switch across years
  (design D9).
