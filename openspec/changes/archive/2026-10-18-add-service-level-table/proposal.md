## Why

The tool has no idea of a "service level". A PM cannot tell whether the cleaning and security crews it proposes are
lean, standard or generous next to what Savills projects really run. The real-budget scan store (50 usable
budgets) now shows how many square metres each cleaner covers and how many 24-hour security posts a project has.
On 2026-10-16 the user approved fixed thresholds for both, set once from that data, instead of the earlier
three-equal-groups split (which always gives about 18-17-17 and moves whenever data is added). On 2026-10-18 a
critique of those thresholds (`Savills-local\budget-test\level-of-service\phan_bien_p1.md`) led to four revisions,
listed below; the user approved them standing in for the Head of PM.

## What Changes

- **A small threshold table in `data/`, one row per service, editable without touching code.** Each row holds the
  service, the measure and its unit, the two cut-off values, the direction (a lower figure means a higher level for
  cleaning; a higher figure means a higher level for security), the sanity bounds outside which a value is not
  classified, the approval date and the source. Approved values:
  - Cleaning, m² of fee-paying NFA per cleaner: below 2,500 = Nâng cao; 2,500 to below 4,000 = Tiêu chuẩn;
    4,000 or more = Cơ bản. Sanity bounds 1,000 and 8,000. Approved 2026-10-16, bounds added 2026-10-18.
  - Security, 24-hour-equivalent posts per 10,000 m² of fee-paying NFA: below 1.5 = Cơ bản; 1.5 to below 3.0 =
    Tiêu chuẩn; 3.0 or more = Nâng cao. Sanity bounds 0.5 and 8. Approved 2026-10-16; the upper cut-off was
    revised from 2.5 to 3.0 on 2026-10-18 (every project within 10% of 2.5 had an inferred, not a read, headcount,
    and 2.5 made Nâng cao the largest group).
  - Landscape: no threshold. The store has no green area, so hectares per person cannot be computed. The table
    carries a landscape row marked "not set" so the gap is visible.
  - The area on both sides is the total fee-paying NFA of every product, and the people counted are those on duty
    per day as the budgets' own A2 / A3 forms list them (user's choices, 2026-10-18).
- **A separate service-level table of real projects.** One anonymous row per project: the two measures, the level of
  each service, and whether the headcount was read from the budget form or inferred from its cost. Cleaning and
  security get two separate levels. They are never merged into one label.
- **A new internal-analysis sheet `Service Levels`.** It takes the cleaning and security headcount the tool has just
  costed, works out the same two measures, shows the level of each against the thresholds, and shows where the
  project sits in the real-project table (percentile and count). It is display only.
- **Rules carried over from the approved scan rules, plus the 2026-10-18 revisions:**
  - no NFA, or a zero or blank measure, means "chưa phân loại" (not classified), never a guess;
  - a value outside the sanity bounds is kept in the table but marked "chưa phân loại: ngoài cận, nghi đọc sai" and
    left out of the comparison set (revised: on 2026-10-16 it was flagged but still given a level);
  - the percentile is computed over projects whose headcount was read from a form; inferred headcount is shown for
    reference only, because inference turns a higher price per person into a higher headcount and skewed the
    inferred rows towards Nâng cao (revised);
  - a measure within 10% of a cut-off is marked "sát ngưỡng" (near the threshold), so a PM sees that a small change
    would move the level (new);
  - two files with identical fee-paying NFA are the same project, and only the latest counts (new; the 2026-10-16
    set held one project twice under two names);
  - the thresholds are fixed and are not recomputed when data is added.
- **The earlier v7 level workbook stops being a definition of "mức".** Its combined three-equal-groups level stays
  as history only, and its README says so, so that the tool and the workbook never give two different levels for
  the same project.
- **No figure on the client deliverable moves. No `verify.py` baseline is re-recorded.**

## Capabilities

### New Capabilities
- `service-level-tiers`: the threshold table, the anonymous per-project table built from the scan store, how a
  project is classified (measures, rules for missing, odd or near-threshold values, source marking), and the
  `Service Levels` sheet.

### Modified Capabilities
- `budget-workflow-verification`: checks that the `Service Levels` sheet ties to the roster and to the threshold
  table, that the comparison set holds only form-read, classified projects, that the table carries no project or
  file name, and that the deliverable is unchanged.

## Impact

- **Code:** a build script `build_service_levels.py` (reads the store given on the command line); a module
  `service_levels.py`; `generate_project_output.py` (the new sheet); `verification/checks.py` and `verify.py`.
- **Data:** new `Budget_Agent/data/service_levels/Ref_ServiceLevelThresholds.csv` and
  `Ref_ServiceLevelProjects.csv` (outer repository, anonymous). The scan store stays in `Savills-local`.
- **Figures:** none. The client deliverable and every recorded baseline stay as they are.
- **Docs:** `docs/project-status.md`, `docs/05-decisions.md` (thresholds, their approval, the 2026-10-18 revisions
  and why), `RUNNING.md` (how to rebuild the table), and one line in the level-of-service README in `Savills-local`
  (v7 level is history).
- **Not in this change:** a "wanted level" input on the form, warnings that block a run, a green-area input for
  landscape, and any use of the level to set headcount. Each would need its own decision.
- **Order with other changes:** independent of `use-real-budget-ranges` and `apply-head-of-pm-decisions-2026-10`,
  but it reuses the same store rules and anonymising step as the first.
