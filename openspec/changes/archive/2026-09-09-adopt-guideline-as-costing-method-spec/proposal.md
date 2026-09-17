## Why

On 2026-09-09 two files arrived in `docs/`: **"AI Guideline - 2027 Resi Budget Form (IT team)"** and
a fully worked sample, **"Ngân sách mẫu … năm 1 + năm 2 … tiền khai trương"**. The first is Savills'
current residential budget template with an instruction written against **every one of its 492
budget lines**, plus the occupancy machinery, benchmark comparables, and the legal references each
figure must cite. The second shows those instructions carried out end to end for the hardest case —
a brand-new project with a pre-opening phase and a two-year fill-up.

Today the pipeline's method authority is `EXENSIVE LOGIC.xlsx`. A comparison of the most recent
generated project (Diamond Skyline, 2026-09-09) against the new guideline found:

- the pipeline writes the **correct 492-line template skeleton**, but fills only the operational
  two-thirds of it;
- it runs in **single-year, 100%-occupancy** mode — the guideline and sample both require a
  month-by-month occupancy ramp;
- the **three largest energy lines** use a cost-per-m² ratio, which the guideline (like
  `EXENSIVE LOGIC.xlsx`) rejects in favour of consumption × tariff;
- lines the guideline populates — `RM.0A` (developer pays on unsold units), `RM.PA`, insurance,
  repairs, household waste — are **left blank**;
- generated remarks are missing mandated components (e.g. `ESC` must state events + PCCC drill +
  décor; `EEE` must cite QĐ 1279/QĐ-BCT).

The guideline is the most complete statement of Savills' costing method the project has ever had.
But it is a workbook with prose in a column — the pipeline cannot consume it, and there is no
recorded decision on how it relates to `EXENSIVE LOGIC.xlsx`. This change does that groundwork and
nothing else. **It moves no budget number.**

## What Changes

- **The repo gains a structured, version-controlled method catalogue** extracted from the AI
  Guideline form: one row per budget code, recording the method, its inputs, the components its
  remark must contain, the legal citation it must carry, and the guideline sheet it came from.
- **The catalogue is declared the project's source of truth for *which method each code uses*** and
  for *what each remark must say*. `EXENSIVE LOGIC.xlsx` remains the source for detailed formula
  mechanics where the two overlap; a stated precedence rule resolves conflicts.
- **The guideline's occupancy dimension is recorded as a committed downstream change** — revenue and
  load-driven costs vary month by month with a fill-up curve. Not implemented here; the design is
  written to it because the PM has confirmed it is a hard requirement (Decision 3).
- **The output skeleton is re-based on the 25-sheet form** as a downstream change — adding the
  occupancy sheets, `B2.6` household waste, and `Master Info` the 19-sheet form lacks.
- **The downstream work is enumerated** as a named change family (occupancy ramp; skeleton re-base;
  energy from consumption × tariff; per-product management fee; the blank lines; multi-year /
  pre-opening output), each to be proposed, reviewed and landed on its own.
- **Three PM decisions are settled** (see Impact) and the catalogue and specs are written to them.

No pipeline script is edited. No intake form field is added. No output changes.

## Capabilities

### New Capabilities

- `costing-method-catalogue`: the project holds an extracted, structured record of Savills' costing
  method for each budget code — method, inputs, required remark components, legal citation, source
  sheet — derived from the AI Guideline form; this record is the authority the pipeline and the
  verification harness consult for method and remark expectations, and it states its own precedence
  relative to `EXENSIVE LOGIC.xlsx`.

### Modified Capabilities

- `logic-spec-method-alignment`: its requirements refer to "the costing specification" as a single
  document. This change makes explicit that the costing specification is the combination of the
  method catalogue (which method, which remark components) and `EXENSIVE LOGIC.xlsx` (formula
  mechanics), with the catalogue taking precedence on method selection. The behavioural
  requirements themselves are unchanged; only the named source of truth is clarified.

## Impact

**Affected systems**

- **Data / reference files** — adds one new catalogue file under the repo (format decided in
  `design.md`). Reads the two `docs/` workbooks as source material.
- **No code** — `generate_project_budget.py`, `generate_project_output.py`, the intake form builder,
  and `verify.py` are untouched by this change. They are the subjects of the downstream changes.
- **Generation A / Generation B** — neither is read or written. **No Fact/Dim table changes and no
  join-key changes**, so the Copilot Studio package's live data is unaffected.

**Relationship to active changes**

- `cost-energy-from-consumption-and-tariff` — the catalogue records the same method this change
  already implements for `EEE`/`EEW`/`EED`; that change is the energy entry in the downstream family
  and continues on its own.
- `report-method-coverage-in-verification` — the catalogue is the record its method-fidelity
  scoring will hold write sites against; this change supplies the catalogue, that change consumes it.
- `fix-parking-allocation-divide-by-zero` — `RP*` / `RM.PA` catalogue rows inform it.

**PM decisions — answered 2026-09-09** (also logged in `docs/05-decisions.md` as D6–D8)

1. **Canonical template.** The **25-sheet `2027 Resi Budget Form (IT team)` is now the standard.**
   The 19-sheet `202608 - 2027 Resi Budget Form` is retained in `input/template/` as backup
   reference and marked superseded. Re-basing the output skeleton onto the 25-sheet form is a
   downstream change.
2. **Precedence.** Where the AI Guideline and `EXENSIVE LOGIC.xlsx` state different methods for the
   same code, **the catalogue wins on method selection; `EXENSIVE LOGIC.xlsx` remains authoritative
   for formula mechanics** (coefficients, rounding, frequency) where the two agree on the method.
3. **Occupancy ramp.** **Required.** A generated budget for a project not yet at stable occupancy
   must show revenue and load-driven costs ramping month by month with a fill-up curve. A
   steady-state single year is acceptable only for a project already at stable occupancy.
