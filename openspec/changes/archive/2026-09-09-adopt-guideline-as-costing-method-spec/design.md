## Context

See `proposal.md - Why` for motivation. Design-relevant current state:

- The pipeline's method authority today is `input/logic/EXENSIVE LOGIC.xlsx`, consulted by hand.
  The `logic-spec-method-alignment` capability requires each filled code to use "the method its
  spec states"; the active `report-method-coverage-in-verification` change intends to score write
  sites against a recorded per-code method verdict.
- The AI Guideline form (`docs/AI Guideline - 2027 Resi Budget Form (IT team) .xlsx`) carries the
  method as free text in a dedicated column: `L` on `1. Summary` and `0. Info`, `W` on
  `2. Budget-Management Fund`, `DJ` on `Master Info`. Both `docs/` workbooks contain a corrupt
  defined name (`#N/A` in print titles, a OneDrive artifact) and must be repaired before any
  reader can open them — the same trap already documented for this project's input workbooks.
- The pipeline's `2. Budget-Management Fund` output and the guideline share an identical 492-line
  code list, so codes are a stable join key between the catalogue and the write sites.
- Budget figures in any spec or report must state currency and unit (`openspec/config.yaml`).

## Goals / Non-Goals

**Goals**

- Produce one machine-readable catalogue file, one row per budget code, that the pipeline and
  `verify.py` can read without re-parsing the guideline workbook.
- Record for each code: the method, its named inputs, the components its remark must contain, the
  legal citation it must carry, the guideline sheet the instruction came from, and — where they
  differ — how the guideline method relates to the `EXENSIVE LOGIC.xlsx` method.
- State a single precedence rule for method-selection conflicts.
- Leave behind a clear, ordered list of the downstream changes this enables.

**Non-Goals**

- No extractor script that runs in the pipeline. Extraction is a one-time, human-reviewed exercise;
  the catalogue is maintained as a source file thereafter.
- No change to how any figure is computed, no new intake field, no verification code. Those are the
  downstream changes.
- Not a re-transcription of `EXENSIVE LOGIC.xlsx`. The catalogue points at it for formula
  mechanics rather than copying them.
- The catalogue does not need a row for every one of the 492 codes on day one — only the codes the
  pipeline fills today plus the codes the downstream family will fill. Coverage can grow.

## Decisions

### D1 — Catalogue format: CSV under `data/`, one row per code

A flat CSV (`data/master_list_verified/Costing_Method_Catalogue.csv` or similar — final path in
tasks) with columns roughly:

| Column | Purpose |
|---|---|
| `code` | e.g. `EEE`, `RM.0A` — the join key to write sites and to the template |
| `item_en` / `item_vi` | label, for human readers |
| `section` | `revenue` / `management-expense` / `sinking-fund` |
| `method` | short canonical method name (e.g. `consumption-x-tariff`, `benchmark-by-area-ratio`, `contract-posts-x-rate`, `developer-covers-unlet`) |
| `method_detail` | one sentence, plain language |
| `inputs` | the quantities/rates the method needs, named |
| `occupancy_scaled` | yes/no — does this line ramp month-by-month with fill % |
| `remark_components` | the parts the generated remark must contain, as a list |
| `legal_citation` | e.g. `QĐ 1279/QĐ-BCT`, `NĐ 105/2025`, `QĐ 67/2025` — blank if none |
| `guideline_sheet` | where the instruction was read from |
| `exensive_logic` | `agrees` / `differs` / `not-covered` / `mechanics-only` |
| `precedence_note` | free text, only when `exensive_logic = differs` |

Rationale: CSV is what every other reference table in `data/` already is; `verify.py` and the
generators already read CSVs; a PM can open it in Excel. Alternatives considered — JSON (nested
`remark_components` is cleaner, but breaks the "every reference table is a CSV" convention and is
harder for a non-engineer to review); a Markdown table (readable, not reliably machine-parsable at
492 rows); keeping it as an annotated copy of the guideline workbook (leaves the corruption trap and
the prose-parsing problem in place).

### D2 — Extraction is manual, reviewed, and recorded once

A throwaway helper repairs the workbook and dumps the guideline column next to each code; a human
turns each prose instruction into the structured columns; the result is committed. There is no
standing extractor. Rationale: the guideline column is prose written for a person, not a grammar;
an NLP pass would need the same human review afterwards and would rot. The cost is a few hours once.

