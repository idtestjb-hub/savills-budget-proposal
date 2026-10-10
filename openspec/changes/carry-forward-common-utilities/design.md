## Context

See proposal.md (Why) and the specs for the required behaviour.

**The code today:**
- `estimate_opex.py` prices electricity and water as A&K Tower's usage per m² × this project's NFA × a tariff read from
  `Fact_OPEX.csv`:
  - electricity 2,226 VND/kWh, excluding VAT;
  - water 19,786 VND/m³, a built-up figure that includes VAT.
- `generate_project_budget.py` writes `EEW.C` (row 230) and `EEE.C` (row 240) of `2. Budget-Management Fund` through
  `_write_ramped_row`:
  - water follows the resident curve;
  - electricity follows `fill_curve.year1_electricity_fills()`, which has a 40% floor.
- `carry-forward-staffing` (applied, not archived) added:
  - the "Project Mode" and "Prior Budget Year" fields;
  - the `Prior-Year Roster` sheet and the reason-code pattern;
  - the dated `Ref_LaborLawParams.csv` table;
  - the `Staff Bridge` sheet and verify section 8 with two invented Existing samples.

  This change copies those patterns rather than inventing new ones.

**The data PMs have** (scan of 75 real budgets, `Savills-local`; no real names here):
- Utility actuals exist as monthly VND amounts: 50 files carry an "actual" column for these codes.
- Only 30 of 108 real electricity lines mention kWh.
- Of the real water remarks sampled, those in Ho Chi Minh City price common-area water at the household top tier
  (base alone, or built up with the drainage charge and VAT). A project in another province uses its local water
  company's price.

**Public basis.** The "Read" column says how far each item has been checked. Tasks 1.1 and 1.2 confirm every row
against its primary text before it goes into the table.

| Item | Value | Basis | Read |
|---|---|---|---|
| Electricity for apartment common areas | Administrative/public-service tariff (TT 60/2025/TT-BCT Điều 8.2.b): 2,226 VND/kWh below 6 kV, 2,138 VND/kWh at 6 kV and above, from 10/05/2025 | QĐ 1279/QĐ-BCT | Session of 2026-10-05 (docs/19 correction note); not re-read on 2026-10-11 |
| Water | Household group includes "chung cư"; top tier 14,400 VND/m³ excluding VAT, since 2022 | QĐ 25/2019/QĐ-UBND Điều 1–2 | Decision text read on caselaw.vn, 2026-10-11 |
| Drainage and wastewater charge | 30% of the water price from 2025 | QĐ 17/2021/QĐ-UBND roadmap | Search results only, 2026-10-11; the 2026 continuation rests on a secondary source (docs/19) |
| VAT, electricity and drainage service | 8% until 31/12/2026, 10% from 01/01/2027; no extension found on 2026-10-11 | NQ 204/2025/QH15, NĐ 174/2025/NĐ-CP | Search results (baochinhphu.vn and others), 2026-10-11 |
| VAT, clean water | 5% | Luật Thuế GTGT 48/2024/QH15 | Not yet looked up; task 1.1 |

## Goals / Non-Goals

**Goals:**
- Existing-project `EEE.C` and `EEW.C` built from the project's own actual spend, repriced only by published tariff and
  VAT rows, with every change explained.
- Zero change in New-prospect mode, checked cell by cell.
- Tariffs in one dated, sourced table instead of in `Fact_OPEX.csv` comments or code.

**Non-Goals:**
- Changing the New-prospect method or its tariffs, including the VAT question docs/22 D1.
- Time-of-use blending of the business electricity tariff. A PM who picks that category enters the bill's average
  price.
- Reading bills automatically, or linking to accounting data.
- Diesel, residents' own use, collect-on-behalf, per-zone rows, and `2.2 Common area Fund` logic (that sheet keeps its
  template share formula).

## Decisions

### D1. A new input sheet, "Prior-Year Utilities", with two labelled blocks

**Block `UTILITY ACTUALS`.** One row per line and month, with the columns:
- Line (`EEE.C` / `EEW.C`, dropdown);
- Month (MM/YYYY);
- Amount (VND);
- Includes VAT (Yes/No);
- Consumption (kWh or m³, optional);
- Note.

