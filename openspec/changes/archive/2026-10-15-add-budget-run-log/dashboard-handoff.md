# Hand-off: the run log for the `/budget/` dashboard page

For the Hub web session. The page itself is a separate release; this note only says what the pipeline leaves behind.

## Where the records are

- One JSON file per complete run, in `PM/Project/Budget_Agent/reports/run_log/` in the synced library
  (the folder is created by the first run; it does not exist until then).
- File name: `<YYYYMMDD-HHMMSS>_<project-slug>.json`. A second run in the same second gets `-2`, `-3`.
  Records are never overwritten or deleted by the pipeline.
- Written only when both workbooks were produced from the same input. A run whose analysis fails writes nothing.
- Read all `*.json` in the folder; sort by `run_id` to get the order.

## The record (schema 1)

| Field | Type | Meaning |
|---|---|---|
| `schema` | number | 1. Check it; a different number means the fields changed. |
| `run_id`, `run_time_local` | text | Run start, local time. |
| `project_name` | text | Name from the input form. |
| `project_mode` | text | `New prospect` or `Existing`. |
| `stable_operation` | true/false | The input form's "Stable Operation?" switch. |
| `budget_year` | number | Budget year of the deliverable. |
| `deliverable_file` | text | File name of the client deliverable. |
| `vat_basis` | text | `inclusive` or `exclusive` (the deliverable's VAT switch). |
| `required_total` | number | Required lines on the two fund sheets. |
| `required_filled` | number | Required lines with a figure above 0. |
| `required_zero_with_reason` | number | Zero, with a remark giving the reason. |
| `required_zero_no_reason` | number | Zero, no reason: these need a look. |
| `required_missing_from_deliverable` | number | Required line not found on the sheet. |
| `required_pct` | 0–1 | `required_filled / required_total` (the "% complete"). |
| `revenue_vnd`, `expense_vnd` | number | Fund revenue and expense, annual. |
| `fund_surplus_vnd` | number | Revenue minus expense. |
| `savills_profit_vnd` | number | Analysis "Total Profit Value" (Savills' profit). |
| `mgmt_fee_revenue_vnd` | number | Analysis "Mgmt Fee Revenue". |
| `profit_cost_basis` | text | The "Cost Basis" selected in the analysis when the profit was read. |
| `error_cells` | number | Cells showing an Excel error in the two fund sheets. |
| `status` | text | `ok`, or a list of named problems separated by `; `. |

Any figure the pipeline could not measure is `null` (blank), never 0. When `status` is not `ok`, show the figures that
exist and the status text; do not treat a `null` as a zero. The two profit fields stay separate (fund surplus is not
Savills' profit).

## Example (invented project)

```json
{
  "schema": 1,
  "run_id": "20261015-193305",
  "run_time_local": "2026-10-15 19:33:05",
  "project_name": "ZZ Sample Tower (TEST DATA - NOT A REAL PROJECT)",
  "project_mode": "New prospect",
  "stable_operation": false,
  "budget_year": 2027,
  "deliverable_file": "ZZ Sample Tower (TEST DATA - NOT A REAL PROJECT) - Sample Consulting Budget.xlsx",
  "vat_basis": "inclusive",
  "required_total": 118,
  "required_filled": 50,
  "required_zero_with_reason": 68,
  "required_zero_no_reason": 0,
  "required_missing_from_deliverable": 0,
  "required_pct": 0.423728813559322,
  "revenue_vnd": 14777200439.179483,
  "expense_vnd": 10046270997.923077,
  "fund_surplus_vnd": 4730929441.256407,
  "savills_profit_vnd": 4077421493.5,
  "mgmt_fee_revenue_vnd": 11432340000.0,
  "profit_cost_basis": "Must-Have Only",
  "error_cells": 5,
  "status": "ok"
}
```

## Choices already made for the page

Two profit figures shown separately; "% complete" = Required lines with a figure above 0; Savills colours
(`SAVILLS_BRAND_GUIDE.md`); little text, titles that state the conclusion. Deploying is done by the `[Hub]` server
session (`hub-deploy.md`), not by the dev session.

## Not in the log

Five older deliverables in `sample_output` have no matching analysis workbook, so their profit would be blank; load them
with a separate one-off script only if the page needs them.