### D3 — Precedence: the catalogue wins on *which method*, `EXENSIVE LOGIC.xlsx` wins on *mechanics*

When both documents name a method for a code and they differ, the catalogue's `method` is
authoritative and `precedence_note` records why. When they agree on the method but `EXENSIVE
LOGIC.xlsx` carries the detailed formula (coefficients, rounding, frequency), that formula stands
and `exensive_logic = mechanics-only`. This keeps the existing energy work
(`cost-energy-from-consumption-and-tariff`) valid: guideline and spec agree there, so nothing moves.

Alternative considered — guideline supersedes entirely. Rejected: `EXENSIVE LOGIC.xlsx` has formula
detail the guideline column does not, and discarding it would strand the active changes that cite
it. **Confirmed by the PM on 2026-09-09** (proposal Impact, Decision 2 / `docs/05-decisions.md` D7).

Because the ramp is now a confirmed requirement (proposal Decision 3), `occupancy_scaled` is not
advisory metadata — it is the flag the downstream occupancy-ramp change keys off, and the catalogue
must set it correctly for every revenue and load-driven code (`RM`, `RM.0A`, `RP*`, `RPa`, `EEE`,
`EEW`, cleaning, and any other line the guideline links to the fill-up sheets).

### D4 — `logic-spec-method-alignment` gets a clarifying delta, not a rewrite

The capability's requirements are already source-agnostic ("the costing specification"). The delta
adds one requirement fixing what "the costing specification" names — the catalogue plus
`EXENSIVE LOGIC.xlsx`, with D3's precedence — and one scenario that a code's remark must contain the
components the catalogue lists for it. No existing scenario is removed or reworded.

### D5 — The downstream family is recorded in this change's `tasks.md`, not scaffolded

`tasks.md` ends with a list of the follow-on changes, each with a one-line scope and its dependency
on this catalogue. They are scaffolded individually, later, after their own review:

- **skeleton re-base** — pipeline writes the 25-sheet form (adds occupancy sheets, `B2.6` waste,
  `Master Info`); the 19-sheet form retained as backup (proposal Decision 1)
- **occupancy ramp** — `RM`, `RM.0A`, `RP*`, `RPa`, `EEE` floor and the other `occupancy_scaled`
  codes vary month by month with a fill-up curve (proposal Decision 3)
- **energy from consumption × tariff** — already active as `cost-energy-from-consumption-and-tariff`
- **per-product management fee** — `RM` written as per-product rows on one NFA basis (the open B3)
- **blank lines** — `ESI` insurance (NĐ 105/2025), `ER` repairs, household waste (QĐ 67/2025),
  `ESC` three-part events; each needs a rate source or its own decision
- **multi-year / pre-opening output** — pre-opening budget + Y1/Y2 roll-up; depends on the ramp

## Risks / Trade-offs

- **The catalogue drifts from the guideline when Savills revises the template.** → `guideline_sheet`
  and a header comment record the guideline file's version and date; a downstream check can diff the
  code list. Re-extraction is a known, bounded task.
- **A prose instruction is ambiguous and the human extractor guesses.** → `method_detail` quotes or
  closely paraphrases the source; anything genuinely unclear is left as `method = unclear` with the
  quote, not resolved by invention (mirrors `logic-spec-method-alignment`'s "do not invent a
  figure").
- **The PM answers the precedence question the other way (guideline supersedes).** → only D3, D4 and
  the `exensive_logic` column semantics change; the format and the downstream list stand. Contained.
- **Scope creep into "just fix the energy lines while we're here".** → this change edits no code;
  the specs and tasks forbid a pipeline edit. Enforced by review.
- **The corrupt-workbook repair alters content.** → the repair only strips the invalid defined
  name; extracted values are spot-checked against the file opened in Excel.

## Migration Plan

Additive. The catalogue file is new; the `logic-spec-method-alignment` delta clarifies wording
without changing behaviour. Nothing to roll back beyond deleting the file and the delta. No pipeline
run is affected until a downstream change consumes the catalogue.

## Open Questions

- Final filename and directory for the catalogue (`data/master_list_verified/` vs a new
  `spec/` directory) — settled in `tasks.md`, does not affect the specs or approach.
- Whether `Master Info`'s 90 comparables are transcribed into the catalogue now or left for the
  per-product / benchmark downstream change — leaning "later", as it is data not method.
