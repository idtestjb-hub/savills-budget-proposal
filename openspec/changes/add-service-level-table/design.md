## Context

See proposal.md for why. What shapes the approach:

- **The analysis behind the thresholds** was run on 2026-10-16 in `Savills-local\budget-test\level-of-service\`
  (`density_p21.py`, `tier_fixed_p21.py`, with `density_p21.md` and `tier_fixed_p21.md`) and critiqued on 2026-10-18
  (`phan_bien_p1.md`, `phan_bien_p1_sens.py`). It reads `level_assignment_v7.csv`, `rec_v7.pkl` and the scan store
  `budget_scan_v2.sqlite`. Result after the 2026-10-18 rules: 48 projects after keeping the latest file per project
  (one pair with identical NFA merged), 41 with fee-paying NFA. The measures form one continuous spread with no
  natural break, so the cut-offs are round numbers read off that spread, not a statistical finding. Three of the four
  sit where a three-equal-groups split would also cut; their only advantage over that split is that they are frozen.
  They split the 41 projects 13 / 18 / 10 for cleaning (Nâng cao / Tiêu chuẩn / Cơ bản) and 12 / 19 / 9 for
  security (Cơ bản / Tiêu chuẩn / Nâng cao), with one security value not classified (suspected misread).
- **Sensitivity (2026-10-18, 42 projects):** moving a cut-off by 10% changes the level of 1 to 6 projects per
  cut-off; 11 projects sit within 10% of the cleaning cut-off 2,500, which is the densest part of the spread. No
  cut-off between 2,000 and 4,500 m² per cleaner would be more stable.
- **The store holds real project names**, so it stays out of the repository. The inner repository (`source_code/`)
  is pushed to GitHub. The outer repository (`PM/Project`, which holds `Budget_Agent/data/`) has no remote.
- **Headcount in the store comes from two places.** In 31 of 52 files for cleaning and 34 of 52 for security it is
  read from a staffing form inside the budget; for the rest it is inferred as service cost divided by the median
  form price per position. The inferred figure is not a count of people, and it is biased: a project that pays more
  per person than the median is counted as having more people. On 2026-10-18 the inferred cleaning rows had a median
  of 2,512 m² per cleaner against 3,391 for form-read rows, and 9 of 18 inferred rows were Nâng cao against 4 of 24
  form-read rows.
- **The tool costs security and cleaning as outsourced positions** with headcount and coverage hours
  (`outsourced-service-costs`). The roster already lists them, so the tool's own measures can be computed from it.
- **The earlier level workbook (v7)** uses these same densities as inputs to a combined index, so its correlation
  with them is circular. It is a separate, frozen analysis; this change does not rebuild it, but retires its level as
  a definition (D12).

## Goals / Non-Goals

**Goals:**
- A PM sees the tool's cleaning and security crew set against fixed, explainable thresholds and against real projects.
- Thresholds and sanity bounds can be changed in a data file, with the approval date recorded.
- A PM can tell when a level is fragile (near a cut-off) or rests on inferred rather than read headcount.

**Non-Goals:**
- No change to any figure, the roster, or the client deliverable.
- No wanted-level input, no warning that blocks a run, no landscape level, no combined level.
- The v7 workbook is not rebuilt; only its README gains a line saying its level is history.

## Decisions

**D1. Thresholds and sanity bounds in a data table, not constants in code.**
`Ref_ServiceLevelThresholds.csv`, one row per service, with the two cut-offs, the direction, the two sanity bounds,
the approval date and the source. The user chose a separate data table. Alternative: constants in code. Rejected
because every change of a threshold would then need a code edit and a release. The bounds live in the same table
(revised 2026-10-18) because a bound is a decision of the same kind as a cut-off.

**D2. A band edge belongs to the higher-numbered band.** Cleaning below 2,500 is Nâng cao; exactly 2,500 is Tiêu
chuẩn; exactly 4,000 is Cơ bản. Security below 1.5 is Cơ bản; exactly 1.5 is Tiêu chuẩn; exactly 3.0 is Nâng cao.
The rule is written once so that tests and the Excel check agree.

**D3. Two levels, never merged.** The user chose to show cleaning and security separately. On 2026-10-16 the two
agreed in only 23 of 42 projects, and a merged label would hide the other 19. Alternatives (rounded average, the
lower of the two) were offered and not chosen. If a later change ever needs one label, it is the lower of the two,
shown with both components; never an average.

**D4. Keep and mark both sources; compare against form-read projects only.** (Revised 2026-10-18.) Both the form-read
and the inferred headcount stay in the table with their `source` ("form" / "chi phí"). The percentile and the count on
the sheet are computed over form-read, classified projects only (23 for cleaning and 25 for security on
2026-10-18). The inferred rows are shown as a second count for reference. Reason: the inference bias in Context would
otherwise pull the comparison set towards Nâng cao. Alternative: inferring headcount from the project's own price per
position. Rejected: that price is not in the store for projects without a form, which is the case being inferred.

**D5. Count the same positions the store counts.** Cleaning counts every cleaning position on the roster, supervisors
included, because the store's headcount does the same. Security counts each position at coverage hours / 24. If this
rule differs from what the store did, the measures stop being comparable. Task 1.1 re-checks it against the store
before the build.

**D6. Fee-paying NFA stands in for the area to clean.** The store has no cleanable area. The sheet says so in
Vietnamese. Gross-versus-usable area can move cleaning cost by about 15% (found in the 2026-10-16 search), so the
note stays on the sheet.

**D7. Anonymous table, built from the store with the approved scan rules, plus an identical-NFA rule.** Same rules as
`use-real-budget-ranges`: latest file per project, an unnamed file is its own project, no PDF, xlsb or duplicate.
Added 2026-10-18: two files whose fee-paying NFA is identical to the square metre are the same project even when
their names differ (one project appeared twice under two phase names on 2026-10-16); the latest budget year wins,
and on a tie the later file date. The two builds SHOULD share one reading step for the store, to avoid two copies of
the rules; if `use-real-budget-ranges` is not yet built, this change carries a small reader and the two are joined
later.

**D8. The percentile excludes the project itself.** The same leave-one-out idea as `real-budget-ranges`, matched by
`name_key` or by NFA within 0.5%, so that a project already in the store is not compared with itself.

**D9. The new sheet is last among the internal sheets and read-only.** It writes no value that another sheet reads,
which keeps every recorded baseline unmoved.

**D10. A value outside the sanity bounds is kept, not classified, and left out of the comparison.** (Revised
2026-10-18.) Security below 0.5 or above 8 posts per 10,000 m², or cleaning below 1,000 or above 8,000 m² per
cleaner, is marked "chưa phân loại: ngoài cận, nghi đọc sai" with the value kept in the table, and is excluded from
the comparison set. On 2026-10-16 the one such project (0.08 posts; its security form has no hours column and only one
row was read) was flagged but still given the level Cơ bản, which would have shown a PM a wrong level with a note.
The next-lowest security value is 0.99, so 0.5 cuts in a real gap. The cleaning bounds enclose every value seen so far
(1,062 to 7,819); the two extremes are checked by hand in task 1.1.

**D11. A measure within 10% of a cut-off is marked "sát ngưỡng".** (New 2026-10-18.) The mark is on the sheet and in
the real-project table. It changes no level. Reason: a quarter of the projects sit within 10% of the cleaning cut-off
2,500, and a PM should know the level would move with a small change in headcount.

**D12. The v7 workbook's combined level is history, not a definition.** (New 2026-10-18.) The README in
`level-of-service` gets one line saying so. Reason: otherwise a project has one merged level in v7 and two separate
levels in the tool, and they disagree for about a third of the projects whichever merge rule is used.

## Risks / Trade-offs

- **The thresholds are set from the same data they are tested on.** → The proposal and the sheet say they are round
  numbers read off the data's spread, not an outside standard, and the build's count check is a regression check, not
  a validation. APPA and similar tables are for schools and cannot be applied to NFA directly.
- **Inferred headcount is biased upward** (see Context). → Excluded from the percentile (D4), shown as a separate
  count, marked on every row.
- **The security cut-off 3.0 is also read off the data.** → It was chosen because the band 2.25 to 2.75 around the
  earlier 2.5 held only inferred rows, and the natural break without the misread project falls near 3.0. Moving it
  by 10% changes the level of 1 to 4 projects.
- **NFA is not the cleanable area.** → Stated on the sheet (D6).
- **A new project's roster is partly the tool's own estimate**, so its level partly reflects the benchmark used to
  estimate it. → The sheet says whether the headcount came from the input or from the benchmark.
- **Small comparison set** (41 projects; 23 and 25 form-read). → The count is always shown; the percentile is given
  without a verdict word.
- **Store drift:** a rescan changes the real-project table but not the thresholds. → Rebuilding the table records the
  store's scan date in the file.

## Migration Plan

Additive only. Build the two data files, add the module and the sheet, extend verification. Rollback: remove the sheet
call and the two data files; nothing else reads them.

## Open Questions

- Whether a later change adds a wanted-level input or a landscape measure (needs green area on the input form).
  Neither alters this change's specs.
- Whether the Head of PM confirms the two 2026-10-18 revisions of values (security 3.0, sanity bounds) at the next
  review; the user approved them standing in.
