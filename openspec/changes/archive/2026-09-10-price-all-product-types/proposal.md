## Why

The client deliverable prices **Apartment only**. The internal analysis workbook prices every
product the intake form carries. For the same project they therefore report different revenue —
**15,020,400,000 vs 13,089,600,000**, a gap of **1,930,800,000 VND (14.8%)**.

The deliverable is the document that goes to the client, and it is the one that is wrong. It
understates revenue by roughly 15%, which makes the project look less viable than the analysis
behind it says it is. This is finding **X-01 / R-B02**, one of the two items the recovery audit
rated **STOP** — unsafe to put in front of a client.

The template has always been able to carry this: rows 14–24 of the Management Fund sheet hold
eleven per-product management-fee lines, ten of them blank on every budget this pipeline has ever
produced.

Decided as **D2** in `docs/05-decisions.md`. Doing it now because it is the largest remaining
client-facing error, and the verification baseline that makes the movement measurable is in place.

## What Changes

**Step 1 — the deliverable prices every product the form carries.** This alone closes the 1.93bn
gap. `RM.AP` stops being the only revenue row written; each product's NFA is priced at its own
derived rate, into its own template row.

**Step 2 — the intake form grows from 5 products to 9.** Office, Retail, Shop Apartment and Villas
are added, so a project with those areas can be quoted at all. Each maps to its own template row.

| Template row | Product | In the form today | After |
|---|---|---|---|
| `RM.AP` | Apartment | yes | yes |
| `RM.OT` | Officetel | yes | yes |
| `RM.SH` | Shophouse | yes | yes |
| `RM.SM` | Shopping Mall | yes | yes |
| `RM.KG` | Kindergarten / Nhà trẻ | yes (as "Nursery") | yes |
| `RM.OF` | Office | no | **added** |
| `RM.RE` | Retail | no | **added** |
| `RM.SA` | Shop Apartment | no | **added** |
| `RM.VI` | Villas | no | **added** |

- **Rate fallback**, decided: a product with no real per-product rate in the comparable data uses
  the derived **Apartment** rate, with the substitution stated in the row's Remarks. This is what
  the analysis already does for Nursery. It never invents a rate; it reuses a real one and says so.
- Both generators price products **identically**, so the two workbooks agree.
- **The recorded verification baseline will move upward** and must be re-recorded with a stated
  reason.

Deliberately **not** in scope:

- **`RM.PA`** (management fee on parking areas) and **`RM.0A`** (developer pays on unsold units).
  Both need inputs that do not exist — parking area in m², and the occupancy fill-up curve. `RM.0A`
  belongs with **B5**.
- **Changing the rate source.** `Fee_Blended` covers 74 of 105 rows against `Fee_Apartment`'s 11,
  and is the better basis — but switching would move every product's rate including ones that
  already have a real per-product figure. Separate decision.
- **Reconciling the comparable-matching basis.** The two generators match on different NFA bases
  today (Apartment NFA in one path, Total NFA in the other). Pricing more products makes that more
  visible; fixing it is **B3**.
- `EMH1` stays blank per **D1**.

## Capabilities

### New Capabilities

- `product-revenue-pricing`: how the pipeline prices management-fee revenue for each product type
  a project contains, and what it does when no real per-product rate exists.

### Modified Capabilities

<!-- None. The two existing specs (budget-workflow-verification, outsourced-service-costs) are
     unaffected: this change alters what revenue is priced, not how verification works or how
     outsourced service costs are computed. -->

## Impact

**Code**

- `build_project_input_form.py` — the Product Mix block grows from 5 rows to 9.
- `generate_project_budget.py` — `PRODUCT_ROWS` extends to 9; `MGMT_FUND_ROWS` gains a per-product
  revenue mapping across template rows 14–24, replacing the single `mgmt_fee_revenue` entry.
- `master_comparables.py` — `PRODUCT_RATE_COLUMNS` gains `Villas → Fee_Villa` and
  `Retail → Fee_Retail`; Office and Shop Apartment have no column and take the fallback.
- `generate_project_output.py` — prices the same 9 products, so the two workbooks agree.

**A constraint worth stating plainly:** the per-product rate data is thin. Across 105 real
properties, `Fee_Apartment` is filled on 11, `Fee_Officetel` on 4, `Fee_Shophouse` on 8,
`Fee_Villa` on 2 and `Fee_Retail` on 2. Four of the nine products will usually fall back to the
Apartment rate. This change makes the deliverable **complete**, not more accurate — every fallback
is disclosed in the output rather than hidden.

**Outputs**

- Deliverable revenue rises for any project with non-Apartment area; the sample gains Shophouse and
  Nursery revenue it was not previously showing.
- `mgmt_fee_revenue_annual`, `total_profit_value`, `margin` and `markup` all move.

**Verification**

- `verification/baselines/baseline.json` re-recorded with a reason after the diff is reviewed.

**Not affected**

- No dependency changes. No production data changes. No template changes — the rows already exist.
