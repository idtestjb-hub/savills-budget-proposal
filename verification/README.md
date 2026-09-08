# Verification harness

Runs the real budget pipeline against a synthetic project, checks the workbooks it produces, and
compares the headline figures against a recorded baseline.

It proves **stability, not correctness**. A green run means the pipeline still produces the numbers
it produced last time — not that those numbers are right. Several are known to be wrong; see
`docs/03-risks-and-gaps.md` and `docs/05-decisions.md`.

## What each module does

| Module | Purpose |
|---|---|
| `isolation.py` | Redirects the pipeline's hardcoded paths so a run cannot read or write production data |
| `run_workflow.py` | Runs **both** generators against the sample, and fails if any production file is touched |
| `checks.py` | Structural checks: expected sheets, corruption artifacts, Excel formula errors |
| `baseline.py` | Extracts the headline figures, hand-checks them, records and compares the baseline |
| `verify.py` | The single entry point — runs the workflow once and applies every check |
| `fixtures/Sample_Project_Input.xlsx` | The synthetic project. Obviously fictional, realistic in scale |
| `baselines/baseline.json` | The recorded figures, plus the runtime that produced them |

## Running it

```bash
cd Budget_Agent/source_code
python verification/verify.py      # everything, in one command
```

Or run a stage on its own:

```bash
python verification/checks.py      # structure only
python verification/baseline.py    # figures + baseline comparison only
```

`verify.py` runs the workflow once and hands the same outputs to every check, so it is faster than
running the two separately. All exit `0` on success and non-zero on failure, and none of them
touches production data — `run_workflow.py` verifies that on every run and fails if a live file
changed.

`baseline.py` needs Excel. The analysis workbook stores its headline figures as formulas with no
cached values, so they cannot be read without recalculation. Without Excel there is no numeric
baseline at all — not a weaker one. `checks.py` degrades gracefully instead, and says so in its
output when it does.

---

## Re-baselining

The baseline is deliberately hard to change. A baseline that can be updated silently is worthless:
the first failing run gets re-recorded, and the regression it caught disappears.

### When to re-baseline

Only when a figure moved **because you intended it to move** — a business decision was implemented,
a rate was corrected, a bug was fixed. Never to make a failing check pass.

If a figure moved and you cannot explain why, that is the harness doing its job. Investigate before
touching the baseline.

### The procedure

**1. Run the comparison and read the failure.**

```bash
python verification/baseline.py
```

It names every figure that moved, with its baseline value, its current value and the delta, in VND.

**2. Confirm every change is one you meant to make.** Go line by line. If any figure moved that you
did not expect, stop — a change to one input often moves figures you were not thinking about, and
that is exactly what the baseline is for.

**3. Re-record, with a reason.**

```bash
python verification/baseline.py --record --reason "why these figures moved"
```

The `--reason` is mandatory and the command refuses to run without it. Write it for someone reading
in six months who was not in the room: say what changed and why the new numbers are correct, not
just "updated".

Good: `"D3 implemented: removed the 21.5% employer insurance loading from ESS1/ESS4/ESS16, which are outsourced vendor contracts, not Savills payroll. Staff cost falls accordingly."`

Not good: `"updated baseline"` · `"fixed"` · `"new numbers"`

**4. Confirm the re-record took.** The command prints the stored baseline back, including the
reason, the figure count and the runtime. Re-run once more and confirm it now passes.

**5. Commit the baseline change on its own**, with the same reason in the commit message, so the
change is reviewable as a single diff of `baselines/baseline.json`.

### What is recorded alongside the figures

Every baseline carries the runtime that produced it — Python version, openpyxl version, Excel
version, platform, and the SHA-256 of the sample fixture. This project pins no dependencies and has
two Python versions in evidence, so when a baseline stops reproducing on another machine, this block
is what makes the difference diagnosable rather than mysterious.

When the **sample fixture has changed** since the baseline was recorded, the comparison still lists
every figure that moved — someone who edits the sample needs to see what it did to the numbers — but
it prints a prominent note first, saying the differences follow from the changed input rather than
from a code regression. The run still fails, so a changed fixture can never pass silently.

### Tolerance

| Unit | Rule | Why |
|---|---|---|
| VND | exact, ±1 | Whole currency amounts should reproduce exactly. The smallest figure tracked is ~28 million VND, so ±1 cannot mask anything meaningful — it only absorbs float representation noise from Excel |
| VND/m²/month | exact, ±1 | Same |
| ratio | relative, 1e-9 | Margin and markup are computed by division and carry genuine float error |
