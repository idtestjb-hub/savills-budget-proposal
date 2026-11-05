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

`Roster Setup` sizes security and cleaning from the total fee-paying NFA (every product):
**`Security: 24h Posts per 10,000 m² Fee-paying NFA`** (default 1.7) gives the 24-hour posts, never fewer than the
gate posts plus one CCTV post, and the posts above that floor are patrol on all three shifts;
**`Cleaning: m² Fee-paying NFA per Cleaning Staff`** (default 3,300) gives the cleaning people on duty per day,
supervisors included. Both defaults are medians of real Savills projects (`data/service_levels`). Blank or 0 means
the default; the old open-space ratio labels of earlier forms are no longer read.

**Savills' own fee (`EMH1`)** sits in the section `SAVILLS' MANAGEMENT FEE (EMH1)`: `Fixed Monthly Fee (VND, excl.
VAT)` (each month's VAT is added) or `% of Collected Management Fee` (of the full annual fee at 100% occupancy, no VAT
added). Fill one at most: both filled stops the run; both blank leaves `EMH1` at 0 with a caveat. Leave them blank
until a real contract term exists — see `docs/05-decisions.md`, D1 and group 7.

**`Contingency Rate (EM#, ES#, EE#)`** (`BUDGET HORIZON` section) is the rate of the three contingency lines on both
fund sheets, written as live formulas. Blank means 2%; 0 is allowed; text, a negative rate or one above 10% stops the
run.

**Building insurance `ESI2`**: `ESI2 Annual Premium (USD)` (blank = 1,000 USD, 0 = nothing) × `USD Exchange Rate (VND
per USD)` (blank = 26,190) plus 10% insurance VAT, spread over the twelve months.

**Asset insurance `ESI1`** (optional section `ASSET INSURANCE (ESI1)`, below every other section): `ESI1 Insured
Asset Value (VND)` × `ESI1 Premium Rate` (blank = 0.05%) plus 10% insurance VAT over twelve months. A blank value
leaves `ESI1` at 0 and the remark names the field; 0 is the PM's 0; a value that is not a number or a rate above 1%
stops the run.

**`Budget Start Month`** (`BUDGET HORIZON` section, MM/YYYY) is the first of the twelve months the budget covers. Blank, or a form without the field, means January 2027. Both fund sheets and the summary show the period, and the date-dependent rules (Existing-mode tariffs and paid holidays) use the month they are applied to. Text that is not a month stops the run and names the field. The occupancy fill-up is not dated: its month 1 is the first month of the period.

**`Water Customer Group`** (`Project Info`, a dropdown) is the customer group on the building's water bill: `Kinh doanh dịch vụ` or `Hành chính sự nghiệp`. Blank, or a form without the field, means the business group, and the water remark says so. A new prospect's water is priced from the dated table `data/generation_B_verified/Ref_UtilityTariffs.csv` (SAWACO base price plus 5% VAT, the 30% drainage charge, and the general VAT of each budget month); diesel is priced from the same table (listed pump price, VAT split out, then the VAT of each month). The SAWACO prices are Ho Chi Minh City ones: a project outside it gets them with a remark asking to check the local water bill. An Existing project chooses its water category on the `Prior-Year Utilities` sheet (household top tier stays the default). Other lines priced before VAT get each month's VAT added (electricity `EEE.C` of a new prospect, `ESC12`, `ESM25`, `ESS9`) when the financial model includes VAT; `ESS9` uses QĐ 65/2026/QĐ-UBND (1,087 VND/kg). A new price or VAT decision is a new row in the table, not a code change.

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
| `Car Parking Price (VND/vehicle/month)`, `Motorbike Parking Price (VND/vehicle/month)` | Change `price-fee-and-parking-from-portfolio`: the monthly price per vehicle, incl. VAT, for a new or an operating building (no stable switch needed). Blank or 0 = the portfolio price: the median first-vehicle list price of the master list's residential projects (`parking_prices.py`: the project itself left out by name, IQR outliers dropped, at least 10 prices; as quoted, no CPI), else the former constants 1,100,000 / 110,000. A recorded revenue above still ranks first. The analysis's `Additional Revenue` lists every master-list row read with its parsed price or the reason it was not used |
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

### 2d. Budget Review of an operating project: start from last year's approved budget

For a building Savills already runs, the PM team's job is a **review**: read last year's approved budget, produce
this year's, and see line by line how the new figure compares with the approved one (change
`add-budget-renewal-mode`, MVP of 2026-10-20). One command does the whole thing, in a work folder of its own:

