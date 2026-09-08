# Running the budget pipeline

How this project is actually run today, traced from the code rather than from older documentation.

> `README.md` in this folder describes a "Generation A/B" split that predates the current pipeline
> and does not mention any of the modules below. Follow this file, not that one. Correcting
> `README.md` is separate work (backlog item A5).

## Prerequisites

- **Python 3** with `openpyxl` (and `pandas` for some non-pipeline scripts). There is no dependency
  manifest and nothing is pinned — `openpyxl 3.1.5` and Python `3.14.6` are what the recorded
  baseline was produced with.
- **Microsoft Excel** for verification only. The pipeline itself does not need it.
- Run every command from `Budget_Agent/source_code/`.

## The three steps

### 1. Create the input form (first time, or to start a new project)

```bash
python build_project_input_form.py
```

Writes `Budget_Agent/reports/Project_Budget_Input.xlsx` with four sheets: `Project Info`,
`Roster Setup`, `Shift Types`, `Staffing Demand`.

> ⚠️ **This overwrites the existing input file with placeholder data.** If you already have a
> project filled in, copy it somewhere safe first. This has destroyed live input more than once.
> Skip this step entirely if you are updating a project that already exists.

### 2. Fill in the yellow cells

Open `Budget_Agent/reports/Project_Budget_Input.xlsx` and enter the project's scale on
`Project Info` — site area, floor and tower counts, product mix (GFA / NFA / units per product),
parking slots, amenities, gate count.

The **Product Mix** block (rows 14–22) carries nine product types, in the same order as the
template's own revenue rows: Apartment, Officetel, Office, Shopping Mall, Retail, Shop Apartment,
Shophouse, Villas, Nursery. Enter area for the ones the project has and leave the rest at 0 — a
product with no area is left blank in the budget rather than written as zero.

Four of the nine have no per-product rate anywhere in the comparable data (Office, Shop Apartment,
Nursery, and Officetel unless a comparable happens to carry one). Those are priced at the project's
derived Apartment rate, and the budget says so on the row.

**The form's rows may be reordered.** The generators find every field by the **label** beside it,
not by its cell address, so inserting rows or moving a section does not break the read. What you
must not do is **rename a label** — the run then stops and names the label it could not find,
rather than reading a value from the wrong row. Product rows are the one exception: a product the
form does not carry is treated as "this project has none", so a workbook filled in before a product
was added still works.

**`Pool Volume (m³)` (`B31`) drives the pool-chemicals cost.** Enter the *total water volume across
every pool* — an adult pool of 320 m³ plus a children's pool of 120 m³ is 440. This is the field the
costing spec's own formula needs; the `Pool Area (m²)` cell above it does not feed any cost, because
converting area to volume would need an average depth that is recorded nowhere.

Leave it at 0 if the developer has not supplied it. The budget then falls back to a flat figure taken
from one real project, says so on the row, and **that figure does not change with pool size** — a
large pool and a small one cost the same until this field is filled. Both client Q&A forms already
ask developers for pool tank capacity, so it is usually obtainable.

`Staffing Demand` is pre-filled with formula-driven suggestions derived from `Roster Setup`'s
ratios. Edit, add or delete rows freely; adjust the ratios in `Roster Setup` rather than
overwriting the formulas.

`Project Info!B34`/`B35` (Savills' own fee) are deliberately blank. Leave them blank until a real
contract term exists — see `docs/05-decisions.md`, D1.

### 3. Run **both** generators

```bash
python generate_project_budget.py
python generate_project_output.py
```

Order does not matter, but **both must run, every time, after any input change.**

| Command | Produces |
|---|---|
| `generate_project_budget.py` | `sample_output/{Project} - Sample Consulting Budget.xlsx` — the 22-sheet client deliverable, in Savills' own template<br>`reports/Roster_Demand_Model.xlsx` — the 5-sheet shift roster |
| `generate_project_output.py` | `reports/Project_Budget_Output.xlsx` — the 14-sheet internal analysis showing the reasoning behind every figure |

## If you run only one generator

**The two outputs will describe different projects.**

Each generator reads the input file independently and writes its own workbook. Neither reads the
other's output, and nothing reconciles them afterwards. So if you change the input and run only one:

- the workbook you regenerated reflects the new project
- the other still reflects the **previous** input, with no visible sign that it is stale
- the client deliverable and the internal analysis that supposedly explains it will disagree

This is not hypothetical. It has happened repeatedly, and at one point the two outputs on disk were
an hour apart in modification time and described different inputs. The only way to notice is to
compare timestamps by hand.

Both workbooks now price the same nine product types and report the same revenue. Until 2026-09-08
the deliverable priced Apartment alone and understated revenue against the analysis by 14.8%; that
was `docs/05-decisions.md` D2, and it is fixed.

## Verifying a run

```bash
python verification/verify.py      # everything, in one command
```

Both run the real pipeline against a synthetic project with every path redirected, so they cannot
read or write production data. See `verification/README.md`.

## What the pipeline reads

Only four reference files, plus the template and your input:

| File | Drives |
|---|---|
| `data/generation_B_verified/Fact_MasterRateCard.csv` | Capex unit prices, staff rates |
| `data/master_list_verified/Dim_Property_Residential.csv` | Comparable matching, management-fee rate |
| `data/generation_A_star_schema/Fact_OPEX.csv` | Electricity, water, diesel |
| `data/generation_A_star_schema/Fact_Capex_Rescanned.csv` | Capex line items |
| `data/generation_A_star_schema/Fact_CapexReserve.csv` | The Years 2+ Capex reserve rate, derived from 4 real projects |
| `input/template/202608 - 2027 Resi Budget Form.xlsx` | The deliverable's shape |
| `reports/Project_Budget_Input.xlsx` | Your project |

Everything else in the repository — including the real project budgets under `input/budget_planning/`
— is not read at runtime. See `docs/06-unread-datasets.md`.
