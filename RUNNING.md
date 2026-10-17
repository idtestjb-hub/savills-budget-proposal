# Running the budget pipeline

How this project is actually run today, traced from the code rather than from older documentation.

> `README.md` in this folder is the module map: which modules the pipeline runs, which scripts
> prepared its reference data, and which are history. This file is how to run it.

## Prerequisites

- **Python 3.14** (baselines recorded on 3.14.6) with the pinned packages in `requirements.txt`
  (`openpyxl`, plus `pywin32` for verification). `requirements-studies.txt` adds `pandas`/`numpy`
  for the one-off ETL and study scripts; the pipeline does not need them.
- **Microsoft Excel** for verification only. The pipeline itself does not need it.
- Run every command from `Budget_Agent/source_code/`.

## The three steps

### 1. Create the input form (first time, or to start a new project)

```bash
python build_project_input_form.py
```

Writes `Budget_Agent/reports/Project_Budget_Input.xlsx` with four sheets: `Project Info`,
`Roster Setup`, `Shift Types`, `Staffing Demand`.

> ⚠️ **It refuses to run if `Project_Budget_Input.xlsx` already exists**, so a filled-in project
> cannot be replaced by accident (this had destroyed live input more than once). It stops with a
> message naming the file and leaves it untouched. Skip this step entirely if you are updating a
> project that already exists.
>
> To start a new project in that place anyway, run `python build_project_input_form.py --force`.
> The existing file is first copied beside itself as
> `Project_Budget_Input_PRE_FORCE_<date_time>.xlsx`, and nothing is replaced if that copy fails.

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

**`Budget Start Month`** (`BUDGET HORIZON` section, MM/YYYY) is the first of the twelve months the budget covers. Blank, or a form without the field, means January 2027. Both fund sheets and the summary show the period, and the date-dependent rules (Existing-mode tariffs and paid holidays) use the month they are applied to. Text that is not a month stops the run and names the field. The occupancy fill-up is not dated: its month 1 is the first month of the period.

**`Capex Drop-to-Reserve Year`** (`BUDGET HORIZON` section, near the bottom) controls the two
internal analysis sheets' (`Owner Operating Position`, `Savills Fee Position`) 4-year Capex
projection — nothing on the client deliverable. Left blank, it defaults to Year 2: every year before
it repeats the project's full initial equipment purchase, and it and every year after drop to a
derived ongoing reserve contribution instead. That default is evidenced, not arbitrary (3 of the 4
real reference projects behind it drop at Year 2), but one of the four — Green Skyline — genuinely
repeats a full purchase in Year 2 and drops in Year 3, which is worth ~290M VND on a project that
shape. Enter `3` or `4` here only when this project's own equipment replacement cycle is known to be
longer than the default. See `docs/05-decisions.md`, D4.

### 2b. A project Savills already manages: Existing-project mode

For a building Savills already runs, the staff lines start from last year's **approved** budget instead of
being estimated (change `carry-forward-staffing`). Leave `Project Mode` at `New prospect` for a new building:
nothing below applies and no figure changes.

1. On `Project Info`, at the bottom (`EXISTING PROJECT` section): set `Project Mode` to `Existing project`,
   pick the `Minimum Wage Region` of the site (blank = Region I) and type the `Prior Budget Year` (e.g. 2026).
2. On the sheet `Prior-Year Roster`, copy from the approved budget. Fill one of the two baselines; both is fine.
   - **Roster:** one row per position, with headcount and monthly gross salary per head (from that budget's A1
     sheet). Type a change in `New Headcount` / `New Monthly Gross`, with a `Reason Code` from the dropdown.
   - **Staff Lines:** the approved EMH2, EMH3 and EMH4 amounts (VND/year). Use this alone when the approved
     budget has no per-position table. `Budget-Year Override` is a whole-line change and needs a reason code.
   - **Holiday and Night Duty:** per code, the staff on duty (normal nights, holiday nights, day shift on
     holidays) and the gross they are paid on, from last year's holiday sheet. EMH3 is priced from this.
   - **Actual Headcount (optional):** C&B or timesheet counts, shown beside the baseline, never used in a figure.
3. On `Staffing Demand`, an in-house position whose code is not in the roster is a new position: give it a
   `Reason Code` in the last two columns.

The tool then recomputes the year under state law only: the regional minimum wage, the insurance base and
caps, the employer rates (all from `data/generation_B_verified/Ref_LaborLawParams.csv`, with dates and legal
sources), and the paid-holiday calendar (24 November counts from 2026). It adds no percentage of its own. Every
changed line gets "Điều chỉnh so với NS <năm>: …" in its remark, and the analysis workbook gets a `Staff Bridge`
sheet. **`run.py` fails if a changed line has no reason, and names it.** Fix the reason and run again.

