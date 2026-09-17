## 1. Sequencing precondition

- [x] 1.1 Archive `price-all-product-types` (and, while there, `read-input-by-label` — both complete)
  so `product-revenue-pricing` exists at `openspec/specs/product-revenue-pricing/spec.md`. Verify
  with `openspec list` (neither appears as active) and `ls openspec/specs/product-revenue-pricing/spec.md`.
  — Done: both moved to `openspec/changes/archive/2026-09-10-*`; main specs `product-revenue-pricing`
  and `input-workbook-reading` synced; `openspec validate --specs` → 8 passed.
- [x] 1.2 Re-read `openspec/specs/product-revenue-pricing/spec.md` and confirm the requirement
  "The two workbooks report the same revenue" is present, so this change's MODIFIED delta has a
  target. Verify: `grep "The two workbooks report the same revenue" openspec/specs/product-revenue-pricing/spec.md`.
  — Confirmed: present at line 37.

## 2. Unify the matching basis in the deliverable generator

- [x] 2.1 In `generate_project_budget.py`, change the per-product rate loop's
  `nearest_comparables(project['apartment_nfa'], …)` (~line 708) to `project['total_nfa']`. Verify:
  `grep -n "nearest_comparables(project\['total_nfa'\]" generate_project_budget.py` shows this site.
  — Done: now line 714, with an explaining comment.
- [x] 2.2 In `generate_project_budget.py`, change the derived-headline-rate block and its
  `all_ranked` companion (~lines 1108–1109) from `project['apartment_nfa']` to `project['total_nfa']`.
  Verify: no `nearest_comparables(project['apartment_nfa']` remains — `grep -n "apartment_nfa'\], exclude" generate_project_budget.py` returns nothing.
  — Done: lines 1116–1117; `grep "nearest_comparables("` shows all 3 sites on `total_nfa`.
- [x] 2.3 Relabel the "Comparables" appendix (~lines 1302–1304): row label "Apartment NFA (m²)" →
  "Total NFA (m²) — matching basis", and the delta row computed against `project['total_nfa']`; add
  an "Apartment NFA (m²)" reference row for context if it reads clearly. Verify: generate the
  sample deliverable and read the Comparables sheet — the size row is Total NFA and the delta ties
  to it.
  — Done: SCALE section now "Total NFA (m²) — matching basis" + delta on total_nfa + "Apartment NFA
  (m²) — for reference only" row; the A2 caption on the Comparison sheet updated too. Sheet-level
  check folded into the verify.py run in task 3.2.
- [x] 2.4 Update the console print in `generate_project_budget.py` (~lines 1117–1120) that prints
  "ApartmentNFA=" to print the Total NFA it now matches on. Verify: run the generator, the printed
  basis matches the value used.
  — Done: prints `TotalNFA=… — matching basis` and the per-comparable delta on `total_nfa`.
- [x] 2.5 Confirm `generate_project_output.py` is untouched by this change. Verify: `git diff --stat`
  (or file mtime) shows only `generate_project_budget.py` and the verification files changed.
  — No git in this clone. Only `generate_project_budget.py` was edited in this group;
  `generate_project_output.py` already matches on `project['total_nfa']` (its line ~179) and was
  not touched.
- [x] 2.6 (added during apply — design Decision 5) Derive `build_budget`'s headline rate with
  `derive_product_rate(all_ranked, 'Apartment', n=2)` — the same function the RM lines and the
  analysis use — instead of `derive_mgmt_rate`, so `0. Info`!I8, the Comparison sheet and the
  analysis show one rate and it is the rate the budget charges. Keep `derive_mgmt_rate` only as the
  no-Apartment-rate fallback. Verify: on Diamond Skyline `0. Info`!I8 (15,900) == the analysis
  derived Apartment rate (15,900) == the rate Apartment RM is priced at.

## 3. Verification enforces the two workbooks agree

- [x] 3.1 Add `check_revenue_agreement(paths)` to `verification/checks.py`: run both generators'
  outputs through Excel COM, compare total management-fee revenue, each product's revenue, and the
  derived rate beyond rounding; return the disagreements with both values in VND. Verify: a unit
  invocation on the current outputs returns "agree".
  — Done: `check_revenue_agreement` reads RM per-product (un-ramped ÷Σfills×12) from the deliverable
  and per-product monthly×12 from the analysis 'Management Fee' sheet; one COM session, both books.
