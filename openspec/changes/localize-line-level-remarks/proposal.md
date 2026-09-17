## Why

`apply-guideline-remark-model` (archived 2026-09-14) composed Vietnamese, project-specific narratives
for `1. Summary`'s section totals, but explicitly left the line-level remarks on `2. Budget-Management
Fund`/`2.2 Common area Fund` (column T) untouched, in whatever language the code that computes each
figure happens to write. A side-by-side scan of our generator's output against a real, delivered
project budget ("Ngân sách mẫu dự án mới sẽ Operation năm 1 + năm 2 có giai đoạn tiền khai trương")
found that where both carry a line-level remark for the same code, the real deliverable is Vietnamese,
narrative, and project-specific, while ours — for every code priced by consumption-x-tariff (`EEE.C`
electricity, `EEW.C` water, `EED.C` diesel) — is English methodology-and-provenance prose ("consumption
x tariff, the method Savills' costing spec states for Electricity..."). A deliverable meant for a
Vietnamese PM/client reads as mixed-language and inconsistent in voice between its summary sheet and
its detail sheet.

## What Changes

- Extend Vietnamese remark composition to **every** line-level `T` remark on `2. Budget-Management
  Fund`/`2.2 Common area Fund`, matching the real sample deliverable's convention (100% Vietnamese,
  no English carve-out for any row). A scan of the current generated deliverable found 50 line-level
  remarks whose text opens in English, spanning two kinds — both in scope:
  - **Computed cost/revenue narratives** (~24 codes: `RM.AP`, `RM.SH`, `RM.0A`, `RP1`, `RP2`, `EMH2`,
    `EMA7`, `EMA15`, `ESC12`, `ESS1`, `ESS4`, `ESS16`, `ESM2`, `ESM3`, `ESM4`, `ESM5`, `ESM8`, `ESM25`,
    `EN1`–`EN4`, `EEW.C`, `EEE.C`, `EED.C`, `RO2a`) — a figure the pipeline computed, explained in
    English methodology prose.
  - **Flagged-zero / no-method reasoning** (~26 codes: `RP3`, `EMH1`, `EMH3`, `EMB1`, `EMB4`, `EMO2`,
    `EMO6`, `EM#`, `ESC1`, `ESC2`, `ESC4`, `ESC5`, `ESI1`, `ESI2`, `ESM6`, `ESM7`, `ESM9`, `ESM10`,
    `ESM12`, `ESM13`, `ESR`, `ES#`, `EE#`, `ERCS1`, and siblings) — English audit-trail text (often
    citing `Costing_Method_Catalogue.csv` by filename) explaining why a code was left at zero.
- No source-code-filename citations in the client-facing translated text — where a flagged-zero remark
  today names `Costing_Method_Catalogue.csv` or another internal artifact, the Vietnamese version SHALL
  describe the reason in plain terms (e.g. "chưa có cơ sở định giá cho hạng mục này") without naming
  the internal file; the internal citation MAY be kept in a code comment for engineering reference, but
  not in the cell text a client reads.
- No figure or zero/non-zero status changes for any code — this is a wording-only change. The VAT
  sentence continues to be appended exactly as today.
- This is a content-authoring task at the same scale as the original summary-level narrative work
  (docs/11/12/13), not a mechanical translation — each of the ~50 templates needs Vietnamese wording
  reviewed for correctness the same way the original change's Wayne Tower narrative review worked.
- Update `deliverable-remarks`'s "composed summary narratives are Vietnamese" requirement, which today
  explicitly carves out line-level remarks as out-of-scope-and-may-stay-English; that carve-out is
  removed entirely (not narrowed) — every line-level remark this pipeline writes SHALL be Vietnamese.
- Extend `check_remark_content` (verify.py's remark-content check) to assert Vietnamese content on every
  non-blank line-level remark, the same way it already asserts it on `1. Summary`'s narratives.

## Capabilities

### Modified Capabilities
- `deliverable-remarks`: the "existing line-level remarks... remain in their existing language" carve-out
  is narrowed — line-level remarks for pipeline-computed codes (starting with the three
  consumption-x-tariff OPEX codes) must now also be Vietnamese; the verification requirement gains the
  matching check.

## Impact

- `Budget_Agent/source_code/generate_project_budget.py`: `_opex_remark()` and its three
  consumption-x-tariff branches (`EEE.C`, `EEW.C`, `EED.C`); no change to the figures it computes, only
  the remark string it returns.
- `Budget_Agent/source_code/verification/checks.py`: `check_remark_content`, extended to cover the
  newly-composed line-level remarks.
- Display-only: no Fact/Dim table, join key, or Copilot Studio-facing data changes. No budgeted figure
  moves; no baseline re-record required.
