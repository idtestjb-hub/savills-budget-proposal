## Status

**Explore, not approved (2026-10-20).** Written after the user's survey `docs/36-khao-sat-che-do-gia-han-ngan-sach-2026-10-20.md`
(Vietnamese). No specs, design or tasks yet: the open questions in "Decisions needed" go to the Head of PM first. Nothing
here moves a figure until a change is proposed from it and signed off. Planned after core v1 (group 10 of
`apply-head-of-pm-decisions-2026-10`), independent of `add-multiyear-preopening-budget-phases`.

## Why

The tool builds a budget proposal for a **new** property. The PM team reads it as a tool to **renew the budget of a
property Savills already runs**: take last year's approved budget, adjust it, and produce this year's. The two are
different jobs, and the second one is only partly built:

- Existing-project mode already exists (`Project Mode` on Project Info). It carries forward staff cost (EMH2, EMH3,
  EMH4) from a prior-year roster, moving figures by state law only, with a reason code on every changed line and a
  `Staff Bridge`; and common-area electricity and water (EEE.C, EEW.C) from twelve months of actual bills, repriced at
  the budget year's tariff and VAT, with a `Utility Bridge`. Both were decided by the Head of PM (docs/05, 2026-10-10
  and 2026-10-11) and back-tested on one real project.
- Every other line of an existing project is still estimated as if the building were new (ratios, real-budget ranges,
  citywide contract rates). Last year's approved figure is not read and not used as the starting point.
- Prior-year figures are typed by hand into `Prior-Year Roster` and `Prior-Year Utilities`. No step reads last year's
  approved budget file, although the real-budget scan store already reads 62 of 87 files by line code, and 97% of the
  lines with a figure on their main fund sheet match a code of the 2027 form (docs/34).
- The PM's own logic for operating buildings exists as a file, `Operation Budget logic (1).xlsx` (492 codes, "take
  the prior year / ask the user" wording, no formulas), scanned on 2026-10-04 and not used (docs/21, section D).

Cloning the core into a second tool for this job would copy the same template, verification, reference data and web
page, and would have to re-apply every Head-of-PM decision taken since; the two copies would drift. The job fits as a
second mode of the one core.

## What Changes (proposed shape, to be confirmed)

Three changes, in order, each with its own A/B and sign-off:

1. **`import-prior-year-budget`.** A reader that takes last year's approved budget workbook (the standard form or one
   of the real-budget forms the scan store already reads) and fills a new input sheet `Prior-Year Budget`: line code,
   name, approved annual amount, the twelve monthly amounts, VAT basis, source sheet and row. Lines that cannot be
   read, and lines whose code does not exist on the 2027 form, are listed on the sheet rather than dropped. New-prospect
   mode does not change by a single VND.
2. **`carry-forward-all-lines`.** For every line of the management fund and the common-area fund, one of four
   treatments, chosen per code group and recorded in `Costing_Method_Catalogue.csv` (or a new column of it):
   (a) indexed: the approved amount moved only by law, tariff, VAT (8% → 10% from 2027) or a dated index;
   (b) kept: the approved amount as it is;
   (c) re-estimated: priced as a new building, because the driver changed (area, headcount, scope);
   (d) entered: the PM's figure with one of the approved reason codes.
   The `Staff Bridge` and `Utility Bridge` become one `Budget Bridge` covering every line: approved → law/tariff/index
   → PM reason → budget year, and `verify.py` ties the bridge's total to the deliverable.
3. **`renewal-deliverable`.** The prior-year approved figure and the difference beside each line, on the internal
   analysis or on the client deliverable (the Head of PM decides which), and a Vietnamese remark that states the reason
   for every changed line.

## Decisions needed (Head of PM, before any change is proposed)

- [ ] What "review" means: (a) copy the approved figures and adjust them with a reason, or (b) regenerate from scratch
      and compare with the approved figures. (a) is the shape above; (b) is today's tool plus a comparison sheet.
- [ ] Which file is "last year's approved budget": the delivered form, the internal detail workbook, or the figure in
      the financial system; and in which format (12 of 87 real files are PDF).
- [ ] The treatment (a–d) for each code group, starting from the `Operation Budget logic` file; which groups may move
      only by law like staff cost.
- [ ] Whether the reason-code list of the staffing change (8 Vietnamese codes) applies to every line.
- [ ] Where the prior-year comparison shows: analysis only, or the client deliverable.
- [ ] Whether the 2027 budget of an existing project keeps the fill-up curve off (`Stable Operation? = Yes` as today).

## Impact (expected)

- Input form: one new sheet `Prior-Year Budget`; `Project Mode` unchanged. `add_existing_project_sheets.py` learns the
  new sheet.
- Code: a new reader module built from the scan store's readers (`Savills-local\budget-test\scan-2026-10-07\build_final.py`,
  outside the repo today, no tests), a treatment table per code, a bridge builder generalising `existing_staffing.py`
  and `existing_utilities.py`, verification checks for the bridge.
- Not touched: every New-prospect figure; the 2027 template; the real-budget ranges and service-level tables.
- Risks: input formats vary (old-form `ESA*` codes, PDFs, files whose fund sheet does not reconcile); the Head of PM's
  "law only" rule was decided for staff cost and may not extend to contracts; the user has not yet confirmed with the
  PM team which of (a) and (b) they expect.

## Capabilities

### New Capabilities
- `budget-renewal-mode` (name provisional): how an operating project's budget for the next year is derived from its
  approved prior-year budget.

### Modified Capabilities
- `existing-project-staffing`, `existing-project-utilities` (their bridges fold into the budget bridge), `input-workbook-reading`
  (the new sheet), `budget-workflow-verification` (the bridge tie). None modified until the change is proposed.
