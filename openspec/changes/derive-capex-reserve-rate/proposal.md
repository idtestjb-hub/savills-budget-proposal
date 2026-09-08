## Why

`CAPEX_RESERVE_RATE = 0.10` is a hardcoded guess. Its own comment says so — *"a commonly cited
property-management rule of thumb, NOT this project's own real reserve policy, which isn't in the
source data."*

**The real policy is in the source data.** Reading `EN1`–`EN3` out of four real project budgets:

| Project | Year-1 Capex | Later year | Period | Implied rate |
|---|---|---|---|---|
| Parking Building | 208,533,972 | 17,377,831 | 12 months | **8.33%** |
| Green Skyline | 318,989,410 | 36,918,094 | stabilised, 12 months | **11.57%** |
| Lumi Prestige & Elite | 421,854,831 | 35,154,569 | 9 months | 8.33% |
| Lumi Signature | 510,944,646 | 42,578,720 | 8 months | 8.33% |

Separately, `EXENSIVE LOGIC.xlsx` states the reserve as *"khoảng **0.1%** chi phí đầu tư trang thiết
bị ban đầu"* — about 0.1% of the initial equipment investment. **No project is remotely near that.**
0.1% would imply a thousand-year replacement cycle. The spec text is wrong, not the code.

So the hardcoded 10% is defensible but unevidenced, and the written spec that contradicts it is
wrong. Decided as **D4** in `docs/05-decisions.md`: derive the rate from the real projects rather
than fix a constant.

**And there is a larger error hiding behind the rate.** Green Skyline's **Year 2 is a full repeat of
Year 1 plus 3% inflation** — the drop to the reserve rate happens in **Year 3**. Lumi and Parking
Building drop in Year 2. The code drops in Year 2 for every project, which under-budgets Year-2
Capex by roughly **290 million VND** on a Green Skyline-shaped project. That is bigger than any
plausible error in the percentage.

## What Changes

- A small extractor reads `EN1`–`EN3` year-1 and later-year totals from the real project budgets and
  writes them to a reference table, one row per project, recording the period length in months.
- The pipeline computes the reserve rate from that table at run time — mean, with `n`, the range and
  the per-project detail reported in the output — instead of using a hardcoded constant.
- **The drop-to-reserve year becomes an input**, defaulting to the observed majority behaviour,
  rather than being fixed at Year 2 for every project.
- The output states which projects the rate came from, so a reader can see the evidence rather than
  a bare percentage.
- **The recorded baseline will move**, and must be re-recorded with a stated reason.

Deliberately **not** in scope:

- **Correcting `EXENSIVE LOGIC.xlsx`.** It is Savills' document, not this pipeline's. This change
  records that the measured rate contradicts it; changing the spec is the PM's call.
- **The fill-up ramp (B5).** Capex is nearly fill-independent — Green Skyline's 25/50/75/100%
  scenarios carry 34.8M / 34.8M / 35.8M / 36.9M — so the ramp must **not** be applied to Capex when
  B5 lands. Recorded here; implemented there.
- Re-deriving Capex **quantities**, which the back-test showed running ~2.2× high. That is a
  different problem in a different place (`estimate_capex_qty.py`).

## Capabilities

### New Capabilities

- `capex-reserve-rate`: how the pipeline determines the ongoing Capex reserve contribution for the
  years after initial equipment purchase, and from what evidence.

### Modified Capabilities

<!-- None. The three existing specs concern verification, outsourced service costs and product
     revenue pricing; none of them describes Capex reserve behaviour. -->

## Impact

**Code**

- A new extractor alongside the other `rescan_*` / `derive_*` scripts, producing the reference table.
- `generate_project_output.py` — `CAPEX_RESERVE_RATE` and its **twelve** use sites across the Owner
  Operating Position and Savills Fee Position sheets, plus the notes that quote it.
- `build_project_input_form.py` and `read_input()` — one new field for the drop year. Safe to add
  now that fields are found by label rather than by row.

**Data**

- One new reference table. No existing table is modified, and no Fact/Dim join key changes.

**A constraint worth stating plainly.** `n = 4`, and only two of those are unambiguous 12-month
years — the 8- and 9-month figures are `Year-1 ÷ 12` written into a short year, which may mean a
pro-rated annual rate or may mean the modeller simply entered one-twelfth. Depending on that
reading the mean is **9.1%** or **10.9%**. Both support ~10%; neither supports 0.1%. This change
makes the rate **evidenced and self-updating**, not precise.

**There is also no formula to copy.** The later-year cell in every source budget is `=$F$219` — a
plain reference to a manually entered column. The percentages above are implied ratios between two
independently typed numbers, not a rule the budgets apply.

**Outputs**

- Year 2–4 Capex changes on both position sheets. `total_profit_value` and `margin` are unaffected —
  they are Year-1 figures — but the multi-year tables move.

**Not affected**

- No dependency changes. No production data changes. No template changes.
