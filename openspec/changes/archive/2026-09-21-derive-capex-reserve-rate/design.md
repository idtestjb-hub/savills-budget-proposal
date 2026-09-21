## Context

See `proposal.md` — Why. Read from the code and the source budgets, not assumed.

- `CAPEX_RESERVE_RATE = 0.10` sits at `generate_project_output.py:2356` with **twelve** use sites
  across the Owner Operating Position and Savills Fee Position sheets — six that multiply a cell by
  it, six that quote it in prose.
- Every use is `Year 1 full, Years 2-4 at the reserve rate`. The drop year is not parameterised.
- In the source budgets the later-year Capex cell is `=$F$219` — a reference to a manually entered
  column. **There is no formula to copy**; the rates below are implied ratios between two
  independently typed numbers.
- Reading `EN1`–`EN3` from the four real budgets that carry a later year:

| Project | Y1 Capex | Later year | Months | Implied |
|---|---|---|---|---|
| Parking Building | 208,533,972 | 17,377,831 | 12 | 8.333% |
| Green Skyline | 318,989,410 | 36,918,094 | 12 (stabilised) | 11.573% |
| Lumi Prestige & Elite | 421,854,831 | 35,154,569 | 9 | 8.333% |
| Lumi Signature | 510,944,646 | 42,578,720 | 8 | 8.333% |

Three of the four write **exactly `Year 1 ÷ 12`** regardless of the year's length. Green Skyline
applies a distinct `0.11573` uniformly across all three categories.

**Green Skyline's Year 2 is a full repeat of Year 1 × 1.030** — the drop happens in Year 3.

## Goals / Non-Goals

**Goals**

- The rate comes from data and updates as projects are added.
- The output shows `n`, the range and the projects behind it.
- The drop year is an input.
- Capex is never scaled by occupancy.

**Non-Goals**

- Correcting Savills' logic spec. Recording the contradiction is enough.
- Re-deriving Capex quantities (the ~2.2× problem) — different module, different change.
- Implementing the fill-up ramp. This change only records that Capex must be excluded from it.

## Decisions

### D1 — Extract to a reference table, mirroring how comparables already work

A `rescan_*`-style extractor reads the real budgets once and writes one row per project: project,
Year-1 Capex, later-year Capex, the later year's length in months, and which sheet each came from.

*Why:* it matches the pattern `master_comparables.py` and `Fact_Capex_Rescanned.csv` already use —
extract once, read at run time, cite in the output. It also means the extraction is reviewable as
data rather than buried in a script that runs on every budget.

*Alternatives considered:*

- **Read the source budgets at run time.** They are 138 MB, need repair before openpyxl can open
  them, and take minutes. Every budget run would pay that cost.
- **Hardcode the four observations.** Cheaper today, but it is the same failure being fixed — a
  number in the code that nobody can trace or update.

### D2 — Compute the mean of the annualised rates, and report the spread

The rate is the mean of each project's annualised implied rate. `n`, the min and the max are
reported alongside it wherever the rate appears.

*Why:* with four observations, a mean without a range is misleading. A reader who sees
`10.9% (n=4, range 8.3%–12.5%)` can judge it; one who sees `10.9%` cannot.

*The ambiguity, stated rather than resolved:* the 8- and 9-month figures are `Year 1 ÷ 12` written
into a short year. Read as a pro-rated annual rate they annualise to 12.5% and 11.1%; read literally
they are 8.33%. The mean is **10.9%** or **9.1%** depending on which. The extractor SHALL record the
period length so both readings stay available, and the estimator SHALL state which it used.

### D3 — The drop year is an input with an evidenced default

A new intake field. Default: the year most reference projects use, which is Year 2 — three of four.

*Why:* Green Skyline shows the drop year genuinely varies, and getting it wrong costs ~290 million
VND on that shape of project, more than the rate error this change is nominally about. A default
that is stated and evidenced is honest; a hardcoded assumption is not.

*Note:* adding an intake field is now safe because `read_input()` finds fields by label rather than
by row (`read-input-by-label`). Before that change this would have shifted every row below it.

### D4 — Capex is excluded from any occupancy ramp

Recorded here as a requirement so that B5 cannot quietly apply the fill-up curve to Capex.

*Evidence:* Green Skyline's own 25% / 50% / 75% / 100% fill scenarios carry Capex of
34,798,845 / 34,798,845 / 35,842,810 / 36,918,094 — a 6% spread across a 4× change in occupancy.
Equipment is bought regardless of how full the building is.

### D5 — Expect the movement before running

Year-1 figures do **not** move: the reserve applies to Years 2–4. So `total_profit_value`, `margin`,
`markup`, `staff_cost_annual` and every `capex_*` figure in the baseline should hold — they are all
Year-1 or category figures.

What moves is the **Years 2–4 rows** on the two position sheets, which the baseline does not
currently track. **If a tracked figure moves, this change has reached further than intended.**

*A gap this exposes:* as with D2, the baseline does not watch what this change alters. Extending it
to cover the multi-year tables is worth doing, and is not in this change's scope.

## Risks / Trade-offs

- **A four-project mean is presented as authoritative** → `n` and the range travel with the rate
  everywhere it appears, and the thin sample is disclosed rather than hidden.
- **The short-year ambiguity is resolved silently** → the extractor records period length; the
  estimator states which reading it used.
- **A tracked baseline figure moves** → that would mean the change reached Year-1 figures, which it
  must not. A task asserts they are unchanged.
- **The extractor is run once and then rots** → it writes its source files and extraction date into
  the table, so a stale table is visible rather than assumed current.
- **Twelve use sites, six of them prose** → a task checks the generated notes quote the derived rate
  and not a stale hardcoded one.

## Migration Plan

The new reference table is generated by the extractor and committed alongside the code, as the other
reference tables are. No existing data changes.

Rollback is reverting the code; the table can stay, unread.

## Open Questions

- Whether the reserve should be expressed against **initial Capex** or against a depreciating asset
  base. Every observed project uses initial Capex, so that is what this implements. Revisiting it
  would need a policy answer from the PM, and does not change these specs or tasks.
