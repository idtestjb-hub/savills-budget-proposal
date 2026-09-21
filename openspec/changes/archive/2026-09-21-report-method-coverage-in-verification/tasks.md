## 1. Record the starting point

- [x] 1.1 Capture every figure that must NOT move, since this change adds no write site — verify by reading them from `verification/baselines/baseline.json` and recording them before any code is touched
      Done — see `starting-point.md` in this change's own directory: all 24 `baseline.json` figures,
      all 7 `deliverable_baseline.json` figures, and the 68.7%/31.0% method-fidelity + ~74%/~72%
      coverage figures proposal.md itself recorded on 2026-09-09.
- [x] 1.2 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero
      Done — PASS, 2026-09-17, before any code in this change was touched.

## 2. Build the reference of what real budgets spend

- [x] 2.1 Extract each reference budget's cost codes and Year-1 values — verify by confirming the totals reported for each project reconcile against that budget's own section subtotals
      Done. Both files' extracted leaf totals now reconcile EXACTLY (to floating-point noise,
      ~2e-6 VND) against each budget's own three top-level totals (Revenue + total Operating
      Expense + Tax). Not straightforward: the first attempt (Revenue + Expense only) was off by
      hundreds of millions of VND on both files. Investigated rather than loosened the tolerance —
      found three distinct causes, each confirmed by direct arithmetic before being added as a
      named exception in `verification/method_coverage.py`: (a) a third top-level branch, Tax
      (`D`), was missing from the anchor entirely; (b) two summary rows per file (`RA1`, `ESS9` for
      11D; `ERF10` for Green Skyline) carry no hierarchy-indicator but duplicate the exact sum of
      their own dot-suffixed children (e.g. `RA1` = `RA1.A`+`RA1.T`+...); (c) `ESR` carries a
      hierarchy-indicator despite having no children at all, the same shape as the already-known
      `EM#`/`ES#`/`EE#` contingency codes, and is genuinely a leaf in both files. See
      `method_coverage.py`'s own comments for the exact figures behind each.
- [x] 2.2 Locate each file's code and value columns by finding known codes rather than assuming a layout — verify by confirming a file whose layout is not recognised fails to load rather than loading the wrong columns
      Done — `extract_reference_budget()` scans the configured code column for three sentinel
      codes (`RM.AP`, `EMH1`, `ESS1`) before trusting anything else; `ReferenceLayoutError` if any
      are missing. Verified negatively: temporarily pointed 11D's config at Green Skyline's
      `code_col`/`value_col` (a genuinely wrong layout) and confirmed it raises `ReferenceLayoutError`
      rather than silently extracting garbage, then reverted.