**Block `UTILITY LINES`.** One row per line, with the columns:
- Tariff Category (dropdown from the table);
- Unit Price on Bill (VND, excluding VAT, optional);
- Unit Price Source;
- Prior-Year Approved (VND/year, optional);
- Approved Includes VAT (Yes/No);
- Budget-Year Consumption Override (per month, optional);
- Reason Code;
- Reason Note.

The reason list sits in a side column that feeds the dropdowns, as on `Prior-Year Roster`.

**Alternatives rejected:**
- A fifth block on `Prior-Year Roster`: that sheet is about staff and is already long.
- Twelve month columns on one row per line: a bill period sometimes runs over 13 or more months, or has gaps, and rows
  make blanks and duplicates visible.

### D2. Tariff table `data/generation_B_verified/Ref_UtilityTariffs.csv`

**Columns:** `Utility`, `Category`, `Component`, `Value`, `Unit`, `EffectiveFrom`, `EffectiveTo`, `Region`,
`LegalBasis`, `SourceUrl`, `CheckedOn`, `Note`.

**Components:**
- `base` (VND per kWh or m³, excluding VAT);
- `wastewater_pct` (water only, % of base);
- `vat_pct`;
- `wastewater_vat_pct`.

**Rows:**
- The rows needed to price every month from the earliest month allowed to the end of the budget year: electricity
  categories below 6 kV and 6 kV and above; the HCMC household top tier; VAT by period.
- An open `EffectiveTo` means "in force until replaced".
- A category with no `base` row (business electricity) requires the PM's bill price.
- The loader fails on a row with no `LegalBasis` or no `EffectiveFrom`, and on a month before the earliest row.

**Repository handling** (same as `Ref_LaborLawParams.csv`):
- lives under the git-ignored `data/` folder;
- force-added to the outer repo;
- dated backup before any edit.

### D3. Unit price of a month on a VAT basis

**Excluding VAT:**
- electricity = `base`;
- water = `base × (1 + wastewater_pct)`.

**Including VAT:**
- electricity = `base × (1 + vat_pct)`;
- water = `base × (1 + vat_pct) + base × wastewater_pct × (1 + wastewater_vat_pct)`.

A PM bill price replaces `base` for that line in every month.

**Consumption of a month:**
- the entered consumption; otherwise
- the amount ÷ the unit price on the amount's VAT basis.

**Implied-rate check:** when both are given, the implied rate is compared on the same basis. A difference above 1%
is flagged. The 1% matches the staffing back-cast tolerance.

### D4. Baseline, fallback and bridge arithmetic

**Window and baseline:**
- `q̄` = the average consumption over the months in the window that have an amount (window: spec requirement 2).
- With 3 to 11 months, the average still applies to 12 months and the line is flagged.
- With fewer than 3 months and an approved amount `A`: `q̄ = A ÷ Σ(prior-year monthly unit price on A's VAT basis)`.
  - The prior year is the "Prior Budget Year" field; when blank, the budget year minus 1.
  - This is what "repriced only for tariff and VAT" means.

**Bridge arithmetic.** Every amount is on the deliverable's VAT basis (switch `2. Budget-Management Fund`!F7):
- `B` (actual baseline) = `q̄ × 12 × p₀`, where `p₀` is the unit price of the latest window month.
- Write `p̃ₘ` for month m's price computed with month m's base and wastewater rows but with `p₀`'s VAT rates.
- Tariff effect = `q̄ × Σₘ (p̃ₘ − p₀)`.
- VAT effect = `q̄ × Σₘ (pₘ − p̃ₘ)`.
  - For water this covers both VAT components.
  - It is zero on an exclusive (KHOÁN) basis.
- Override effect = `(q_override − q̄) × Σₘ pₘ`.
- Budget year = `B` + tariff effect + VAT effect + override effect = `Σₘ q × pₘ`, the same sum the deliverable writes.
- When `A` is given:
  - consumption effect = `B − A`, with `A` converted to the deliverable's VAT basis using prior-year VAT rates;
  - the bridge starts from `A`;
  - otherwise it starts from `B`.

**Why it ties:** the deliverable and the bridge use the same monthly prices, so they tie to the VND by construction,
and verify checks within 1 VND.

**A useful property:** when only amounts are entered and no tariff row changes, the budget year equals the actual
average whatever category is chosen. The category then affects only the kWh or m³ shown in the remark.

### D5. Writing the deliverable

**When:** only in Existing-project mode.