- [x] 3.2 Surface it in `verification/verify.py` as its own line in section 5 (deliverable figures),
  failing the run and naming the figure on disagreement. Verify: `python verification/verify.py`
  prints the cross-generator line and it reads OK.
  — Done: verify.py section "5b"; run 2026-09-10 PASS —
  "deliverable and analysis agree on all 3 priced product(s) and the total (12,178,230,000 VND/year)".
- [x] 3.3 Negative test: with the matching bug reintroduced, confirm `check_revenue_agreement`
  FAILS naming the disagreeing figures, then restore.
  — Done on Diamond Skyline (the fixture is apartment-dominant and can't show it — see the NOTE
  below). With the deliverable back on `apartment_nfa`, `check_revenue_agreement` → `ok=False`,
  naming Apartment / Officetel / Nursery / TOTAL with both values in VND (deliverable
  17,381,400,000 vs analysis 15,020,400,000). Text recorded in `design.md` D-appendix "Negative
  test". File restored from a clean copy; `grep` confirms no test markers remain.
  — NOTE: the synthetic fixture (Apartment 52,000 / Total 54,400 m²) is apartment-dominant;
  `derive_product_rate` picks the same comparables at either NFA, so reverting the bug on the
  fixture does NOT make `verify.py` 5b fail. A dedicated mixed-use fixture is a sensible follow-up.

## 4. Measure, baseline, sign off

- [x] 4.1 Manual spot-check against a known project: generate the Diamond Skyline deliverable before
  and after the change. Fill a table in `design.md` (a D-appendix) with, in VND: the derived
  management-fee rate, total RM revenue, each per-product RM line (`RM.AP`…`RM.KG`), `RM.0A`, the
  parking-area management fee if written, and the estimated surplus — before and after, with the
  delta. Verify: the table is complete and every non-zero delta is explained.
  — Done: `design.md` "D-appendix — Measured effect". Headline: deliverable RM 17,381,400,000 →
  15,020,400,000 (−2.36bn, now == analysis); `0. Info`!I8 15,150 → 15,900; estimated year-1
  surplus 9,671,416,438 → 7,312,010,678 (−2.36bn). Measured via `run_workflow` against the real
  Diamond input to a temp dir — production `reports/` untouched.
- [x] 4.2 Confirm the analysis workbook's 24 baseline figures are unchanged (the analysis generator
  did not change). Verify: `python verification/verify.py` section 4 shows all 24 matching.
  — Done: `verify.py` run 2026-09-10 — section 4 "all 24 figures match the baseline"; section 5
  "all 7 ramped deliverable figures match the baseline".
- [x] 4.3 Present the Diamond Skyline movement to PM and record sign-off in `docs/05-decisions.md`
  (extend D2 / the B3 note) and `docs/08-guideline-change-family.md` row C. Verify: both docs name
  the change, the figure movement, and the sign-off date.
  — PM signed off 2026-09-10. `docs/05` D2: new "**B3 — CLOSED 2026-09-10**" block with the
  measured effect; D6 status updated (Master Info clause dropped). `docs/08` row C rewritten
  ("✅ DONE 2026-09-10"), diagram + suggested order updated.
- [x] 4.4 ~~Re-record `verification/baselines/deliverable_baseline.json`~~ — NOT NEEDED. The
  synthetic fixture is apartment-dominant; all 7 deliverable-baseline figures and all 24 analysis
  figures are unchanged by this change (verified in 4.2). Same outcome as `read-input-by-label`.

## 5. Close out

- [x] 5.1 `openspec validate "unify-revenue-basis-across-outputs" --strict` passes.
  — "Change 'unify-revenue-basis-across-outputs' is valid" (2026-09-10).
- [x] 5.2 Update `docs/project-status.md` — move change C from "not started" to done, and note B3 is
  closed. Verify: the OpenSpec-state table and the guideline-family section reflect C.
  — Done post-archive: archived-changes table (9), accepted specs (`product-revenue-pricing` → 6
  requirements), guideline-family diagram + §2 narrative, "read these first" (3b), next-action list.
