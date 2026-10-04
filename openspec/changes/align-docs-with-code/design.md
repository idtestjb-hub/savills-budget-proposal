## Context

The live run is `run.py`, which calls `generate_project_budget.py` and `generate_project_output.py`.
Reading the imports of every module in `source_code/` (not the old README) gives 12 modules the live
run reaches: `run`, `generate_project_budget`, `generate_project_output`, `build_project_input_form`,
`input_labels`, `master_comparables`, `estimate_capex_qty`, `estimate_opex`, `estimate_new_project`,
`fill_curve`, `vn_holidays`, `common_utils_v2`. The other 19 are data-preparation scripts, one-off
studies, or leftovers of the abandoned star-schema ETL (`etl_*.py`). `legacy/README.md` already
records the six modules retired on 2026-10-04.

See proposal.md for why.

## Goals / Non-Goals

**Goals:**
- Each document states only what can be confirmed from the code or the files on disk today.
- A newcomer can tell, from the README alone, which modules run, which prepared the CSVs, and which
  are history.

**Non-Goals:**
- No new documentation beyond these four items; `docs/` is not touched.
- No retirement or movement of any module (a separate backlog item if wanted).
- No rewrite of archived changes or of main specs, even where their boilerplate still says
  "Generation A/B".

## Decisions

**1. README groups modules by role, not by "generation".** Four groups: live pipeline; scripts that
prepared reference data (and what each wrote); one-off studies and backfills; `legacy/`. Alternative:
keep the generation vocabulary and mark A as retired. Rejected: the word stays in old commit messages
and specs but a new reader gains nothing from it.

**2. Each README row is checked against the import graph and the file it writes.** The README says
"checked <date> against the imports" so a later reader knows how current it is.
Alternative: generate the table with a script. Rejected: a line of judgement per row cannot be
generated, and a generator is one more thing to maintain.

**3. Docstrings are rewritten, not just trimmed.** Each keeps the method explanation (the study
logic, the number-locale parsing) because that is valuable; only the false statements about wiring
and "next step" change. The "REVISED" history paragraph in `estimate_capex_qty.py` is kept as
history.

**4. `config.yaml` keeps the two conventions that still help (plain-language proposals; state
currency and unit) and replaces the generation rule.** New rule for specs: say which data files a
change reads or writes and whether any recorded baseline figure moves. New rule for tasks: where a
figure can move, include a before/after measurement on one project and name who signs off. This
changes what future proposals look like, so the wording is reviewed on its own line before it is
written (task 3.1).

**5. `RUNNING.md` corrections are limited to facts re-read from the code** (template file name,
deliverable and analysis sheet counts, the list of files read at run time). Wording and structure
stay.

## Risks / Trade-offs

- The module table can drift again. Mitigation: the README states its check date and method.
- Changing `config.yaml` rules means the `guard-input-file-overwrite` change, written under the old
  rule, carries "Generation A/B" boilerplate in its spec's Purpose. Accepted; archived specs are not
  rewritten.
- A docstring edit is the only change to `.py` files. `verify.py` will confirm nothing else moved.
