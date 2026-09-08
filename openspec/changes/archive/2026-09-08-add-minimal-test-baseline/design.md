## Context

See `proposal.md` — Why, for motivation. The constraints that shape this design are structural, and were verified against the code rather than assumed:

- `main()` in both generators takes **no arguments**. It reads the module-level constant `INPUT_PATH` (`generate_project_budget.py:45`).
- Output destinations are likewise module-level constants: `BUDGET_OUT_DIR`, `ROSTER_FINAL_OUT` (`generate_project_budget.py:53-55`) and `OUTPUT_PATH` (`generate_project_output.py:44`).
- `read_input(path)` **does** accept a path parameter, so reading is already redirectable. Writing is not.
- The two generators are mutually dependent: `generate_project_output.py:32` imports `read_input`, `INPUT_PATH` and `PRODUCT_ROWS` from `generate_project_budget`, which imports back at function level.

The consequence: the workflow cannot currently be pointed at a different input or output location from outside. Since this change must not modify production code, that has to be solved at the verification layer.

## Goals / Non-Goals

**Goals:**
- Run the genuine code path — not a reimplementation of it — against synthetic data.
- Leave production input, reports and deliverables provably untouched.
- Record a numeric baseline that a later change can be measured against.
- Make the difference between a full check and a degraded check visible in the result.

**Non-Goals:**
- Refactoring the generators to accept paths as arguments. That is a real improvement, but it is a change to production code and belongs in its own change.
- Any accuracy judgement. This design proves stability only; see `proposal.md` — Accepted limitations.
- Test coverage of the superseded or path-broken modules.

## Decisions

### D1 — Redirect the path constants at run time rather than changing the modules

The harness overrides `INPUT_PATH`, `BUDGET_OUT_DIR`, `ROSTER_FINAL_OUT` and `OUTPUT_PATH` on the imported modules before invoking the workflow, pointing them at a temporary directory.

*Why:* it is the only option that satisfies both constraints at once — production code is untouched, and production data is never read or written. The generators already write to a temporary location first and copy into place, so redirecting the destination fits how they work rather than fighting it.

*Alternatives considered:*
- **Add path parameters to the generators.** Cleaner long-term and worth doing eventually, but it modifies production code, which this change explicitly excludes.
- **Copy the whole project tree to a sandbox and run there.** Fully isolated and needs no override at all, but `input/` alone is 160 MB and the reference data is larger still; the cost per run would discourage running it.
- **Let it write to the real output locations.** Rejected — it would overwrite the current deliverable and analysis workbooks, which is precisely the failure this change exists to prevent.

*Cost, stated plainly:* the harness depends on those four constant names. If someone renames one, the harness must fail loudly rather than silently write somewhere unexpected — see R1.

### D2 — Synthetic project is realistic in shape, obviously fake in identity

The sample project uses invented scale figures in plausible ranges (floor area, unit counts, parking, amenities) under a clearly fictional name, and contains no real client name.

*Why:* the comparable-matching logic selects on size, so unrealistic figures would exercise an atypical branch and make the baseline unrepresentative. An obviously fake name means a sample deliverable can never be mistaken for a client document.

*Note:* per the decision recorded when this change was scoped, the sample project runs against the **real** comparable reference data. The verification therefore exercises the genuine matching path. No client data is copied into the sample input; the reference data is read where it already lives.

### D3 — Baseline is a stored set of named figures in VND, updated deliberately

Headline figures are extracted from the generated workbooks and compared against stored values. Every figure carries its name and its unit (VND). Updating the baseline is an explicit action requiring a recorded reason.

*Why:* a baseline that can be updated silently is worthless — the first failing run would simply be re-recorded and the regression lost. Requiring a stated reason makes a deliberate change reviewable and an accidental one visible.

*Alternatives considered:* comparing whole files byte-for-byte. Rejected — Excel files differ on every write regardless of content, so it would fail constantly and teach people to ignore it.

### D4 — Figures chosen for the baseline are the ones that carry business meaning

The baseline covers the totals a reviewer would actually check: total operating revenue, total operating expense, the surplus/deficit line, the derived management-fee rate, and the per-category costs (staff, the three service contracts, the four Capex categories, and the utility lines).

*Why:* these are the figures the recovery backlog will move. A baseline over incidental values would pass while a headline number changed.

### D5 — A degraded check is reported, never silently substituted

When full Excel recalculation is unavailable, the harness performs the weaker file-level inspection **and says so in the result**.

*Why:* this exact substitution already happened repeatedly during the audit — Excel automation failed, a weaker check ran in its place, and nothing in the output indicated that the stronger check had not run. A verification tool that quietly reduces its own rigour is worse than none, because it produces false confidence.

### D6 — The unread-dataset inventory is documentation, produced from evidence

The inventory records each dataset that exists but is not read at runtime, with the evidence establishing that. Nothing is connected.

*Why:* connecting unread data changes budget figures. Doing that inside the change that establishes the baseline would mean the baseline captures post-change numbers and loses its value as a "before" reference. Recorded separately, the following change can be measured against it.

## Risks / Trade-offs

- **Harness depends on module-internal constant names** → assert all four exist before overriding; abort with a clear message naming the missing constant if a rename has occurred. Silent fallback to production paths must be impossible.
- **Baseline recorded on an unpinned runtime** → record the interpreter version alongside the baseline, so a cross-machine mismatch is diagnosable rather than mysterious. Dependency pinning is separate work and should follow closely.
- **Baseline can ossify an incorrect number** → accepted and documented. This proves stability, not correctness; several figures are already known to be inaccurate (Capex ~2.2× high, water ~3.3× high, roster ~⅓ low). The baseline records today's behaviour so tomorrow's change is measurable, not because today's behaviour is right.
- **Excel automation is unreliable on this machine** → mitigated by D5 rather than solved. Reliability of Excel automation itself is out of scope.
- **Floating-point comparison** → compare with an explicit tolerance rather than exact equality; the tolerance is an implementation detail (see Open Questions).
- **The two generators must both run** → the harness runs both, which also makes it the first place the documented "run both" rule is enforced automatically rather than by memory.

## Open Questions

These can be answered during implementation without changing the specs, the approach, or the task breakdown:

- The exact numeric tolerance for baseline comparison. Likely exact for integers and a small relative tolerance for derived values.
- Whether the sample deliverable is retained as a fixture for inspection, or discarded after each run.