```bash
python review.py "<last year's approved budget>.xlsx" [--input form.xlsx] [--facts facts.json] [--workdir DIR]
```

What it does, in order:
1. **Import** (`review_import.py`): reads the approved workbook on the Savills form (2026 or 2027 layout) by content,
   not by fixed addresses: both fund sheets, every leaf line of sections R and E with the year column as the approved
   figure, the twelve months, the VAT basis, the source row; and the scale from `0. Info` (NFA and units per product,
   parking bays, the applied fee rate per product). It then writes a filled form in Existing-project mode: `Project
   Mode`, `Prior Budget Year`, `Budget Start Month` (the file's first month plus twelve), the `STAFF LINES` approved
   EMH2/EMH3/EMH4, the `UTILITY LINES` approved EEE.C/EEW.C (no monthly bills, so the utilities module starts from the
   approved amount and says so), the fee rate per product and its VAT basis, `Stable Operation?` = Yes, parking revenue
   (RP1/RP2 ÷ 12) and collect-on-behalf water/electricity (RO3.x/RO4.x ÷ 12), and a new sheet **`Prior-Year Budget`**
   with every line read plus an `IMPORT NOTES` block. Facts the file does not carry (towers, floors, gates, pools,
   district, site and garden area) are **never invented**: numeric ones are written as 0, text ones left blank, all of
   them listed in the notes, unless `--facts` (a JSON of `Project Info` label → value, with an optional `_sources`
   map) supplies them. `City / Province` is one of them, and the water tariff stops without it, naming the field: give
   it in `--facts`. With `--input`, a dated copy of your form is used and the original is not changed.
2. **Generate**: both generators run through `verification/isolation.py`, so the live `reports/` and `sample_output/`
   are never written. Staff and utilities move by law and tariff as in 2b; everything else is estimated as for a new
   building.
3. **Review sheet**: Excel recalculates a copy of the deliverable, and a sheet **`Review`** is added at the end of the
   work folder's `Project_Budget_Output.xlsx`: a summary (revenue, expense, surplus: approved vs tool), then per fund
   sheet and section one row per code with the approved figure as read, the VAT factor, the approved figure on the
   deliverable's basis, the tool's figure, the difference, and **how the tool got its figure**: `Mang sang theo luật`
   (EMH2–4), `Mang sang theo biểu giá` (EEE.C, EEW.C), `PM nhập` (lines fed by an operating input the import filled),
   `Ước lượng: <method>`, `Chưa có phương pháp` (the file has a figure, the tool has no method; the tool column shows 0,
   the approved figure is never copied), `Công cụ ra 0`, `Chỉ công cụ`. Codes the 2027 form does not carry are listed
   under their own heading and stay in the approved totals. The command prints and writes `review_summary.md` /
   `.json`, and exits 1 when either of two ties fails: tool column R/E = the deliverable's own R/E rows; approved
   column R/E = the source file's own R/E rows.

Not in this first version, said plainly: the per-position roster from the file's staff sheet, the twelve monthly
bills, and carry-forward rules for lines other than staff and utilities. PDF and xlsb files are refused with a message;
Excel is needed for step 3 (without it the three workbooks are still written and the command says why it stopped).

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
| `generate_project_output.py` | `reports/Project_Budget_Output.xlsx` — the 15-sheet internal analysis showing the reasoning behind every figure (the last sheet, `Service Levels`, is display only) |

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

### The Service Levels sheet (change `add-service-level-table`)

The internal analysis ends with a sheet **`Service Levels`**: are the cleaning and security crews the tool has just
costed lean, standard or generous next to real Savills projects? Display only: it changes no figure, and nothing
else reads it.

- **Two measures.** Cleaning: m² of total fee-paying NFA per cleaning person on duty per day (supervisors included).
  Security: 24-hour-equivalent posts per 10,000 m² of fee-paying NFA, where a `24H` shift row counts 24 hours and
  any other shift row 8 hours (the three rows of a gate make one post). The people are Staffing Demand's
  `Staff On Duty / Day`; the roster's Staff Count (rest-day cover added) is shown beside it for the tie.
- **Fixed thresholds** in `data/service_levels/Ref_ServiceLevelThresholds.csv`: cleaning below 2,500 = Nâng cao,
  2,500 to below 4,000 = Tiêu chuẩn, 4,000 or more = Cơ bản (bounds 1,000–8,000); security below 1.5 = Cơ bản, 1.5 to
  below 3.0 = Tiêu chuẩn, 3.0 or more = Nâng cao (bounds 0.5–8). A value on a cut-off takes the higher-numbered band;
  a value outside the bounds, a missing NFA or a zero headcount gives `chưa phân loại` with the reason; a value within
  10% of a cut-off carries `sát ngưỡng`. Edit the CSV to change a threshold, and record the new approval date in it;
  no code changes. Landscape has no threshold (the store has no green area).
- **Real projects** in `data/service_levels/Ref_ServiceLevelProjects.csv`: one anonymous row per project (48 on
  2026-10-18, 45 with NFA; readers v8) with both measures, their level, and whether the headcount was read from the budget's own
  A2/A3 form (`form`) or inferred from its cost (`chi phí`). The sheet's percentile counts only form-read, classified
  projects, with the project itself left out (by name key or an NFA within 0.5%); the inferred count is shown apart.
- **Rebuilding the table** (only after a new scan of `input/budget_planning/` and a re-run of the level-of-service
  readers in `Savills-local\budget-agent\level-of-service\`: `extract_fix_v8.py` → `levels4_v8.py` → `levels5_v8.py`,
  see that folder's README; v8 of 2026-10-18 reads security forms whose shift column is text and cleaning forms
  without an hours column):

  ```bash
  python build_service_levels.py --store "C:\Users\CDangQuang\Savills-local\budget-agent\scan-2026-10-07\final_v2\budget_scan_v2.sqlite" --levels "C:\Users\CDangQuang\Savills-local\budget-agent\level-of-service\level_assignment_v8.csv"
  ```

  It writes the table beside the thresholds, prints the counts per level, and writes the name-to-id map and the
  names list next to the store (never into the repository). It refuses to write if a project or file name would
  land in the table. `verify.py` section 5h checks the sheet against the roster and both tables; the name scan
  needs the names list from the store folder and is noted as skipped on a PC without it.

## Lines priced from real Savills budgets

Seven Required lines have no price in the input or the costing catalogue. They are priced from what Savills-managed
projects actually budget (change `use-real-budget-ranges`): `EMB4` operation audit, `ESS12` pest control, `ESC5` Tết
decoration, `ESS7` façade cleaning (only with at least one tower), `ESS23` outsourced pool staff (only with a pool and
no in-house pool staff on A1), and `ESC1` events and `ESC2` fire drill as stand-ins for count x price. Since change
`price-fee-and-parking-from-portfolio` the same file also carries `RM.AP`, the apartment management-fee **rate** of each
real budget: (RM.AP + RM.0A, the developer's share on units not yet handed over) per month ÷ apartment NFA, excluding
VAT, column `basis = apartment_nfa`. Its range (same leave-one-out, IQR and 10-project floor) gives the applied Apartment
rate: median × (1 + VAT of the first budget month) on an inclusive deliverable, decided in
`master_comparables.resolve_product_rates()` between the PM's entered rate and the two-comparable average; the two
nearest comparables stay on the Comparison sheets and drive the benchmark verdict. Under 10 projects, or without the
file, the Apartment rate comes from the comparables as before.

- **The data** is `data/real_budget_ranges/Ref_RealBudgetValues.csv`: one anonymous row per project and code, VND per
  m² of fee-paying NFA per month, excluding VAT, at budget-year and 2027 prices (CPI from
  `data/generation_B_verified/Ref_CPI_VN.csv`). Its `README.txt` gives the build date and the counts.
- **At run time** each code's range leaves out the project itself (same name, also without a trailing "(...)", or
  NFA within 0.5%), then values outside P25 - 1.5 x IQR .. P75 + 1.5 x IQR. With at least 10 projects left, the line
  = median x fee-paying NFA x 12, with each budget month's VAT added (none under KHOÁN), spread evenly. Otherwise the
  line stays at 0 and its remark says why. A line another source already priced is never replaced.
- **The analysis** shows each range on `Real-Budget Ranges`: ids used and left out, P25 / median / P75, CPI factors
  and sources, the figure written, and the cross-check ranges of `ESI1`, `EMH1` and `EMH3` (never priced from them).
  `verify.py` ties it to the deliverable on the standard and Existing samples.
- **Rebuilding the data** (only after a new scan of `input/budget_planning/`, or a CPI change):

  ```bash
  python build_real_budget_ranges.py --store "C:\Users\CDangQuang\Savills-local\budget-agent\scan-2026-10-07\final_v4" --out "..\data\real_budget_ranges" --nfa-table "C:\Users\CDangQuang\Savills-local\budget-agent\scan-2026-10-07\nfa_per_file.csv"
  ```

  It writes the name-to-id map and the names list next to the store, never into the repository, and refuses to write
  if a project or file name would land in the data. Without the values file every line falls back to 0 with its
  reason and the run still completes. `--master` (default: the residential master list) is the second NFA source.

- **How the store is built** (outside the repository, in `Savills-local\budget-agent\scan-2026-10-07`; since change
  `widen-real-budget-store`, store `final_v4`):
  1. `SCAN_VERSION=v4 python v2\scan_budgets_v2.py --all` (about 5-9 minutes; `BUDGET_ROWS_SRC` = this `source_code`
     folder) writes `tables_v4`.
  2. `python v2\scan_other_forms.py --out tables_v4` reads the files listed in `code_maps\other_forms.csv` (four
     departmental-form budgets, the 2022 file with its own code column, the budget with item names only) through the
     reviewed maps `code_maps\departmental.csv`, `q2_2022.csv`, `no_code_budget.csv`. A map whose first line has no
     `# approved_on=` date is not read; a line with an amount and no map row stops the file (`other_refused.csv`).
  3. `SCAN_VERSION=v4 python v2\build_final_v2.py` merges them and writes `final_v4`; `python v2\compare_v4.py`
     lists everything that moved against `final_v3`.
  4. `nfa_per_file.csv` holds the reviewed fee-paying NFA of the files whose own sheet has none (cell, rate, approval
     date). Its row wins over the file's profile; the master list is the fallback, and either one must pass the fee
     check (revenue `RM.*` per month ÷ NFA within 15% of the rate written in the file or the master list; for mixed
     products the reference is the area-weighted rate of the file).
  5. Overlay first (`--out` a scratch folder), measure with `verify.py` and the M3 runs, get the sign-off, then copy
     `Ref_RealBudgetValues.csv` and `README.txt` into `data\real_budget_ranges`, the four store CSVs (`dim_file`,
     `file_profile`, `project_map`, `reconcile`) into `input\budget_planning\_kho_quet`, and re-record the baselines.
  6. The web library reads `final_v4` (`BUDGET_WEB_LIBRARY_STORE`, default `final_v4`). Files read through a map tie in
     the store but stay greyed in the Review tab ("Form riêng"), because Review does not read those forms.

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

## Site packages: one click-to-run folder per managed site

For sites with no office network and no Python (change `site-standalone-package`). Build on the office PC, outside
SharePoint, then send the zip; the site extracts it to `C:\BudgetAgent\` and double-clicks a launcher. Excel is
needed at the site.

```bash
python build_site_runtime.py --out C:\ZWork\site-runtime
python build_site_package.py --site "Project name" --prior "<approved budget .xlsx>" --library-id <store id> --city "Hồ Chí Minh" --runtime C:\ZWork\site-runtime --out C:\ZWork\site-packages --check --zip
```

The runtime is a pruned copy of this PC's Python 3.14 plus only the packages the generators and the web import
(pinned versions checked, nothing downloaded). The package holds `python\`, `app\` (this folder without tests, legacy,
OpenSpec, docs and the two build scripts; `data\`; the input form; the 2027 template), `site\` (`site.json` + the
approved budget), `runs\`, `tmp\`, `Chay Budget Agent.cmd` (local web, three tabs, see `webapp/README.md`) and
`HUONG-DAN.txt`.
`--check` imports the modules with the packaged Python, reads the approved budget, and scans the package for the build
PC's user name, machine name, paths and AI-tool names. The scan store and `input\budget_planning` never go into a package.

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

`data/real_budget_ranges/Ref_RealBudgetValues.csv` and `data/generation_B_verified/Ref_CPI_VN.csv` are read on every
run for the seven lines priced from real Savills budgets and the analysis sheet `Real-Budget Ranges`.

`data/service_levels/Ref_ServiceLevelThresholds.csv` and `Ref_ServiceLevelProjects.csv` are read on every run for
the analysis workbook's `Service Levels` sheet only (display; no figure depends on them). A missing file gives a
note on that sheet and the run still completes.

One more file is read only on a fallback path: `data/generation_B_verified/Fact_MasterRateCard.csv`
supplies a flat Capex price list when no nearest-project item list can be built
(`load_capex_items()` in `generate_project_output.py`). A normal run does not open it.

Everything else in the repository — including the real project budgets under `input/budget_planning/`
— is not read at runtime. See `docs/06-unread-datasets.md`.
