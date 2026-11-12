# Fact coverage across all projects (task 4.1)

Run on 2026-11-12 with `python verification/fact_coverage.py --library`. The output gives counts only, never project
names.

## Master list (105 projects)

How many projects get each fact from the master list, under the agreed rules: the tower count is never filled; the
floor count and lifts are filled only for one-tower projects.

| Fact | Projects |
|---|---|
| Street address | 99 |
| Gate count | 90 |
| Swimming pool (yes/no, count) | 84 |
| City | 71 |
| Car parking slots | 66 |
| Basements | 63 |
| Motorbike parking slots | 61 |
| District | 59 |
| Floor count (one tower only) | 17 |
| Lifts per tower (one tower only) | 15 |
| Tower count | 0 (note only, decision of 29/10/2026) |

Facts per project, as number of facts : number of projects:
- 0 : 3
- 1 : 2
- 2 : 5
- 3 : 5
- 4 : 7
- 5 : 10
- 6 : 11
- 7 : 11
- 8 : 17
- 9 : 22
- 10 : 5
- 11 : 7

## Budget library (49 selectable approved budgets)

- **Master name match:**
  - 35 files match exactly one master row by folded name, so the Review fills their blank facts from the master.
  - 14 files match no master row. Their name in the budget file differs from the master name (another phase, or
    another spelling), so the PM must type their facts or pick the row.
- **Parking slots from each file's own `0. Info`:** car slots in 43 files, motorbike slots in 43 files.
- **Facts from the master, for the 49 files:**

| Fact | Files |
|---|---|
| Street | 35 |
| Gates | 31 |
| Pool (yes/no and count) | 30 |
| Car slots | 28 |
| Basements | 27 |
| District | 27 |
| Motorbike slots | 25 |
| City | 24 |
| Floors | 2 |
| Lifts | 2 |

## Reading

- The tower count, the whole-project floor count and the lifts per tower remain the PM's to enter for almost every
  project, by the agreed rules.
- The result section and the `0. Info` block flag these blanks, so they are visible instead of silently costing 0.