On the deliverable, EMH2, EMH3 and EMH4 are always formulas into their detail sheets (`A1`, `A1.1`, `A5`). An
approved amount carried forward shows there as its own row ("… đã duyệt NS <năm> mang sang"), and an override
as a row "Điều chỉnh của PM" with its reason, so each line equals its detail sheet.

A workbook filled in before this change has none of these fields. Add them to a dated copy:

```bash
python add_existing_project_sheets.py
```

The original stays untouched. The copy is written beside it as `Project_Budget_Input_EXISTING_<date>.xlsx`;
check it, then replace the original with it yourself.

### 2c. A building already in operation: its actual figures

For a building that is already running, the PM can enter what is known instead of letting the tool estimate it
(change `use-operating-project-actuals`). Every field is optional: leave them blank and the run is exactly the
run without them.

| Field on `Project Info` | What it does |
|---|---|
| `Stable Operation?` = Yes | 100% occupancy in all 12 months on every occupancy-scaled line, and `RM.0A` (developer top-up) = 0 |
| `Actual Rate (VND/m²/month)` and `Rate VAT Basis`, two columns beside the `Product` header of Product Mix | The entered rate prices that product in both workbooks, in place of the comparables. `Rate VAT Basis` is `incl. VAT` or `excl. VAT`; a basis other than the deliverable's is stated in the remark, never converted |
| `Actual Car Parking Revenue (VND/month)`, `Actual Motorbike Parking Revenue (VND/month)` | `RP2` (car) and `RP1` (motorbike) = the figure x 12, not slots x rate x occupancy. 0 is allowed and says so in the remark |
| `COLLECT ON BEHALF (THU HỘ CHI HỘ)` block: header row `Collect-on-behalf product` / `Water (VND/month)` / `Electricity (VND/month)`, then one row `Thu hộ chi hộ: <product>` per product | Water goes to `RO3.<x>`, electricity to `RO4.<x>`, each x 12, and the same amounts to `EEW.A` / `EEE.A`, so the surplus does not move. They stay out of `2.2 Common area Fund` |

Rules the run enforces, each stopping with a message that names the field:
- Parking revenue and collect-on-behalf amounts are used only when `Stable Operation?` is Yes.
- An entered rate needs its VAT basis.
- Collect-on-behalf rows exist only for Apartment, Officetel, Office, Shopping Mall, Retail and Shophouse.
  An amount for Villas, Shop Apartment or Nursery stops the run.
- In Existing-project mode, `EEE.C` and `EEW.C` still come from the prior-year actuals: the switch does not change them.

`run.py` prints an `Operating-project inputs:` block listing every field as filled, blank or "not on the form". A
misspelt label shows up there as "not on the form" instead of being ignored silently.

A form built before this change has none of these labels. A form built now has them, blank. To add them to an
older form, copy the labels exactly as above into column A of `Project Info`, below the last used row (the two rate
columns go in the `Product` header row of Product Mix). `verification/fixtures/build_operating_fixture.py` does the
same on the test sample and can be used as the model.

Each choice made for this change sits in one named place in `operating_inputs.py` (its docstring lists them):
- 100% stable occupancy: `fill_curve.STABLE_FILL`;
- the switch being required: `require_stable()`;
- which products have collect-on-behalf rows: `COB_SUFFIX`;
- which expense line pairs with each revenue line: `paired_with` in `Costing_Method_Catalogue.csv`;
- how a VAT-basis mismatch is shown: `DELIVERABLE_VAT_BASIS` and `vat_mismatch_vi()`.

### 3. Run the pipeline

