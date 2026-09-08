## Why

Security, cleaning and landscape are priced from vendor post rates — `Fact_MasterRateCard.csv`'s
**Service** domain, e.g. Security at 17,500,000 VND per 24/24 post per month — and the pipeline then
multiplies them by a 21.5% employer social/health/unemployment insurance loading. A vendor's post
price already covers that vendor's own staff insurance, so the loading is applied twice on three of
the largest cost lines in the budget.

Three independent sources say these roles are outsourced on every real project, and have never been
Savills payroll:

- `Dim_Position.csv` — 408 positions across ME, GEN, CS, MGT, AMN, ACC and ADM. **No security,
  cleaning or landscape department exists.** The only "guard" entries are pool lifeguards.
- `Fact_StaffCost.csv` — 12,897 salary rows across all 8 projects. **None of these roles appear.**
- `Fact_MasterRateCard.csv` — only Service-domain post prices exist for the three. **No Staff-domain
  salary exists for any of them**, so there is no in-house rate to price them with even in principle.

The Savills template also files them under `ES` — *Expenses for Outsource Service*.

This was decided as **D3** in `docs/05-decisions.md` on 2026-09-08. Doing it now, first among the
decided changes, because it is the smallest and most self-contained, and because the verification
baseline that makes it measurable has just been established.

## What Changes

- `ESS1` (Security), `ESS4` (Cleaning) and `ESS16` (Landscape) are priced **without** the employer
  insurance loading, in both generated workbooks.
- `EMH2` (Savills staff cost) **keeps** the loading. It covers genuine Savills payroll and is
  unaffected.
- The two outputs stay consistent with one another: the deliverable's `ESS` rows and the analysis
  workbook's Security/Cleaning/Landscape cost lines use the same basis. Changing only one would
  recreate exactly the class of divergence the recovery audit found.
- The Remarks text on those rows states the cost basis explicitly, so a reader can see that no
  employer contribution is included and why.
- **The recorded verification baseline will move** and must be re-recorded with a stated reason,
  following `verification/README.md`. Budget totals fall.

Deliberately **not** in scope:

- **D2** (pricing all product types) and **D4** (capex reserve rate) — separate decisions, separate
  changes.
- `EMH1` (Savills' own management fee) stays blank per D1.
- The **method mismatch** between the logic spec and the code: `EXENSIVE LOGIC.xlsx` computes `ESS4`
  as `m² × unit price × 12` and `ESS16` as `monthly contract × 12`, while the code derives both from
  headcount. That is a real gap, recorded in `docs/05-decisions.md`, and is not addressed here.
- Any in-house/outsourced **toggle**. The decision was to default to outsourced now; a per-project
  vendor-selection step may follow later.

## Capabilities

### New Capabilities

- `outsourced-service-costs`: how the pipeline prices the outsourced service contracts —
  security, cleaning and landscape — and how that basis differs from in-house payroll.

### Modified Capabilities

<!-- None. openspec/specs/ holds no main specs yet; the only prior change is not archived. -->

## Impact

**Code**

- `generate_project_budget.py` — `fill_management_fund_sheet()`: the values written to the `ESS1`,
  `ESS4` and `ESS16` rows, and their Remarks. `staff_remainder` (`EMH2`) must continue to be the
  loaded cost of every *other* roster position, so the split arithmetic needs care rather than a
  blanket change to `position_annual_cost()`.
- `generate_project_output.py` — the Cost Priority / Summary figures for Security, Cleaning and
  Landscape, which today sum the roster's loaded column.

**Outputs**

- The client deliverable and the analysis workbook both fall in total cost. On the synthetic sample
  the three lines are worth roughly 2.31bn VND loaded; unloaded they are about 1.91bn.

**Verification**

- `verification/baselines/baseline.json` — `staff_cost_annual`, `total_profit_value`, `margin`,
  `markup` and the three `service_*_annual` figures are all expected to move. Re-record with a
  reason once the diff has been reviewed line by line.

**Not affected**

- No dependency changes. No production data changes. No template changes.
