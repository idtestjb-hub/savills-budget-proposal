## Why

The AI Guideline form carries an `AI GUIDELINE` column (stripped from the working template by change
A) that tells you exactly how to write every remark — a per-line working note on
`2. Budget-Management Fund` and a **composed section narrative** on `1. Summary` that the client
reads (`docs/11-guideline-remark-model.md`). The pipeline does the line-level part; it does **not**
compose the summary narrative — `1. Summary` column K is blank or pulls one line's remark — and it
never applies the guideline's mandatory VAT sentence. A budget whose summary does not explain its
own numbers cannot be handed to a client.

## What Changes

- **`1. Summary` column K is composed per the guideline recipe**, for every non-zero PART‑1 total,
  replacing today's blank / single-line pull. Each narrative is built from the project's own data:
  - `RM` — chargeable area by product + fee rate by product (with VAT status) + the developer
    pre‑collection assumption (from `0. Info` and the fill‑up sheet)
  - `RPa` — the parking assumptions (from `0. Info`)
  - `RO` / `EMA` / `EMB` / `ESM` / `ESA` / `ER` / other‑service — *"Dự ước bao gồm: …"* enumerating
    every child line the pipeline wrote a figure to, by name
  - `ESC` — events (count + names) / PCCC drill / decorations
  - Security & Cleaning — the role‑by‑role position breakdown (from `A2` / `A3`) + the 24h unit rate
  - `ESI` — the two insurance items · `EN` — the three capex groups + "depreciated over 24 months"
  - `EEW` / `EEE` / `EED` — consumption + tariff with its citation + fill‑up basis + the electricity
    40 % floor
  - `ESA` / `ESL` append the fixed *"Điều 150 Luật nhà ở 2023 …"* sentence · `RI` a default text
  - Output **bilingual — Vietnamese then English**.
- **One VAT‑sentence helper**, called by the K composer and by the existing `_write_remark` /
  `_opex_remark`, appends the guideline's mandatory sentence
  (*"Chi phí đã bao gồm VAT và dự ước tại năm ⟨budget year⟩" / "This cost includes VAT, estimated for
  year ⟨N⟩"*) to every incl‑VAT remark, keyed on the `0. Info!F7` switch
  (`KHOÁN` = excl‑VAT throughout · `THU HỘ CHI HỘ` / `KHÔNG KHOÁN` = incl‑VAT throughout).
- **`Costing_Method_Catalogue.csv` gains the guideline's remark rules** — the 55 line‑level
  `AI GUIDELINE` instructions folded into `remark_components`, and the 19 summary‑row composition
  recipes recorded (a new column or new rows). The catalogue stays the single authority for remark
  content.
- **Verification checks remark content** — for every code the pipeline fills, its `T` remark carries
  the components its catalogue entry lists; for every non‑zero `1. Summary` PART‑1 total, its `K`
  remark names every child line that has a figure and carries the VAT sentence where the figure
  includes VAT.

**No budgeted figure moves** — this is display-only. `verify.py`'s 24 analysis + 7 deliverable
baseline figures are unchanged.

## Capabilities

### New Capabilities

- `deliverable-remarks`: how the client deliverable presents the reasoning behind every figure — a
  composed section narrative on `1. Summary` per the guideline's recipe, the mandatory VAT‑treatment
  sentence, and the bilingual form — and how verification confirms a remark says what it must.

### Modified Capabilities

- `costing-method-catalogue`: the catalogue additionally records, per summary row, the composition
  recipe for its `1. Summary` narrative, and records the VAT‑treatment sentence rule; its
  `remark_components` coverage is extended to every code the guideline's `AI GUIDELINE` column
  instructs.

## Impact

- **Affected code**:
  - `generate_project_budget.py` — a new `1. Summary` K‑narrative composer (reads `0. Info`, the
    fill‑up curve, and the set of codes the pipeline wrote); a VAT‑sentence helper shared with
    `_write_remark`; `_opex_remark` gains the VAT sentence.
  - `verification/checks.py` + `verify.py` — a `check_remark_content` (section 5e), following the
    existing COM‑check pattern.
- **Affected data**: `data/master_list_verified/Costing_Method_Catalogue.csv` — additive columns /
  rows only. **No Generation A or Generation B table changes; no Fact/Dim join key changes** — the
  Copilot Studio package's live data is unaffected.
- **Baselines**: none move. `deliverable_baseline.json` and `baseline.json` are unchanged (remarks
  are text, not baselined figures). A new remark-content check is added; it records no numeric
  baseline.
- **Risk**: Low. Display-only; no figure moves; the composed narratives are generated from data the
  pipeline already has. The judgement call is the Vietnamese wording of the templates, which a PM
  should review (manual spot-check task).
