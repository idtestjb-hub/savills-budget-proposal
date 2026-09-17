## Context

See `proposal.md` and `docs/11-guideline-remark-model.md`. Grounding facts:

- `1. Summary` column K, today: `K16/K17` are literal Vietnamese text the template ships; `K30/K38/
  K39/K40/K42` are `='2. Budget-Management Fund'!T<row>` (one line's remark); `K49/K51/K52/K53` pull
  `!AO<row>`; the rest are blank. `_normalise_all_remark_columns()` already reformats every Remarks
  column after the fills (text format, wrap, sized rows).
- The pipeline knows exactly which fund-sheet rows it filled — `MGMT_FUND_ROWS`,
  `PRODUCT_REVENUE_ROWS`, `COMMON_AREA_FUND_ROWS` — and with what value (it computes each before
  writing). It does **not** need to read column G back (a formula with no cached value).
- The budget year is `build_budget(project, demand, year)`'s `year` argument.
- **`2. Budget-Management Fund!F7`** holds the VAT switch (`E7` = "Mô hình tài chính:"; data-validation
  list `KHOÁN` / `KHÔNG KHOÁN` / `THU HỘ CHI HỘ`; ships `THU HỘ CHI HỘ`). `KHOÁN` = excl-VAT
  throughout; `KHÔNG KHOÁN` / `THU HỘ CHI HỘ` = incl-VAT throughout. (Corrected during apply
  2026-09-10 — the scaffold said `0. Info!F7`, but that cell is `=SUBTOTAL(9,F8:F12)`, a parking-slot
  count; the switch has always been on the fund sheet. `2. Budget-Management Fund!Y4` carries a
  redundant "(Excluding/Including VAT)" label.) The pipeline already opens `2. Budget-Management
  Fund` and writes its `AH5`/`AL5`.
- `Costing_Method_Catalogue.csv` is `#`-comment lines + a 13-column CSV keyed on `code`;
  `remark_components` is a free-text column already populated for 61 of 67 codes.
- `verify.py` runs COM checks (`check_revenue_agreement` 5b, `check_benchmark_reconciles` 5c, and
  the pending `check_summary_reconciles` 5d from `reconcile-summary-with-detail-sheets`).

## Goals / Non-Goals

**Goals**

- `1. Summary` PART-1 non-zero totals each carry a composed, bilingual, project-specific narrative.
- One VAT-treatment sentence, applied consistently at both remark levels, keyed on `0. Info!F7`.
- The catalogue holds the remark rules (line components + summary recipes + the VAT rule) so code
  and verification read one authority.
- `verify.py` fails on a missing narrative, an unlisted funded child, a missing recipe part, or a
  missing VAT sentence.

**Non-Goals**

- Translating the existing English line-level `T` remarks to bilingual — only the VAT sentence is
  added there.
- Any figure change — this is display-only; no baseline moves.
- Multi-year / pre-opening narrative variants (Change E).
- The `RO2a` / `EMH2` figure reconciliation (`reconcile-summary-with-detail-sheets`).

## Decisions

### D1 — Compose K as plain text at generation time, from what the pipeline wrote

A new `_compose_summary_narratives(wb, project, year, written)` runs in `build_budget()` after the
fund / common-area / staff fills and **before** `_normalise_all_remark_columns()`. `written` is the
`{code: (row, value, item_name)}` map the pipeline already builds as it fills each line. For each
PART-1 `1. Summary` row with a non-zero total, it writes a plain-text bilingual narrative into the
Remarks cell (column K), overwriting a template pull or blank.

- **Why plain text, not a formula:** the narrative is composed from `0. Info`, the fill curve and
  the written-line set — none of which is a single cell. A formula cannot express *"list every child
  line that has a figure"*.
- **Why before the normalise sweep:** so the sweep sizes the (now much taller) K rows.
- `K16`/`K17` (`RA`/`RR`, always zero here) keep the template's own Vietnamese advertising-law text.

### D2 — Two narrative shapes: recipe-driven and roll-up

- **Recipe-driven** (`RM`, `RPa`, `EMH`, `ESC`, security, cleaning, `ESI`, `EN`, `EEW`, `EEE`,
  `EED`): a fill-in-the-blanks bilingual template per code, held in `generate_project_budget.py` as
  a small module dict. Placeholders (`{area_apt}`, `{rate_apt}`, `{kwh_month}`, `{tariff}`,
  `{tariff_cite}`, `{roles}` …) are filled from `0. Info`, `estimate_opex()` output, `fill_curve`,
  and the roster. The catalogue records **which parts** each recipe must contain (D4); the code
  holds the **wording**.
- **Roll-up** (`RO`, `EMA`, `EMB`, `ESM`, `ESA`+`ESL`, `ER`, other-service): the narrative is
  `"Dự ước bao gồm: <item name>, <item name>, … / Estimate includes: …"` over exactly the child
  codes in `written` that fall under that section, plus any fixed sentence the catalogue names for
  the section (e.g. the `ESA`/`ESL` Housing-Law sentence).
- A total with neither a recipe nor children with figures, but non-zero (rare), gets a minimal
  *"See the '2. Budget-Management Fund' detail"* line.

### D3 — One VAT-sentence helper

`_vat_sentence(wb, year) -> str` reads `2. Budget-Management Fund!F7`; returns `""` when it is the
exclusive-of-VAT option (`KHOÁN`), else the bilingual sentence with `year` substituted (both the
Vietnamese and English forms from the catalogue's recorded wording). An unrecognised or blank F7 is
treated as inclusive (the form ships `THU HỘ CHI HỘ` and its `Y4`/`1. Summary!F7` both say
"Including VAT"). Called by:

- `_write_remark()` — appends it to every line-level remark it writes (the only bilingual touch on
  the `T` column in this change);
- `_opex_remark()` — appends it;
- `_compose_summary_narratives()` — appends it to each narrative.

The sentence text and the governing cell come from the catalogue (D4), not hard-coded.

### D4 — Catalogue carries the rules; code carries the wording

`Costing_Method_Catalogue.csv` gains:

- `remark_components` extended to every `AI GUIDELINE`-instructed code (~55) — transcribed from the
  guideline column, as a `;`-separated component list, same format as the 61 existing.
- New rows for the 19 summary recipes, `code` = the `1. Summary` code (e.g. `SUM.RM`, or reuse the
  bare code with `section = summary-narrative`), `remark_components` = the ordered parts,
  `method_detail` = the input source for each part, `remark_components` fixed sentences quoted
  verbatim in a new `fixed_sentence` column.
- One row `VAT.RULE` (or a `# ` header block promoted to a real row) holding the VAT sentence
  (VN + EN) and `inputs = 2. Budget-Management Fund!F7` (the "Mô hình tài chính" switch).

The recipe *wording templates* (with placeholders) stay in `generate_project_budget.py` — they are
formatting, not method. The catalogue is the check's authority for *what must be present*.

### D5 — `check_remark_content` (verify.py §5d)

New `verification/checks.py` function. For the generated deliverable:

1. determine the non-zero PART-1 `1. Summary` totals — from the same written-leaf set the composer
   used (`_collect_written`), which is the composer's own contract: compose for everything it funded;
2. assert each non-zero PART-1 total's K cell is a composed narrative (not blank, not a `=` pull);
3. recipe rows — assert each part the catalogue recipe lists is present, via a small anchor-token
   table in `checks.py` (presence of parts, not phrasing — the wording is the Head of PM's to
   review); aggregate rows — assert every `written` child's item name appears; row 34 — assert the
   fixed Điều 150 sentence;
4. if `2. Budget-Management Fund!F7` is inclusive-of-VAT, assert the VAT sentence is in every
   non-empty composed K cell and in a sample of `T` cells the pipeline wrote;
5. assert each composed K carries a Vietnamese passage and an English passage.

**openpyxl, not COM** (revised during apply): every cell the check reads — the composed K text, the
line `T` remarks, the fund leaves' C/F/H:S/Y/Z — is a literal the pipeline wrote, so Excel
evaluation adds nothing and costs a ~60–90 s round-trip plus an Excel dependency. A broken
`1. Summary` VLOOKUP that zeroes a funded row is a *figure* fault, already owned by
`check_summary_reconciles` (the sibling `reconcile-summary-with-detail-sheets` change), not by a
remark-content check.

Returns `(ok, rows, differences, notes)`; wired into `verify.py` as §5d (the next section after
5c — `reconcile-summary-with-detail-sheets` also plans a §5d `check_summary_reconciles`; whichever
lands second renumbers). No baseline recorded — pure content assertions.

## Risks / Trade-offs

- **[The Vietnamese template wording is wrong or unnatural]** → the templates are reviewed by the
  Head of PM against a real project's composed output (tasks §5); they live in one dict, easy to
  revise; the check enforces *presence of parts*, not exact phrasing.
- **[A recipe part has no data for some project]** (e.g. no nursery) → the template omits that
  clause cleanly (same pattern as the `0. Info` per-product loop); the check only requires parts
  that apply.
- **[K rows become very tall]** → `_normalise_all_remark_columns` already caps row height and wraps;
  the narratives are a few sentences, not essays.
- **[Catalogue schema churn]** → additive columns/rows only; the existing 13 columns and 67 rows are
  untouched; `check_catalogue_drift.py` (from the adopt-guideline change) still passes on the
  originals.
- **[Double VAT sentence if a remark already has one]** → `_vat_sentence` output is a fixed string;
  callers append only if it is not already a substring.

## Migration Plan

Additive, display-only. Deploy = ship the code + the extended catalogue; the next `run.py` writes
the narratives. No baseline re-record. `verify.py` gains §5e; expect it to pass once the composer
and catalogue are in place. Rollback = revert the code and the catalogue rows; `verify.py` §5e is
removed with it. Manual spot-check (tasks §5): generate for one real project, read every composed
`1. Summary` narrative aloud, confirm each states the right area/rate/consumption/child-list for
that project and reads correctly in both languages.

## Open Questions

- Whether the 19 summary recipes get their own `code` values (`SUM.<code>`) or reuse the bare code
  with a `section` discriminator. Deferrable — does not change the specs, the composer, or the
  check; only the catalogue's row layout.
