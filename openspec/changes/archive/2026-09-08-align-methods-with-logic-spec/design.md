## Context

See `proposal.md` — Why. Established by reading the spec, the code and the reference data.

- `EXENSIVE LOGIC.xlsx` states a method per code. `ESS4`'s is `m² × unit price × 12` or
  `monthly contract × 12`; `ESS16`'s is `monthly contract × 12` only; `ESS1` allows a headcount
  branch. All three were computed from roster headcount × daily rate.
- `Fact_MasterRateCard.csv`'s Service domain prices everything `VND/position/month` — Security
  17,500,000, Cleaning 8,000,000, Landscape 11,000,000. **There is no per-m² rate anywhere**, so
  `ESS4`'s primary branch cannot be computed.
- `generate_project_output.py`'s Service sheet **already** computes the contract method in its
  column H: `post rate ÷ shift roles × night blend × qty × 12`. It sat beside the roster figure as
  a comparison rather than being used as the cost.
- The two workbooks disagreed by **210,372,000 VND** across the three lines.

## Goals / Non-Goals

**Goals**

- Each of the three codes computed by a method its spec states.
- One figure per code, identical in both workbooks.
- The method and its inputs visible on the output.

**Non-Goals**

- Improving rate accuracy. The citywide rates stay n=1.
- `EMH1`, or the 250 unimplemented codes.
- Restructuring Cost Priority's sections, though three of its "STAFF" rows are now vendor contracts.

## Decisions

### D1 — Use the contract branch for all three, and say why for `ESS4`

A vendor contract is priced as posts × post rate. That is `monthly contract × 12` expressed in the
terms the data actually provides, and it is exactly what the Service sheet already computed.

*Why not the `m²` branch for `ESS4`:* no per-m² rate exists in any reference table. Implementing it
would require inventing one, which is the failure mode this whole project is recovering from. The
spec offers an alternative; the alternative is used and the substitution is stated on the row.

*Alternative considered:* keep the roster basis and argue it approximates a contract. Rejected — it
demonstrably does not: the roster gave 475,500,000 for cleaning against the contract's 288,000,000,
because the roster's per-position daily rates are unrelated to the citywide post price.

### D2 — Point the analysis at the Service sheet's cell, rather than recomputing

Cost Priority's three service categories become `='Service'!H5/H6/H7` instead of sums over the
Staff (Roster) sheet.

*Why:* one calculation, one place. Recomputing the same formula in a second location is how the two
workbooks drifted apart to begin with.

*Cost:* it hardcodes three row numbers. They are deterministic — the Service sheet writes exactly
three categories in a fixed order beneath a header at row 4 — and the reference is commented with
that reasoning. A fourth service category would need this updated, and would fail visibly rather
than silently because the referenced row would hold the wrong label.

### D3 — Fold the supervisory variant into its parent contract

`Cleaning — Supervisory` no longer exists as its own Cost Priority row.

*Why:* a supervisor is part of the cleaning vendor's contract, not a separate engagement. The
contract figure already covers the post. Leaving it as a separate row would double-count.

### D4 — Match the Service sheet's rounding exactly

The blend factor is rounded to 4 decimal places before use, because the Service sheet writes it
into a cell at that precision and multiplies by the rounded value.

*Why:* without this the two workbooks differed by 42,004 VND on Security — small, but it would have
meant "the two agree" was untrue, and a near-miss is harder to reason about than a clean match.

### D5 — Expect the movement before running

`staff_cost_annual` follows the Cost Basis toggle, which holds Security and Cleaning but not
Landscape (Conditional):

```
Security  1,313,648,000 -> 1,294,958,000   =  -18,690,000
Cleaning    323,340,000 ->   288,000,000   =  -35,340,000
                                              -----------
                                              -54,030,000
```

Profit rises by exactly that. Across all categories the Staff TOTAL falls 210,372,000 — the whole
of the previously measured cross-workbook gap. `EMH2` must not move.

### D6 — Add the input `ESM4` needs rather than approximate it from one we have

The spec prices pool chemicals from water **volume**; the form captured pool **area**. Rather than
invent an area-to-volume conversion, the form gained a `Pool Volume (m³)` field.

*Why not derive volume from area:* it needs an average depth, which varies with the pool's profile
and is not recorded anywhere. A guessed depth would put a fabricated multiplier under a real
formula — worse than the flat figure, because it would look derived.

*Why the range midpoint:* the spec states 1–4 kg/m³/month, a 4× span driven by bather load,
backwash frequency and rainfall — none of them captured. 2.5 is the midpoint, and every generated
note carries the full span so the figure is never read as precise.

*Why the fallback survives:* a form filled in before this field existed, or left blank, must still
produce a budget. It gets A&K's flat figure, labelled as a fallback that does not scale, naming the
field that would change that. `0`, blank and non-numeric all mean "unknown" — not "a pool of no
volume".

*Where it lives:* `estimate_opex()`, which both generators already call. Putting it at the
deliverable's write site would have left the analysis on the flat figure — reproducing, on a new
line, exactly the divergence D2 exists to prevent.

### D7 — A hand-check that cannot read its input fails

`read_sample_scale()` read the fixture at fixed addresses. The Product Mix block grew from 5 rows to
9, and five of seven inputs became `0`/`None` without anything failing: the management-fee check's
`input_nfa.get(label) or nfa` fell through to the workbook under test, and the parking check's
`parking < actual` passed trivially at `parking == 0`.

Both now read by label — the same fix `read-input-by-label` applied to the pipeline, which had never
been applied to the harness checking it — and both fail on an unanchored input. The `or` became an
explicit `is not None`, since a real `0` is an input, not a missing one.

*Why this is in this change:* it is where the degradation was found, and it is load-bearing for
every claim this change makes. Two of the "5 independently reconciled" figures were not being
reconciled at all.

## Risks / Trade-offs

- **Less project-specific than what it replaces** → accepted, and stated in the proposal, the
  remarks and the decision record. The roster differentiated a supervisor from a line cleaner; the
  contract does not. Method fidelity was the instruction; rate width is `R-D02`.
- **Hardcoded Service row references** → deterministic and commented; a change to that sheet's
  shape breaks visibly.
- **Three vendor contracts sit in a section headed "STAFF"** → cosmetic, and restructuring the sheet
  is out of scope. Worth revisiting.
- **The rate is n=1 citywide** → unchanged by this work, and now more prominent because it is the
  sole basis rather than a cross-check.
- **`ESM4`'s midpoint is a choice inside a 4× range** → stated on every figure it produces, with the
  span. Narrowing it needs consumption data no project records today.
- **`ESM4` omits acid** → the spec cites ~60 L/year for a 440 m³ pool but prices none of it, so the
  line is understated by an unknown amount. Named on the row rather than filled with a guess.

## Migration Plan

No data migration. Generated output only. Rollback is reverting the code and re-recording the
baseline with a reason.

## Open Questions

- Whether Cost Priority should carry an "Outsourced services" section distinct from "Staff", now
  that three of its staff rows are vendor contracts. Presentational; does not affect these specs,
  the approach or the tasks.
