## Context

See `proposal.md` — Why. Established by running the comparison by hand on 2026-09-09.

- The template's Management Fund sheet carries the cost code in column `Y` and its name in `Z`. Every
  row the pipeline writes is therefore identifiable by code, and `MGMT_FUND_ROWS` plus
  `PRODUCT_REVENUE_ROWS` already name every write site.
- Real budgets use the same code system, so comparison is exact rather than fuzzy. 11D Thi Sách puts
  codes in column `F`; Green Skyline puts them in `Z` like the template. Layout differs per file.
- The measured result: 68.7% of written cost matches the spec's method, 31.0% does not, and the
  31.0% is entirely `EEE.C`, `EEW.C` and `EED.C`. Coverage is ~74% of 11D's spend, ~72% of Green
  Skyline's.
- `verify.py` is a single entry point that already runs the workflow once and applies every check.

## Goals / Non-Goals

**Goals**

- Coverage and method fidelity reported on every run.
- A verdict that cannot silently go stale when a derivation changes.
- A summary line that describes what was checked and no more.

**Non-Goals**

- Changing any figure, method or cost code.
- Failing on a low score. Only a *missing* verdict fails.
- Judging accuracy.
- Widening the reference set beyond budgets already held.

## Decisions

### D1 — Method verdicts are a recorded judgement, not a run-time inference

Each code the pipeline writes gets a recorded verdict — matches, partial, or mismatch — with the
spec's stated formula, the method actually used, and the reasoning.

*Why not infer it:* deciding whether "A&K's VND/m² cost ratio" satisfies "projected annual kWh ×
updated tariff" is a reading of two prose descriptions. No parser settles that, and a parser that
appeared to would be the most dangerous outcome available — a confident wrong number where there is
currently an honest gap. The judgement is human; the harness's job is to hold it against reality and
report the totals.

*Cost, accepted:* the verdicts need maintaining. D2 is what makes that non-optional.

### D2 — A write site with no verdict fails the run

The failure mode for a recorded judgement is silent ageing: someone adds a cost line, or changes how
one is derived, and the report keeps quoting a percentage that no longer describes the code.

So the harness cross-checks the verdict list against the actual write sites. A code written with no
verdict fails. A verdict for a code no longer written fails. Either way it names the code.

*Why this is the load-bearing decision:* without it this change produces a number that is true today
and decays. With it, the only way to add a cost line is to say how it was derived — which is the
behaviour worth having, more than the percentage itself.

*What it does not catch:* a derivation changed in a way that keeps the same write site and should
have flipped the verdict. The verdict carries the method it describes, so a reviewer can see the
mismatch, but nothing detects it automatically. Stated rather than papered over.

### D3 — Report the numbers; fail only on a missing verdict

No threshold on coverage or fidelity.

*Why:* any threshold today is arbitrary. Set above the current score it blocks all work; set below,
it is noise that gets ignored, and an ignored check is worse than none because it still reads as
assurance. The numbers move when work lands, and a reviewer can see the direction.

*Revisit when:* the energy change lands and fidelity rises. A ratchet — never go below the last
recorded score — is the natural successor, and it needs a stable score to ratchet from.

### D4 — Coverage is measured against real budgets, never against the pipeline's own output

The reference is what real projects actually spend, extracted per code from budgets already held.

*Why this matters more than it sounds:* the hand-checks in `baseline.py` degraded precisely because
one of them fell back to reading its expectation from the workbook under test. A coverage check that
measured the pipeline against its own template would report 100% and mean nothing. The reference has
to come from outside.

*Layout differences are per-file:* each reference budget needs its own code and value column
recorded. Discovered by locating known codes rather than assumed, so a differently-shaped file fails
to load rather than loading wrong.

### D5 — Roll-ups are excluded, and getting that wrong is easy

Section headers (`EM`, `ES`, `ESS`, `EE`, …) carry subtotals. Counting them as line items
double-counts.

*A caution from doing this by hand:* the contingency codes `EM#`, `ES#` and `EE#` look like section
markers and are real leaf items — the first pass excluded them and understated the gap by about a
point. The exclusion list is data with a comment, not a regex, and any code excluded should be
justified.

### D6 — Reference figures are real client spend and stay handled as such

The reference table holds real project cost figures per code.

*Why it is stated here:* the repository's rule is that real data stays on SharePoint and is not
pushed to Git. This table is derived from real budgets and inherits that handling — codes and
amounts recorded for the harness, not published anywhere the source budgets are not. The change
should not create a new copy of client data in a place the existing rules did not anticipate.

## Risks / Trade-offs

- **A percentage invites goal-seeking** → someone could raise fidelity by recording a generous
  verdict. Mitigated only by the verdict carrying its reasoning, which makes a generous one visible
  to a reviewer. Not eliminated.
- **Verdicts age** → D2 catches added and removed write sites, not silently altered ones.
- **Two reference projects, one office and one residential** → a narrow reference set, and the
  pipeline only supports residential. Coverage against an office building is indicative, not a
  target. Report both separately rather than averaging them into one misleading figure.
- **More output on a green run** → the summary gets longer. Worth it: the current one-line summary is
  what allowed "green" to be read as "fine".

## Migration Plan

Additive. No figure changes, no generator changes. Rollback is removing the module and its reporting
call; the baseline and structural checks are untouched either way.

## Open Questions

- Whether to extend the reference set to the other real budgets held under `input/`. More reference
  projects give a better coverage picture; each needs its own layout recorded.
- Whether fidelity should later ratchet (D3). Natural once the energy change lands.
- Whether coverage should eventually distinguish "no rate data exists" from "not implemented" — the
  gap analysis found both, and they are very different backlogs.