- [x] 2.3 Separate section roll-ups from line items, and justify every exclusion — verify by confirming each excluded code is recorded with a reason, and that the contingency codes are treated as line items rather than as section markers
      Done. `_LEAF_DESPITE_INDICATOR` (`EM#`, `ES#`, `EE#`, `ESR` — shared across both files,
      confirmed identically shaped in both) and each file's own `rollup_despite_no_indicator`
      (11D: `RA1`, `ESS9`; Green Skyline: `ERF10`) each carry an inline comment naming the exact
      figures that confirmed them, per design.md D5's "data with a comment, not a regex."
      Contingency codes (`EM#`/`ES#`/`EE#`) are treated as leaves, not section markers — confirmed
      directly: excluding them was what understated the gap "by about a point" the first time
      (design.md D5's own account), and including them here is what makes 2.1's reconciliation
      land exactly.
- [x] 2.4 Keep each reference figure's provenance — verify by confirming a reader can trace any row back to the workbook and sheet it came from
      Done — every extracted leaf carries `sheet`, `row`, and `item` (the Vietnamese/English item
      name from the adjacent column) alongside its value.
- [x] 2.5 Keep real client figures within the repository's existing handling for real data — verify by confirming the reference table is covered by the same rules as the budgets it derives from, and that the change creates no copy of client data outside them
      Done. Both reference files are read directly from `input/budget_planning/` (real,
      already-gitignored client data) and never copied, cached, or written elsewhere — the module
      re-reads them fresh from that path on every run rather than persisting an extracted copy.
- [x] 2.6 Confirm the extractor read nothing under production paths and wrote nothing there — verify by comparing the production fingerprints before and after running it
      Done — covered by 6.4's own `verify.py` run, which snapshots `run_workflow.py`'s
      `PRODUCTION_FILES` before and after the whole suite including this check, and reported
      "OK all production artefacts byte-identical" (the reference-budget files themselves are
      real client data, but outside `PRODUCTION_FILES`' tracked set on principle — they were also
      separately confirmed unwritten by inspecting `extract_reference_budget()`'s own code, which
      only ever calls `openpyxl.load_workbook(..., data_only=True)`, never `.save()`).

## 3. Record a method verdict for every code the pipeline writes

- [x] 3.1 Record, for each cost code the pipeline writes, the method the costing spec states, the method actually used, and a verdict — verify by confirming every write site has an entry and that each entry carries its reasoning rather than a bare verdict
      Done — `METHOD_VERDICTS` in `method_coverage.py`, all 36 codes, each with `spec_method`
      (from `Costing_Method_Catalogue.csv`'s own `method` column, or an explicit "not recorded"
      note when the catalogue has no entry), `actual_method` (read from the source, not assumed),
      `verdict`, and `reasoning`.
- [x] 3.2 Derive the list of write sites from the code itself rather than restating it — verify by confirming the check reads the pipeline's own row mappings, so a new write site appears without anyone updating a second list
      Done — `write_site_codes()` reads `generate_project_budget.MGMT_FUND_EXPECTED_CODE` and
      `.PRODUCT_REVENUE_EXPECTED_CODE` directly, no second hand-maintained list.
- [x] 3.3 Fail the run when a written code has no verdict — verify by temporarily adding a write site with no entry and confirming the run fails and names that code
      Done — verified directly: temporarily added a fake key/code to a copy of
      `MGMT_FUND_EXPECTED_CODE` in a scratch script and confirmed `check_method_verdicts()` returns
      `ok=False` with the fake code named in `missing`; `check_method_coverage` (checks.py) turns
      this into a `verify.py` FAIL naming the code. Reverted, no change to the real dict.
- [x] 3.4 Fail the run when a verdict exists for a code no longer written — verify by temporarily removing a write site and confirming the run fails and names it
      Done — same technique: temporarily removed one entry from a copy of the dict and confirmed
      `check_method_verdicts()` names it in `orphaned`. Reverted.
- [x] 3.5 Confirm no verdict is inferred at run time — verify by confirming the check reads recorded judgements only, and produces no verdict of its own for an unrecorded code
      Done — `compute_fidelity()` looks up `METHOD_VERDICTS[code]['verdict']` for every code with a
      written value; there is no branch anywhere in this module that computes or guesses a verdict.
      A code missing from the registry raises via `check_method_verdicts()` before fidelity is ever
      computed (3.3), rather than silently defaulting to any verdict.

## 4. Report both measures on every run

- [x] 4.1 Report which codes a reference budget uses that the pipeline does not fill, and what share of that budget's value they represent — verify by running verification and confirming both the count and the share appear
      Done — `verify.py` section 6 prints, per reference project, the unfilled share and the full
      list of unfilled codes. Confirmed live: 11D 18.6% (55 codes), Green Skyline 6.4% (42 codes).
- [x] 4.2 Report each reference project separately rather than averaging them — verify by confirming an office property's coverage is not blended with a residential one into a single figure
      Done, reported as two separate lines (81.4% / 93.6%), never averaged. **Correction to
      design.md's own risk section, found while building this**: both reference files found under
      `input/budget_planning/` today are residential apartment properties (11D: 157 "Căn hộ" units;
      Green Skyline: 1,251 "Apartment" units; 0 office/retail area in either, confirmed directly
      from each file's own Info sheet) — not "one office and one residential" as design.md's Risks
      section states. Not corrected in design.md by this change (a record of the original proposal,
      not rewritten here); flagged in `method_coverage.py`'s own comment so a future reader doesn't
      inherit the stale premise. The task's actual requirement (separate, never averaged) is met
      regardless of property type — two residential-only reference points still should not be
      blended into one number.
- [x] 4.3 Report the share of written cost that matches, partially matches, and does not match the spec's method — verify by confirming the three shares appear and sum to the total written cost
      Done — `compute_fidelity()` returns all three buckets from the same `code_to_value` input;
      `matches['value'] + partial['value'] + mismatch['value'] == total_value` by construction
      (every code lands in exactly one bucket). Confirmed live: matches 99.9%, partial 0.0%,
      mismatch 0.1%.
- [x] 4.4 Name the codes behind a mismatch — verify by confirming a reader can tell which codes make up the mismatching share without reading the source
      Done — each bucket carries its own `codes` list; `verify.py`'s NOTE line names them inline
      (currently: mismatch = `ERM` alone).
- [x] 4.5 Reproduce the measured starting point — verify by confirming the reported fidelity matches the figures recorded in this change's proposal for the current code, and investigating any difference rather than adjusting the expectation
      **Investigated a real, large difference rather than forcing a match — see `METHOD_VERDICTS`'
      own header comment for the full account.** Today's measured fidelity is 99.9% matches / 0.1%
      mismatch, not proposal.md's 2026-09-09 figure of 68.7% / 31.0%. Root-caused, not dismissed:
      proposal.md's entire 31.0% mismatch was `EEE.C`/`EEW.C`/`EED.C` — and
      `cost-energy-from-consumption-and-tariff` was archived the very next day, 2026-09-10,
      rewiring exactly those three codes onto consumption × tariff (confirmed directly against
      `estimate_opex.py`'s own docstring before changing their verdict). Coverage similarly moved
      (was ~74%/~72%, now 81.4%/93.6%) because several new write sites (`ERM`, `EMH4`, `EMA7`,
      `ESC12`, `ESM25`) were added by later changes this session. Both movements are attributable to
      real, already-shipped, already-archived changes — not a bug in this instrumentation, and not
      adjusted to match the stale number.

## 5. Stop the summary overstating

- [x] 5.1 State coverage and method fidelity in the result summary alongside the baseline comparison — verify by reading the final summary of a green run and confirming all three appear
      Done — `verify.py`'s RESULT block states baseline-match, method fidelity %, and both
      coverage %s together, confirmed live.
- [x] 5.2 Confirm the summary does not imply the figures were checked for correctness — verify by reading it as someone who has not used the harness before, and confirming a green run cannot be read as a statement of accuracy
      Done — reworded the PASS line itself ("reproduces its own recorded baseline... NOT asserted
      as correct") and added an explicit closing line ("A green run says the pipeline reproduced
      its own numbers. It does NOT say those numbers are right") rather than relying on the reader
      to infer the distinction from the section header alone.

## 6. Confirm nothing moved

- [x] 6.1 Confirm no tracked figure changed — verify by running `python verification/verify.py` and confirming every figure recorded in 1.1 is unchanged and the baseline was not re-recorded
      Done — `verify.py` sections 3-5 (24 `baseline.json` figures + 7 `deliverable_baseline.json`
      figures) all report OK against the SAME recorded baseline from 1.1; neither baseline file's
      `recorded_at`/`reason` changed.
- [x] 6.2 Confirm no generator, estimator or template behaviour changed — verify by confirming both generated workbooks are byte-comparable in content to a pre-change run apart from any timestamp
      Done, by construction: this change added a new module (`method_coverage.py`) and a new check
      function (`check_method_coverage` in checks.py) plus its call site in `verify.py` — it does
      not import into, or get called from, `generate_project_budget.py` or
      `generate_project_output.py` at all. Confirmed no generator file has any diff.
- [x] 6.3 Confirm the structural checks still pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean under full recalculation
      Done — `verify.py` section 2: sheets/corruption/formula-error checks all OK, 5 errors
      inherited from the blank-template baseline (unrelated to this change), full recalculation
      method (not degraded).
- [x] 6.4 Confirm production data was untouched throughout — verify by comparing the production fingerprints against their recorded values
      Done — `verify.py` section 1: "OK all production artefacts byte-identical", same run that
      exercised the new section 6.

## 7. Documentation

- [x] 7.1 Record what a green run does and does not now assert — verify by confirming `verification/README.md` distinguishes reproducibility, coverage, method fidelity and accuracy, and says which of the four are measured
      Done — new "What a green run does and does not assert" table at the top of the README:
      reproducibility/coverage/fidelity measured every run, accuracy explicitly never measured.
- [x] 7.2 Record how to add a verdict when a new cost line is added — verify by confirming a reader who adds a write site knows what the failing run is asking them to do
      Done — new "Adding a verdict when you add a cost line" section, with the exact dict shape
      and a note that a missing verdict fails the run by design.
- [x] 7.3 Record that a low score does not fail the run, and why no threshold was set — verify by confirming the reasoning and the condition for revisiting it are both written down
      Done — new "Why there is no coverage or fidelity threshold" section, stating the reasoning
      (any threshold today is arbitrary) and the revisit condition (catalogue gains method entries
      for currently-uncovered codes; a ratchet becomes the natural next step).
- [x] 7.4 Record the measured starting point so later movement is meaningful — verify by confirming the coverage and fidelity figures for the current code are captured with their date
      Done — new "Measured starting point (2026-09-17)" section: 99.9%/0.0%/0.1% fidelity,
      81.4%/93.6% coverage, with the investigated explanation for why these differ from
      proposal.md's own 2026-09-09 figures (task 4.5).
- [x] 7.5 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
      Done — new dated amendment note at the top of the file, matching today's established
      pattern, naming this change, the measured figures, and that it's implemented but not yet
      archived.
