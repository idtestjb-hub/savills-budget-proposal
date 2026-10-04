## Why

Four pieces of written guidance describe a pipeline that no longer exists, and each one misleads a
reader who trusts it:

- `README.md` (marked "Stale index") presents "Generation A" and "Generation B" and a "suggested run
  order" that starts at `cell_scan.py`, which was retired to `legacy/` on 2026-10-04. Of the 12
  modules in `source_code/` that the live run imports, the README lists one (`common_utils_v2.py`);
  it omits `run.py`, both generators, `master_comparables.py` and the rest.
- The `estimate_capex_qty.py` docstring says the function is "not wired into
  generate_project_output.py yet" and the Capex sheet "still ships Qty blank on purpose". Both
  generators import it today (`generate_project_output.py:37`, `generate_project_budget.py:45`).
- The `transform_master_list.py` docstring says `generate_project_output.py` and
  `master_comparables.py` "are not yet wired to this". `master_comparables.py` documents that it
  reads the Master List output, and the live run draws its comparables from it.
- `openspec/config.yaml` tells every future proposal that two parallel pipelines "exist by design",
  that the Copilot Studio package is live, and points to `docs/Fact_Dim_Master_Mapping.md`, which
  does not exist. Its `rules` make every new spec declare a "generation" that is no longer a real
  distinction.

`RUNNING.md` is the accurate guide, but a few of its figures also drifted (template file name,
sheet counts, the list of files the run reads); those are corrected here too.

## What Changes

- Rewrite `source_code/README.md` as a short module map for the code as it is: the live pipeline
  (what `run.py` reaches), the data-preparation scripts that produced the CSVs the pipeline reads,
  the one-off study scripts, and `legacy/`. It points to `RUNNING.md` for how to run.
- Correct the two docstrings so each states what the module does now and who calls it.
- Rewrite the `context` and `rules` in `openspec/config.yaml` to describe the current pipeline and
  the checks that actually matter (which data files a change reads or writes, whether a recorded
  baseline figure moves, how a PM would review it). The existing archived changes and main specs are
  not edited.
- Correct the figures in `RUNNING.md` that no longer match the code (found by re-reading it against
  `generate_project_budget.py`).
- No code behaviour changes. No figure moves. No baseline is re-recorded.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- (none) No requirement changes, so the change sets `skip_specs: true`.

## Impact

- `README.md`, `RUNNING.md`, `openspec/config.yaml`, and the leading docstrings of
  `estimate_capex_qty.py` and `transform_master_list.py`. Docstring edits touch comments only; the
  modules' code is not changed.
- Future proposals are drafted against the new `config.yaml`; it changes the boilerplate they carry.
- `verify.py` is run at the end to show nothing else moved.
