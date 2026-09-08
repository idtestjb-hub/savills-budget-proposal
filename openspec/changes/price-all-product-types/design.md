## Context

See `proposal.md` — Why. Constraints read from the code and data, not assumed.

- `generate_project_budget.py:438` writes exactly one revenue figure:
  `mgmt_fee_annual = derived_rate * project['apartment_nfa'] * 12`, into the single
  `MGMT_FUND_ROWS['mgmt_fee_revenue']` entry (template row 14, `RM.AP`). The in-code comment already
  admits the limit: *"Apartment only … other product types aren't priced here today"*.
- `PRODUCT_ROWS` (`generate_project_budget.py:64`) lists 5 products; the intake form's Product Mix
  block mirrors them.
- `PRODUCT_RATE_COLUMNS` (`master_comparables.py:72-81`) maps 4 of those 5 to `Fee_*` columns.
  `Nursery / Nhà trẻ` has no column anywhere in the source data, and `Shopping Mall` uses
  `Fee_Retail` as a stated proxy.
- The analysis workbook already prices per product and already applies an Apartment-rate fallback —
  the sample's Nursery row carries *"Apartment rate (fallback — no product-specific …)"*. The
  behaviour this change needs exists; it is the deliverable that lacks it.
- Template rows 14–24 hold eleven `RM.*` revenue lines. Nine correspond to products; `RM.PA` and
  `RM.0A` do not and are out of scope.

**The data constraint that shapes everything below.** Per-product rate coverage across 105 real
properties:

| Column | Filled | | Column | Filled |
|---|---|---|---|---|
| `Fee_Apartment` | 11 | | `Fee_Villa` | 2 |
| `Fee_Officetel` | 4 | | `Fee_Retail` | 2 |
| `Fee_Shophouse` | 8 | | `Fee_Blended` | **74** |

Four of the nine products will usually fall back. This change makes the deliverable **complete**,
not more accurate.

## Goals / Non-Goals

**Goals**

- The deliverable prices every product the project contains, closing the 1.93bn gap.
- The intake form can express nine product types.
- Both generators price products identically.
- Every fallback is visible in the output.

**Non-Goals**

- Improving rate accuracy. `Fee_Blended`'s 74 rows are the better basis and are deliberately left
  alone here.
- `RM.PA` and `RM.0A` — they need inputs that do not exist.
- Reconciling the two generators' comparable-matching basis (B3).

## Decisions

### D1 — Replace the single revenue row with a per-product mapping, keyed on the product name

`MGMT_FUND_ROWS['mgmt_fee_revenue']` becomes a `PRODUCT_REVENUE_ROWS` mapping each product name to
its template row. The writer loops over the products the project actually reports area for.

*Why:* it mirrors how `PRODUCT_ROWS` and `PRODUCT_RATE_COLUMNS` are already keyed, so a product is
added in one place rather than three. The template rows are fixed positions, verified once — the
same approach `MGMT_FUND_ROWS` already uses.

*Alternative considered:* keep writing a single combined figure into `RM.AP`. Rejected — it would
close the arithmetic gap while leaving the deliverable claiming all revenue is Apartment revenue,
which is a different kind of wrong and harder to spot.

### D2 — A product with no area is left blank, not written as zero

*Why:* the template's own convention. A blank row reads as "not applicable to this project"; a zero
reads as "this project has this product and it earns nothing". The existing `write_even_monthly`
helper already skips falsy amounts, so this follows from reusing it.

### D3 — The fallback is the Apartment rate, and it is labelled at the row

Decided with the project owner. A product with no `Fee_*` column, or with an empty one for the
matched comparables, is priced at the derived Apartment rate. The row's Remarks state that no
product-specific rate exists and that the Apartment rate was substituted.

*Why:* it reuses a real, comparable-matched rate rather than inventing one, and it is what the
analysis already does — so the two workbooks agree by construction rather than by coincidence.

*Alternatives considered:*

- **Use `Fee_Blended`** (74 rows). Better data, and it would change the rate for products that
  already have a real per-product figure — a larger movement than this change should carry.
  Recorded as the obvious follow-up.
- **Leave unpriced products blank.** Never invents anything, but re-opens the revenue gap for any
  project with villas or offices, which is the problem being fixed.

### D4 — Form fields are added for the four missing products only

Office, Retail, Shop Apartment and Villas. Not `RM.PA` or `RM.0A`.

*Why:* the form should offer exactly what the pipeline can price. Offering a Parking-area field that
produces no revenue row would mislead whoever fills it in.

### D5 — Expect the movement before running

On the synthetic sample the deliverable currently prices Apartment only:
`52,000 m² × 18,350 × 12 = 11,450,400,000`. The analysis prices three products and reports
**12,178,230,000**. After this change the deliverable should report the analysis figure, a rise of
**727,830,000 VND** — Shophouse (1,500 m² at 29,425) plus Nursery (900 m² at the fallback 18,350).

`mgmt_fee_revenue_annual` is read from the analysis workbook and should **not** move; the analysis
already prices all three. `total_profit_value` and `margin` should also hold. **If the analysis-side
figures move, something has gone wrong** — this change is meant to bring the deliverable up to the
analysis, not to change the analysis.

The sample contains no Office, Retail, Shop Apartment or Villa area, so step 2 adds fields that the
sample does not exercise. A second fixture or a temporary input variant is needed to prove they work
— see the tasks.

## Risks / Trade-offs

- **Fallback rates get read as real product rates** → every fallback row states the substitution in
  its Remarks, and a task checks the wording appears in the generated file.
- **The analysis moves when it should not** → the design states the expectation, and a task asserts
  the analysis-side baseline figures are unchanged.
- **New form fields are added but never exercised** → the synthetic sample has no area for them; a
  task runs a temporary input variant that does, and confirms those rows are priced and written.
- **A product is priced into the wrong template row** → row numbers are fixed positions in a
  template that Savills controls. A task verifies each product's figure lands in the row whose label
  matches, read back from the generated file.
- **Revenue rises while known cost errors remain** → this widens the apparent surplus, and `EMH1` is
  still blank. The output already carries that caveat; this change does not make the profit line
  trustworthy and must not be read as doing so.

## Migration Plan

No data migration. Generated output only.

Rollback is reverting the code and re-recording the baseline with a reason. Because the form gains
fields, an input workbook created after this change carries rows an older build would ignore —
harmless, but worth knowing.

## Open Questions

- Whether `Shopping Mall` should keep using `Fee_Retail` as its proxy now that `Retail` is priced in
  its own right. Both would read the same column. Deferred: it affects which comparables each row
  cites, not the arithmetic, and can be settled without changing these specs or tasks.