**What `build_budget()` does:**
- calls `existing_utilities.compute()`;
- writes the twelve monthly amounts of `EEE.C` and `EEW.C` through the same row writer (fractions all 1.0, amounts
  from the compute result, not from `estimate_opex`).

**The remark:**
- the guideline remark for the code, without the curve and floor sentences;
- then `adjustment_sentence()`, in the shape of `existing_staffing.adjustment_sentence`;
- then the VAT sentence that already exists.

**Related lines:**
- The `1. Summary` narrative for `EEE`/`EEW` reads the same remark source, so it loses the curve wording too.
- `2.2 Common area Fund` keeps its template formula (a share of `2. Fund`).

### D6. Analysis workbook

**`Utility Bridge` sheet:**
- built from the compute result: the amounts of D4, the months used with each month's amount, consumption and
  source, and the flags;
- created only in Existing-project mode.

**OPEX sheet:**
- In Existing-project mode its Electricity and Water rows show the Existing figures and point to `Utility Bridge`, so
  the two workbooks never disagree.
- New prospect is untouched.

**Alternative rejected:** leaving the OPEX sheet on the new-building estimate with a "reference only" label. Two
different annual electricity figures in one project's outputs would confuse the reader.

### D7. Reasons

- **Own list:** utilities get their own reason list (spec requirement on overrides), in `existing_utilities.py`, using
  the reason record (code, text, source) of `existing_staffing.py`.
- **Tool-written reasons** name:
  - the months used ("thực chi bình quân 12 tháng 09/2025–08/2026");
  - the unit price and its legal basis;
  - the VAT rate and its legal basis.
- **Approval:** the Head of PM approves the list before archive, as for staffing.

### D8. Stops versus flags

**Stops**, all naming the row or field:
- water with no bill price when "City / Province" is not Ho Chi Minh City or is blank;
- a category with no single table price (business electricity) and no bill price;
- negative amount;
- duplicate month;
- a month in or after the budget year;
- an unknown line, category or reason code;
- an override without a reason;
- "Khác" without a note;
- a month not covered by the table;
- fewer than 3 months with no approved amount;
- Existing mode with no utility sheet.

**Flags** (printed summary and bridge, never blocking):
- zero months;
- missing months;
- fewer than 12 months;
- implied-rate differences;
- months older than the window that were ignored.

### D9. Existing inputs

- `add_existing_project_sheets.py` adds the new sheet to a dated copy when it is missing, as it does for the roster.
- The two invented section-8 samples (`verification/fixtures/build_existing_fixture.py`) get utility data:
  - **sample 1:** 12 months with VAT-inclusive amounts, consumption on some months, and one zero month;
  - **sample 2:** 2 months plus an approved amount (the fallback path), and an override with a reason.

## Risks / Trade-offs

- **[The 2026 drainage and wastewater charge rests on a secondary source]** (docs/19: 30% continued into 2026). →
  Task 1.2 looks for the primary text. If none is found, the row's `Note` says so and the remark cites the 2021
  roadmap.
- **[VAT 10% for 2027 may be extended at 8%]** → One table row; the remark names the basis. Re-check before each
  release.
- **[The default water category may not match a building's bill]** (some branches bill a common meter at another
  rate). → The implied-rate flag catches it when consumption is entered. With amounts only, VND is unaffected (D4).
- **[Existing-mode input workbooks without utility data now stop]** (for example the project X clone). → The message
  names the sheet and the helper; the clone is updated in the back-test task.
- **[`use-operating-project-actuals` P3 adds a stable-operation switch to the same lines]** → This change ADDs its own
  requirement to `occupancy-ramp`. When P3 is applied, Existing mode wins for `EEE.C`/`EEW.C`, and its design must say
  so.
- **[Actual spend may include one-off events]** (a leak, construction power). → The PM overrides consumption with a
  reason. The tool does not try to detect outliers.

## Migration Plan

- **New prospect:** nothing to migrate; an A/B comparison on the standard sample must show 0 cell differences.
- **Existing-project input workbooks:** run `add_existing_project_sheets.py` to get a dated copy with the new sheet,
  then fill it in.
- **Rollback:** revert the two commits (submodule, then outer repo). The tariff table is additive.

## Open Questions

- The Head of PM's approval of the six utility reason codes. This can follow apply: the list is data in one place and
  does not change the specs' structure.
