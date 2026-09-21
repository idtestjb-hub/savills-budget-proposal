## Why

On 2026-09-09 a manual comparison against two real project budgets found that **31.0% of the cost
the deliverable carries is computed by a method the costing spec does not state**, and that **~26%
of what a real project actually spends is on lines the pipeline leaves blank entirely**.

Both facts had been true for months. Neither was known. `verify.py` was green throughout.

That is not a failure of the harness so much as a gap in what it was built to do. It answers one
question well — *did the numbers change since last time?* — and it answers it under full Excel
recalculation with a real baseline. But three other questions have never been asked by anything:

| Question | Asked by | Answer today |
|---|---|---|
| Did the numbers change? | `verify.py` | measured every run |
| Do we fill the line at all? | nobody | ~74% of real spend |
| Do we use the method the spec states? | nobody | 68.7% of what we write |
| Is the number right? | nobody | known wrong in places |

A green run currently means "the pipeline reproduced its own last numbers". It is routinely read as
"the pipeline is fine". The distance between those two readings is where this finding lived.

The existing spec already requires that **verification report its own strength honestly**. A harness
that measures reproducibility and stays silent about coverage and method invites exactly the
over-reading that happened here.

## What Changes

**Verification reports coverage and method fidelity alongside the baseline comparison**, as figures
that update on every run rather than facts discovered by hand every few months.

**Coverage** — of the cost codes a real reference budget uses, which does the pipeline fill, and what
share of that budget's value do the filled ones represent. Measured against reference budgets held
for the purpose, not against the pipeline's own output.

**Method fidelity** — for each code the pipeline fills, whether the method it uses is one the costing
spec states for that code. The verdict per code is a recorded judgement with its reasoning, not
something inferred at run time; what the harness does is hold that record against the code's actual
write sites and report the totals.

**A code that gains or loses a write site without a verdict is a failure.** That is what makes the
record stay true: adding a cost line without recording how it was derived, or silently changing a
derivation, breaks the run rather than quietly ageing the report.

**The summary line stops overstating.** A green run currently ends with a line about figures matching
and hand-checks passing. It gains coverage and method fidelity, so the headline a reader takes away
matches what was actually verified.

Deliberately **not** in scope:

- **Changing any figure, method or cost code.** This change measures; it fixes nothing. The energy
  codes stay mismatched until `cost-energy-from-consumption-and-tariff` moves them.
- **Failing a run for low coverage or low fidelity.** Thresholds would be arbitrary today and would
  either block work or be ignored. The numbers are reported; a *missing verdict* is what fails.
- **Judging accuracy.** Whether a figure is right is not decidable from the spec or the template, and
  pretending otherwise would be a third false comfort.
- Extending the reference set beyond the budgets already held.

## Capabilities

### New Capabilities

<!-- None. This extends what budget-workflow-verification already requires of itself. -->

### Modified Capabilities

- `budget-workflow-verification`: the requirement that verification report its own strength honestly
  is extended from *which checking method ran* to *what proportion of the work was checked at all* —
  coverage against real reference budgets, and method fidelity against the costing spec, reported on
  every run, with a missing verdict treated as a failure.

## Impact

**Code**

- `verification/` — a new module holding the per-code method verdicts and the coverage comparison,
  plus reporting wired into the existing single entry point.
- No change to either generator, to `estimate_opex.py`, or to any figure.

**Data**

- A reference table of what real budgets use per cost code, derived from budgets already held under
  `input/`. Read-only against those files. **Generation A and B tables are untouched and no Fact/Dim
  join key changes**, so the Copilot Studio package's live data is unaffected.
- Reference figures are real project spend. They stay inside the repository's existing confidential
  handling — the reference table records codes and amounts, and is not published anywhere the source
  budgets are not.

**Figures**

- **None move.** This change adds no write site and alters no calculation. If any tracked figure
  moves, something is wrong with the change rather than with the figure.

**Not affected**

- No dependency changes. No production data changes. No template changes.
