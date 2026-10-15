## Why

For a project Savills already runs, both logic files say the same thing about common-area electricity (`EEE.C`) and
water (`EEW.C`): start from what the building actually used. `EXENSIVE LOGIC.xlsx` gives "average monthly kWh (last 12
months) x updated tariff" and forbids a flat inflation percentage; `Operation Budget logic` gives "the average of last
year's reported figures". The tool does neither. Even in Existing-project mode (added by `carry-forward-staffing`) it
prices both lines as for a new building: a usage ratio from one other property (A&K Tower) times the floor area, ramped
by the new-building fill-up curve. Real budgets show what PMs do by hand instead: 25 of 108 real electricity lines (22 files)
add or cut a flat "x%" on last year's spend, the kind of uplift the logic file forbids. `carry-forward-staffing` named
electricity as the next line to carry forward.

## What Changes

- **Existing-project mode only.** In "New prospect" mode every figure stays exactly as today.
- A new input sheet **Prior-Year Utilities**. Per line (`EEE.C`, `EEW.C`) and month, the PM enters:
  - the amount actually spent (VND), and whether it includes VAT;
  - optionally, the consumption (kWh or m³).

  Per line, the PM may also enter:
  - the tariff category, if it is not the default;
  - the unit price shown on the bill, which wins over the table;
  - the approved prior-year amount (VND/year);
  - a consumption override for the budget year, with a reason code.
- **Baseline = actual average of the 12 most recent months** that have a figure.
  - Fewer than 12 months: the average of the months entered x 12, flagged.
  - Fewer than 3 months: the approved prior-year amount becomes the baseline, repriced for tariff and VAT changes. If
    that amount is missing too, the run stops and names the fields.
- **Price and VAT come from a new dated, sourced tariff table**, `Ref_UtilityTariffs.csv`, built like the labour-law
  table. The tool adds no percentage of its own.
  - Defaults:
    - electricity at the administrative/public-service rate below 6 kV, 2,226 VND/kWh excl. VAT (QĐ 1279/QĐ-BCT;
      TT 60/2025/TT-BCT Điều 8.2.b);
    - water at the Ho Chi Minh City household top tier, 14,400 VND/m³ excl. VAT, plus the drainage and wastewater
      charge of 30% (QĐ 25/2019/QĐ-UBND places "chung cư" in the household group).
  - VAT follows the law for each month of the budget year. The form's existing VAT switch (`2. Budget-Management Fund`
    F7) decides whether the line is shown with or without VAT.
- **Monthly spread:** consumption is spread evenly over the 12 months. No fill-up curve and no 40% electricity floor
  apply in this mode, because actual spend already reflects the building's current occupancy.
- **Remarks and reasons:**
  - Every change from the approved prior-year amount is explained in the remark, keeping the guideline's original remark
    first and adding "Điều chỉnh so với NS <năm>: …".
  - The tool explains effects from actual consumption, tariff and VAT itself.
  - A PM consumption override needs a reason code. Without one, the run fails.
- **Utility Bridge:** a new internal sheet in the analysis workbook, not on the client deliverable. It runs from the
  approved prior year, through the consumption, tariff, VAT and PM-override effects, to the budget year, and ties
  exactly to `EEE.C` and `EEW.C`.
- **Verification** gets an invented Existing-project sample with utility data and checks:
  - the bridge ties to the deliverable;
  - a missing reason fails;
  - a duplicated month stops the run;
  - New prospect is unchanged.

Not in this change:
- residents' own use and collect-on-behalf (`EEE.A` / `EEW.A`, `RO3` / `RO4`), which belong to `use-operating-project-actuals` P4;
- the per-zone rows (`EEE.AA…P`, `EEE.F1/F2`, `EEW.AA…P`) and diesel (`EED.C`);
- the New-prospect VAT question (docs/22 D1).

## Capabilities

### New Capabilities

- `existing-project-utilities`: Existing-project mode for common-area electricity and water. Covers:
  - the actual-spend baseline and its month rules (window, blank, zero, duplicate);
  - the fallback to the approved amount;
  - the tariff table, default categories and VAT;
  - the even monthly spread;
  - reason codes for PM overrides;
  - the Utility Bridge.

### Modified Capabilities

- `occupancy-ramp`: in Existing-project mode, common-area electricity and water are not distributed by the fill-up
  curve and carry no electricity floor.
- `deliverable-remarks`: changed `EEE.C` / `EEW.C` lines carry the "Điều chỉnh so với NS <năm>" sentence after the
  guideline's remark.
- `input-workbook-reading`: the Prior-Year Utilities sheet is read by label; a workbook without it is read as before.
- `budget-workflow-verification`: verification runs an Existing-project sample with utility data and ties the Utility
  Bridge to `EEE.C` and `EEW.C`.

## Impact

- **Reads (new):**
  - the input workbook's Prior-Year Utilities sheet;
  - `data/generation_B_verified/Ref_UtilityTariffs.csv` (new, one row per tariff component with effective dates and
    legal source).
- **Code:**
  - new `existing_utilities.py` and `utility_tariffs.py`;
  - `generate_project_budget.py` (Existing-mode writing of `EEE.C` / `EEW.C`);
  - `generate_project_output.py` (Utility Bridge, OPEX sheet note);
  - `build_project_input_form.py` and `add_existing_project_sheets.py` (new sheet);
  - `verification/` (checks, section 8 samples);
  - unit tests.
- **Figures:**
  - New prospect: none. The baselines are not re-recorded, and an A/B comparison on the standard sample must show 0
    cell differences.
  - Existing-project mode: `EEE.C` and `EEW.C` move to the actual-spend basis. The back-test on the project X clone
    (real data, kept in `Savills-local`) measures the movement against the real 2027 file, and the PM signs it off
    before archive.
- **Breaking for Existing-project inputs:** an input workbook in Existing-project mode that has neither utility actuals
  nor an approved prior-year amount for these two lines stops with a message naming the fields. The two invented
  section-8 samples get utility data.
- **Order:** builds on `carry-forward-staffing` (the project mode field). Archive that change first.
- **Data protection:** real figures stay in `Savills-local` and `docs/05-decisions.md`; only invented samples go into
  `source_code`.