**The easy way — the launcher.** Fill the yellow cells, **save and close** the workbook, then
double-click `Run Budget Agent.cmd` in `C:\Users\<you>\Savills-local\launchers\budget-agent-main\`. It
finds Python, runs both generators, and leaves the window open so you can read the result (press a
key to close).

> The launcher lives **outside the SharePoint library on purpose**: the tenant blocks syncing `.cmd`
> files, so a copy placed in `Budget_Agent\reports\` never uploads and shows a sync error. It is
> local to one PC and uses absolute paths: on another PC, copy the folder and fix the `cd /d` line
> to that PC's library path.

> The green box on `Project Info` is only a reminder, not a working button. This workbook lives on
> SharePoint, and Excel turns any cell hyperlink into a web URL — a link to the local `.cmd` just
> opens a 404. A real one-click **button** needs a VBA macro in a macro-enabled (`.xlsm`) copy:
> Developer tab → Insert → Button → assign this macro, then Save As `.xlsm` and point
> `generate_project_budget.py`'s `INPUT_PATH` at the `.xlsm`:
> ```vba
> Sub RunBudgetAgent()
>     Dim p As String
>     p = Environ$("USERPROFILE") & "\Savills-local\launchers\budget-agent-main\Run Budget Agent.cmd"
>     If Dir(p) = "" Then MsgBox "Not found: " & p, vbExclamation: Exit Sub
>     CreateObject("WScript.Shell").Run """" & p & """", 1, False
> End Sub
> ```

**The command-line way** — from `Budget_Agent/source_code/`:

```bash
python run.py
```

One command. It runs both generators in order. `Run Budget Agent.cmd` is just a wrapper around this
that finds Python, changes to the right folder, and pauses at the end.

Before doing anything it checks the input file exists and is not locked by Excel — the most common
cause of a half-finished run. If the deliverable is written and the analysis then fails, it reports
that as a **failure** naming the consequence, not as a partial success. When both succeed it re-opens
them and confirms they name the same project, which is the actual symptom of the drift described
below.

The two generators still work on their own if you need them separately:

```bash
python generate_project_budget.py
python generate_project_output.py
```

Order does not matter, but **both must run, every time, after any input change** — which is exactly
why `run.py` exists.

| Command | Produces |
|---|---|
| `generate_project_budget.py` | `sample_output/{Project} - Sample Consulting Budget.xlsx` — the 25-sheet client deliverable (the form's 24 sheets plus `Comparison`), in Savills' own template<br>`reports/Roster_Demand_Model.xlsx` — the 5-sheet shift roster |
| `generate_project_output.py` | `reports/Project_Budget_Output.xlsx` — the 14-sheet internal analysis showing the reasoning behind every figure |

### The run log (change `add-budget-run-log`)

At the end of every complete `python run.py`, the tool writes **one small file per run** into
`Budget_Agent/reports/run_log/` (named `<yyyymmdd-hhmmss>_<project>.json`; a file is never edited afterwards, so
several PCs never write to the same file). It takes about 15 to 40 seconds: Excel opens a read-only copy of the deliverable
and of the analysis, recalculates, and reads the figures. The output workbooks themselves are not opened or changed.

What a record holds (fields in `run_log.py`, rules in spec `budget-run-log`):
- the project name, run time, mode, budget year, deliverable file name and VAT basis;
- **completeness:** the Required lines of the AI Guideline on `2. Budget-Management Fund` and `2.2 Common area Fund`
  (118 lines on the standard form, a code on both sheets counts once per sheet): how many carry a figure above 0, how
  many are zero with a stated reason (not complete), how many are zero with no reason, and `required_pct` = filled / total;
- the Management Fund's revenue, expense and surplus (VND per year, in the deliverable's VAT basis);
- the Savills profit: the analysis workbook's *Total Profit Value* with the cost basis the PM selected and the
  management fee revenue it is measured on. It is a separate number from the fund surplus;
- `error_cells` (formula errors on the deliverable) and `status`.

A blank (`null`) figure means "could not be read", never zero; `status` says why (`excel_unavailable`,
`missing_label:...`, `missing_row:...`). A problem with the log prints one `Run log:` line and never changes the run.
`verify.py` checks the log on the synthetic project in a temporary folder.

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

Six reference files, plus the template and your input. This list comes from tracing every file a run opens on the standard sample (2026-10-05):

| File | Drives |
|---|---|
| `data/master_list_verified/Costing_Method_Catalogue.csv` | The costing method and the remark rules for each budget code |
| `data/master_list_verified/Dim_Property_Residential.csv` | Comparable matching, management-fee rate |
| `data/master_list_verified/Fact_ProjectLocation.csv` | Project locations for ranking comparables |
| `data/generation_A_star_schema/Fact_OPEX.csv` | Electricity, water, diesel |
| `data/generation_A_star_schema/Fact_Capex_Rescanned.csv` | Capex line items |
| `data/generation_A_star_schema/Fact_CapexReserve.csv` | The Years 2+ Capex reserve rate, derived from 4 real projects |
| `input/template/2027 Resi Budget Form (IT team).xlsx` | The deliverable's shape |
| `reports/Project_Budget_Input.xlsx` | Your project |

`data/generation_B_verified/Ref_LaborLawParams.csv` (the labour-law table) is read on every run for the
analysis workbook's payroll caps and rates, and drives the staff lines in Existing-project mode.

One more file is read only on a fallback path: `data/generation_B_verified/Fact_MasterRateCard.csv`
supplies a flat Capex price list when no nearest-project item list can be built
(`load_capex_items()` in `generate_project_output.py`). A normal run does not open it.

Everything else in the repository — including the real project budgets under `input/budget_planning/`
— is not read at runtime. See `docs/06-unread-datasets.md`.
