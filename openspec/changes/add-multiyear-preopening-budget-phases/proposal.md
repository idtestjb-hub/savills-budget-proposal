## Why

Today's deliverable generator produces exactly one steady-state operating year on one
`2. Budget-Management Fund` sheet. A real, delivered Savills budget — scanned this session
("Ngân sách mẫu dự án mới sẽ Operation năm 1 + năm 2 có giai đoạn tiền khai trương") — is structurally
much richer: a 3-month pre-opening phase (`0.Budget-Pre 03 months`), separate year-1/year-2/year-3
fund sheets (`2a`/`2b`/`2c`), matching common-area-fund sheets per year, occupancy-ramp variants at
25%/50%/75%/100% stabilized, and a `1. Summary` that reports year 1 and year 2 side by side. Our
current template (`2027 Resi Budget Form (IT team).xlsx`) and generator cannot produce any of this —
not because a rule is missing, but because the sheets themselves don't exist yet. This is the gap the
user's own instinct named directly: the input needs a way to say how many years (and whether a
pre-opening phase applies) a project needs estimated.

This is a genuinely large, novel capability — new template sheets, new generator logic to decide a
ramp/escalation schedule per phase, and a redesigned summary — not a bug fix. It is proposed
separately from `localize-line-level-remarks` (also raised from the same sample scan) because the two
are independent in scope and risk.

## What Changes

- Add a project-level intake choice for the operating horizon to project: how many post-opening years
  to generate (minimum 1, matching today's behavior), and whether the project has a pre-opening phase
  and its length in months.
- Add template sheets, generated on demand per project rather than baked permanently into the standard
  template: one pre-opening budget sheet (when requested) and one fund sheet + one common-area-fund
  sheet per requested year beyond year 1 (reusing today's single-year sheet as "year 1").
- Extend `1. Summary` to report every requested year side by side (today's single-year columns,
  repeated per year), matching the sample's `1. Summary năm 1 + năm 2` layout.
- Reuse the existing `occupancy-ramp` capability's fill-up curve for within-year distribution; this
  change is additive to it — it decides how many year-sheets exist and how a curve carries across the
  pre-opening-to-year-1 boundary and between years, not how a single year ramps internally.
- **BREAKING** for any downstream consumer that assumes exactly one `2. Budget-Management Fund` sheet
  by that literal name — a 2+-year project now produces `2a.`/`2b.`/etc. sheets instead. A 1-year,
  no-pre-opening project (today's only supported shape) SHALL continue to produce exactly today's
  sheet names and figures unchanged, so existing single-year projects are not broken.

## Capabilities

### New Capabilities
- `multi-year-budget-phases`: project-level control over how many operating years and whether a
  pre-opening phase are generated, and the per-phase sheet scaffolding and summary layout that follow.

### Modified Capabilities
- `standard-budget-template`: today's "the deliverable SHALL contain every sheet the standard template
  defines, sheet names matching the standard template's names" assumes one fixed sheet set; this
  changes to allow a per-project-configured set of year/phase sheets, generated from a template pattern
  rather than the template's own literal sheet list.
- `occupancy-ramp`: the fill-up curve extends across a pre-opening phase and multiple years rather than
  being scoped to a single year's twelve months.

## Impact

- `Budget_Agent/source_code/input/template/` and `Budget_Agent/source_code/generate_project_budget.py`:
  new per-year/phase sheet generation, replacing today's single hard-coded `2. Budget-Management Fund`/
  `2.2 Common area Fund` fill with a loop over the requested phases.
  `Budget_Agent/source_code/generate_project_output.py` (the analysis generator) needs the equivalent
  extension so both workbooks describe the same project shape, per the existing "both generators must
  run, and must agree" convention (`verification/run_workflow.py`).
- Project intake form / `0. Info`: new fields for years-to-project and pre-opening duration.
- `1. Summary`: column layout changes for a 2+-year project (a 1-year project's layout is unchanged).
- This is a figure-moving change for any project that opts into more than one year or a pre-opening
  phase (a 1-year, no-pre-opening project's figures SHALL be unchanged) — needs the same
  measure-then-Head-of-PM-sign-off gate as other figure-moving changes in this project.
- Given the size, this proposal expects to be broken into staged sub-changes at apply time (see
  design.md's Migration Plan) rather than implemented as one pass.
