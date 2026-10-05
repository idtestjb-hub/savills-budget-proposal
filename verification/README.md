# Verification harness

Runs the real budget pipeline against a synthetic project, checks the workbooks it produces, and
compares the headline figures against a recorded baseline.

## What a green run does and does not assert

Four different questions could be asked of this pipeline. A green run answers exactly two of them,
and says so in its own summary line (change `report-method-coverage-in-verification`, 2026-09-17):

| Question | Measured? | By what |
|---|---|---|
| **Reproducibility** — did the numbers change since last time? | Yes, every run | `baseline.py` / `verify.py` sections 3-5, full Excel recalculation |
| **Coverage** — do we fill the line at all? | Yes, every run | `method_coverage.py` / `verify.py` section 6, against real reference budgets |
| **Method fidelity** — do we use the method the costing spec states? | Yes, every run | Same section, against a recorded human verdict per code |
| **Accuracy** — is the number actually right? | **No, never** | Not decidable from the spec or the template; several tracked figures are already known to be wrong — see `docs/03-risks-and-gaps.md` and `docs/05-decisions.md` |

A green run means: the pipeline reproduced its own last numbers, fills a measured share of what a
real project actually spends, and uses the spec-stated method for a measured share of what it
writes. It does **not** mean the figures are correct — before 2026-09-17 the summary line did not
distinguish these, and a green run was read as "the pipeline is fine" more often than the evidence
supported.

## What each module does

| Module | Purpose |
|---|---|
| `isolation.py` | Redirects the pipeline's hardcoded paths so a run cannot read or write production data |
| `run_workflow.py` | Runs **both** generators against the sample, and fails if any production file is touched |
| `checks.py` | Structural checks, numeric reconciliation checks, the remark-content check (`check_remark_content`, with a whole-workbook scan for internal wording, `scan_internal_wording`), coverage/fidelity (`check_method_coverage`), and the input-form guard (`check_input_form_guard`, `verify.py` section 7) |
| `method_coverage.py` | Reference-budget extraction, the per-code method-verdict registry, and the coverage/fidelity computations |
| `baseline.py` | Extracts the headline figures, hand-checks them, records and compares the baseline. The management-fee hand-check sums every product the tool can price (all nine product rows of the input form) and names any product that has an area but no fee as unpriced |
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

`verify.py` has seven sections. Sections 1-6 run the workflow once and hand the same outputs to
every check. Section 7 is separate: it builds the input form twice in a temporary folder to confirm
`build_project_input_form.py` refuses to replace an existing `Project_Budget_Input.xlsx` unless run
with `--force`, and keeps a dated backup when forced (change `guard-input-file-overwrite`). It
touches no file in `reports/`, and fingerprints the live input before and after to prove it.

`verify.py` runs the workflow once and hands the same outputs to every check, so it is faster than
running the two separately. All exit `0` on success and non-zero on failure, and none of them
touches production data — `run_workflow.py` verifies that on every run and fails if a live file
changed.

`baseline.py` needs Excel. The analysis workbook stores its headline figures as formulas with no
cached values, so they cannot be read without recalculation. Without Excel there is no numeric
baseline at all — not a weaker one. `checks.py` degrades gracefully instead, and says so in its
output when it does.

---

## The internal-wording scan

`check_remark_content` (section 5d of `verify.py`) scans every text cell of every sheet of the client
deliverable for words that belong to the tool's developers, not to the Developer reading the file:
file and function names, "Python", change-process phrasing such as "thay đổi này", the internal
guideline's name, "n=1", and the two placeholders the standard form ships. The word list is
`_INTERNAL_WORDING_DENYLIST` in `checks.py`. A hit fails the run and names the sheet and cell.

Text that comes from Savills' standard form is exempt cell by cell: `_TEMPLATE_OWNED_TEXT_CELLS`. The
scan compares each exempt cell with the template's own text, so a cell the pipeline has overwritten
cannot hide there. Add a cell to that list only after confirming it is the form's own text, and report
it to the template owner rather than editing it.

RP5's remark on `2.2 Common area Fund` (T15, which the form ships as the single word "demo") is not on
the list: the tool writes its own reason there. The Required-line check does not accept the form's
placeholder as a reason (`_FORM_PLACEHOLDER_REMARKS`, matched on sheet, code and exact text), so if the
tool ever stops writing that reason the Required check, the line-remark scan and this scan all fail
and name the cell.

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

---

## Coverage and method fidelity

Two more figures verify.py reports on every run, neither of them a pass/fail on a score:

- **Coverage**: of the cost codes a real reference budget uses (11D Thi Sách, Green Skyline — real
  client workbooks under `input/budget_planning/`, never the pipeline's own output), what share of
  that project's value is on codes this pipeline actually fills.
- **Method fidelity**: of what the pipeline writes, what share is computed by the method the costing
  spec states for that code (`data/master_list_verified/Costing_Method_Catalogue.csv`), reported as
  three VND-weighted shares — matches, partial, mismatch — with the codes behind each named.

### Adding a verdict when you add a cost line

`verification/method_coverage.py`'s `METHOD_VERDICTS` needs one entry per code the pipeline writes
to (`generate_project_budget.MGMT_FUND_EXPECTED_CODE` / `.PRODUCT_REVENUE_EXPECTED_CODE`). If you
add a new write site without adding a verdict, `verify.py` section 6 **fails the run** and names the
code — this is deliberate (design D2): a missing verdict is the one thing this section fails for,
because a verdict that can silently go stale defeats the whole point of recording it.

Each entry needs:

```python
'YOUR_CODE': dict(
    spec_method='...',      # from Costing_Method_Catalogue.csv's own `method` column, or an
                             # explicit note if the catalogue has no entry for this code
    actual_method='...',    # what the pipeline genuinely does — read the source, don't assume
    verdict='matches',      # 'matches' | 'partial' | 'mismatch'
    reasoning='...',        # why — this is what keeps a generous verdict visible to a reviewer
),
```

Removing a write site without removing its verdict fails the same way, naming the orphaned code.

### Why there is no coverage or fidelity threshold

No threshold is set on either score, and the run never fails for a low one. Any threshold today
would be arbitrary: set above the current score it blocks all work; set below, it becomes noise that
gets ignored, and an ignored check is worse than none because it still reads as assurance. The
numbers are reported so a reviewer can see the direction they move in, and only a *missing* verdict
is load-bearing enough to fail a run over.

**Revisit this when** `Costing_Method_Catalogue.csv` gains method entries for the codes that
currently have none (`ERM` as of 2026-09-17), and coverage/fidelity have moved enough times to trust
a floor. A ratchet — never go below the last recorded score — is the natural next step once there is
a stable score to ratchet from.

### Measured starting point (2026-09-17)

Method fidelity: **99.9% matches, 0.0% partial, 0.1% mismatch** (by written VND; the only mismatch is
`ERM`, which has no method recorded in the catalogue at all). Coverage: **81.4%** of 11D Thi Sách's
real spend, **93.6%** of Green Skyline's, is on codes this pipeline fills.

This supersedes the 2026-09-09 hand count this change's own proposal was built on (68.7% / 31.0%
fidelity, ~74% / ~72% coverage) — not a discrepancy in this instrumentation, but real, already-
shipped progress: `cost-energy-from-consumption-and-tariff` (archived 2026-09-10) fixed the entire
31.0% mismatch, and several new write sites (`ERM`, `EMH4`, `EMA7`, `ESC12`, `ESM25`) landed since.
See `openspec/changes/report-method-coverage-in-verification/tasks.md` task 4.5 for the full
investigation.
