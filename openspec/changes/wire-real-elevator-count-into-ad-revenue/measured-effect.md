## Measured effect — Wayne Tower (real intake) and a synthetic 3-tower illustration

Measured 2026-09-16, on the current code, via `verification/run_workflow.py`'s protected harness
(production-file snapshot before/after every run; confirmed unchanged on every run in this document).

### What moved on Wayne Tower's real intake: nothing

Wayne Tower's real intake has never had a "Passenger Elevators per Tower" value — the field did not
exist before this change. `read_input()` correctly resolves it to `None` on Wayne Tower's real file,
confirmed directly (not assumed). With the field absent, `_real_ad_frame_qty()` returns `None` and
both generators fall through to `ELEVATOR_AD_ITEMS`'s own unchanged `qty_per_tower=2` fallback.

Measured directly on Wayne Tower (2 towers):

| Figure | Before this change | After this change |
|---|---|---|
| Ad-frame quantity | 4 (= 2/tower × 2 towers) | 4 (unchanged) |
| `2.2 Common area Fund` RA2 monthly revenue | 3,393,940 VND (= 848,485 × 4) | 3,393,940 VND (unchanged) |
| Remark | "Giả định, không phải số liệu thực tế: khoảng 2 khung quảng cáo/tòa..." (assumption, not real data) | Identical text — the field being absent falls back to the exact pre-change wording |

**This change has zero effect on Wayne Tower's real deliverable, or any other real project, until
someone fills in its own Passenger Elevators per Tower field.** That is the honest current state, not
a caveat — no existing project's figures move today.

### Illustrative effect, using a synthetic 3-tower project (real elevator count supplied)

To show what the mechanism does once a project supplies its real count, ran a synthetic project
(3 towers, 3 passenger elevators/tower — matching the template's own worked example, "Mỗi tháp có 3
thang khách... Có 03 tháp") through the full pipeline, once with the field set and once without:

| | Ad-frame qty | RA2 / Ad-frame monthly revenue | Annual |
|---|---|---|---|
| No elevator count supplied (today's assumption, ~2/tower) | 6 | 5,090,910 VND | 61,090,920 VND |
| Real count supplied (3/tower × 3 towers) | 9 | 7,636,365 VND | 91,636,380 VND |
| **Swing** | **+3 (+50%)** | **+2,545,455 VND/month** | **+30,545,460 VND/year** |

Both surfaces agree on the real-data run: the analysis workbook's Additional Revenue sheet (Source
column states "Real data: this project's own 3 passenger elevator(s) per tower (Project Info intake)
x 3 tower(s) = 9 ad frame(s) — not an assumption") and the deliverable's `2.2 Common area Fund` RA2
row (7,636,365 = 848,485 × 9, verified arithmetic). This is a real, measured swing on real per-device
rates (Fact_MasterRateCard.csv) — not a synthetic or hypothetical rate; only the *quantity* was
synthetic (a stand-in project), matching the fixed worked-example ratio the template itself documents.

### Task 2.6's basement-LCD extension, measured the same way

Refreshed same day, after task 2.6 (real basement count sizing the "LCD screen (basement lobby)" row,
previously a flat `flat_qty=1` regardless of actual basement count). Wayne Tower's real intake has no
"Number of Basements" value either — same zero-effect confirmation as the elevator field, not
re-tabulated separately since it's the identical mechanism (field absent -> `None` -> unchanged
fallback).

Illustrative effect: same synthetic 3-tower project, now also given 2 basements, run through the full
pipeline with BOTH fields set:

| | Ad frame Qty | LCD tower-lobby Qty | LCD basement-lobby Qty | RA1.A (combined LCD) monthly |
|---|---|---|---|---|
| Neither field supplied | 6 | 3 | 1 (flat, unchanged) | 1,212,121×3 + 1,060,606×1 = 4,696,969 VND |
| Both fields supplied (3 elevators/tower, 2 basements) | 9 | 3 (unaffected) | 2 (real data) | 1,212,121×3 + 1,060,606×2 = **5,757,575 VND** |
| **Swing on RA1.A** | | | | **+1,060,606 VND/month (+22.6%), +12,727,272 VND/year** |

Verified exact arithmetic on the real deliverable output, not just the isolated function. The
tower-lobby LCD row (Qty 3) is byte-identical whether or not basement count is supplied — confirming
task 2.6 only touches the third `ELEVATOR_AD_ITEMS` tuple, exactly as scoped.

### Is the swing "modest," as proposal.md expected? Stated plainly, not assumed

proposal.md flagged the expected swing as small *relative to the other two changes proposed this
session* (`rank-comparables-by-location`'s management-fee rate swings of 11.5–16.3%;
`activate-dormant-staffing-ratios`, not yet measured). On this illustration: +30.5M VND/year is real
money, but small next to a management-fee rate swing that moves an ~12B VND/year revenue line by
double digits, or a payroll-cost correction spanning 8 staffing roles. Confirmed modest in that
relative sense, not asserted without measuring.

### What did NOT move

- The LCD tower-lobby row: byte-identical quantity (3) and remark text across every combination of
  the two fields supplied/absent — confirmed by direct comparison, not just designed-for (`tasks.md`
  3.2). (The LCD basement-lobby row DOES now move when `basement_count` is supplied — that is task
  2.6's intended effect, not a regression; see above.)
- Every other figure on Wayne Tower's deliverable and analysis workbook.
- The standard synthetic sample's full 5-check regression suite: 0 differences (`check_revenue_
  agreement`, `check_benchmark_reconciles`, `check_remark_content`, `check_summary_reconciles`,
  `check_required_line_items`), confirming this change is a no-op there too, re-confirmed after task
  2.6 as well.
- `EXAMPLE - Wayne Tower Thu Thiem.xlsx` and the other 4 tracked production files: unchanged on every
  run in this document (`run_workflow()`'s own snapshot, plus a direct mtime check on Wayne Tower
  specifically, predating today's session entirely).
