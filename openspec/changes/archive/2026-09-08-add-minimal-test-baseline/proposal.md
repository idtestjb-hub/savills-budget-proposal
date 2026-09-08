## Why

Today there is no way to tell whether a change to this pipeline has broken something. There are no automated checks anywhere in the codebase, and the only accuracy check ever performed — a manual comparison of generated output against a real historical budget — was done once, by hand, in a spreadsheet that cannot be re-run.

This matters now because the recovery backlog is almost entirely made up of changes that move budget numbers: correcting the management-fee basis, modelling gradual building occupancy, recalibrating cost estimates. Every one of those is currently a gamble. A reviewer cannot confirm that a fix improved a figure without opening spreadsheets and checking by hand.

A second, smaller problem: how to run the project is not written down accurately. The existing `README.md` describes a set of scripts that no longer form the working pipeline, so a person picking this up would follow instructions that do not work.

## What Changes

- **A synthetic sample project** — a fictional building with invented but realistic scale figures, used as the input for verification. Production input is never read or written.
- **A repeatable verification command** that runs the core workflow end to end against that sample project.
- **Structural checks** on the result: the expected sheets exist, the workbooks contain zero Excel formula errors after a full recalculation, and no file-corruption artifacts are present.
- **A recorded numeric baseline** (all figures in VND) captured from the sample run. Verification fails if those figures move unexpectedly on a later run.
- **Written documentation of how the project is actually run today** — the real entry points, in the real order, including the requirement to run both generators.
- **A recorded inventory of datasets that exist but are not read by the pipeline**, with evidence. This is documentation only.

Explicitly **not** in this change, per the request that opened it:

- No business logic is redesigned and no budget rule is altered.
- No new features. In particular, the unread datasets identified above are **documented, not connected** — wiring them in would move budget numbers and is deliberately deferred to a following change, so that its effect can be measured against the baseline this change establishes.
- No dependency versions are added, pinned, or upgraded.
- No production data is modified.
- **No Fact/Dim join keys are touched**, so the Copilot Studio package's live data is unaffected.

## Capabilities

### New Capabilities

- `budget-workflow-verification`: the ability to confirm, on demand and without manual spreadsheet inspection, that the core budget-generation workflow still runs correctly and still produces the same numbers — using synthetic data only.

### Modified Capabilities

None. No existing requirement changes; this change only adds the ability to verify behaviour that already exists.

## Impact

**Added**
- A synthetic sample input workbook, stored separately from production input.
- A verification entry point and its recorded baseline figures.
- Documentation of the real run procedure and of unread datasets.

**Unchanged**
- Every existing pipeline module. This change reads the pipeline; it does not modify it.
- All reference data, including the hand-verified comparables. The sample project is run against the real comparable set, so the verification exercises the genuine code path.
- Dependencies and runtime.

**Accepted limitations, recorded deliberately**

- Because dependency pinning is out of scope, the baseline is captured on an unpinned runtime. Two Python versions are in evidence in this repository, so the baseline may not reproduce identically on a different machine. Pinning is a separate, already-identified piece of work and should follow closely.
- Because the sample project is synthetic, there is no real budget to compare against. Verification therefore proves **stability**, not **accuracy** — it will detect a number silently changing, but it cannot say whether that number was ever right. Accuracy work is separate and depends on decisions not yet made.
- Excel-based verification depends on Excel automation being available on the machine. Where it is not, a weaker file-level check is the fallback, and the difference must be reported rather than hidden.

**Assumption recorded**: sample data and baseline files live alongside the verification entry point inside `source_code/`, not in the shared `input/` or `reports/` folders, so they can never be confused with production data.
