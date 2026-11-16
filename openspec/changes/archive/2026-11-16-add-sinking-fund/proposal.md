## Why

The user reported (2026-11-12) that no Budget Agent output has a sinking fund (quỹ bảo trì). The standard form has
the two sheets for it, `3. Budget-Sinking Fund` and `3.1 Report-Sinking Fund`, and `1. Summary` rows 66–70 read
sheet 3. But the tool has never written either sheet, and both ship hidden. Budget Review reads only the
management fund and the common-area fund, so a project's approved sinking fund is lost when it is reviewed.

Before planning, the real-budget scan store was checked for the sinking fund (see "Data checks" below). Several
misreads were found. Measured against the corrected data, a per-code median predicts a new project's sinking fund
poorly. For a review, carrying the prior approved figure forward per code predicts it well. The user chose the rules
below on 2026-11-12.

## What Changes

- **A sinking-fund reference built from real budgets.** The scan store's sinking-fund sheets are read under fixed
  rules, and one anonymous value per project and code is written beside the management-fund ranges:
  - one file per project, chosen and NFA-checked exactly as for the management fund;
  - prices brought to 2027 with CPI;
  - VAT taken out at the rate in force on each date.
  The amount is the line's Total Price (column H). On five sheets of one form variant, the store reads the prior
  year's approved column instead of the budget year, and H avoids that. A sheet in which every line carries the same
  amount is a placeholder and is left out. A sheet from another budget year in the same file is left out.
  Lift codes (ERLM1–ERLM4, ESA1) are per lift; every other code is per m² of fee-paying NFA. The lift count comes
  from the master list.
- **New project: sheet 3 is priced.**
  - Every code found in at least 10 reference projects, 48 codes today across all 32 projects with sinking-fund
    figures, gets the median. Its remark gives the basis and the middle range (p25–p75).
  - Every other code is left blank with "PM điền", as on sheet 2.
  - Lift codes need the project's total lift count, service lifts included: a new Project Info input, pre-filled
    from the master list (user, 12/11). A code below 10 projects for its driver
    (ERLM3, ERLM4 today) is left for the PM.
- **Warranty period for a new project.** The input form gets "Số tháng bảo hành còn lại tính từ tháng đầu
  ngân sách" (default 24). The input has no handover date. Months inside the
  warranty cost only:
  - maintenance contracts (every code whose item is a maintenance contract, 40 codes);
  - safety inspections (ESA1–ESA21);
  - periodic cleaning and suction (ERCS1–ERCS5);
  - outsourced sewage-plant operation (ERS1);
  - bank fees (EMB1);
  - miscellaneous (ERM; priced on sheet 2 today, see below);
  - irrigation, and plumbing and sanitary (ERPS4, ERPS5).

  Spare parts, renovation and "Others" lines are 0 for those months, with the remark "trong thời gian bảo hành".
  The PM can change the number of months.
- **Budget Review: the sinking fund becomes the third fund.**
  - The prior approved figures are written into `3.1 Report-Sinking Fund`.
  - The new year on sheet 3 is built per code from a base:
    - the approved file's own sinking-fund budget, read from Total Price, × CPI;
    - when that sheet is empty, its 3.1 approved figure × CPI, with the year named.
  - A code with neither falls back to the median rule above.
  - Every figure is in the same VAT basis as sheet 2.
  - A code with an approved figure that the tool gives 0 gets a "Nhập số" row on `4. Điều chỉnh` (`SF|` prefix).
  - The web Review results show a sinking-fund comparison table: approved, new year, median reference, difference.
- **Sheets 3 and 3.1 are shown when they hold figures.** `1. Summary` rows 66–70 tie to sheet 3, and `verify.py`
  checks it.
- **Each code in one fund only.** The tool never prices the same code on both sheet 2 and sheet 3. Today ERM is
  priced on sheet 2, and ERCS1 is left there for the PM. Where a code belongs is the Head of PM's question B8
  (`docs/22`). Until it is answered:
  - any code sheet 2 prices or leaves for the PM stays there and is 0 on sheet 3 (today ERM and ERCS1). The set is
    found at run time;
  - the open question is recorded as a task.
- **Site package.** The sinking-fund reference file is anonymous. The package carries it, and the leak check covers it.

## Data checks (12/11/2026, store `final_v5`, outside the repository)

- The store was rescanned with two newly added files. No old file's lines changed. Neither new file adds
  sinking-fund figures: one has an empty sheet 3, the other has no main management-fund sheet.
- 32 projects carry sinking-fund spending. Budget years run 2021–2026, most of them 2026.
- **Leave-one-project-out test, total sinking fund:**
  - per-code median × NFA: median error about 87%;
  - renovation codes alone: about 225%;
  - prior approved × CPI: 37% on the total, 13% per code.

  The 13% is partly circular: the PM drafts the new year with 3.1 open in the same workbook. It still shows that
  carry-forward is the better base for a review.
- A pool of "similar NFA" projects did not consistently beat all projects, so all projects are used.
- No first-year budget in the store has real sinking-fund figures. The warranty rule is therefore the user's business
  rule, not a measured one.

## Capabilities

### New Capabilities
- `sinking-fund`: pricing of `3. Budget-Sinking Fund` for a new project (medians, lifts per lift, PM lines, warranty
  months), and for a review (prior approved per code × CPI, fallback to the median); `3.1` prior figures; sheet
  visibility; the one-fund-per-code rule.

### Modified Capabilities
- `real-budget-ranges`: the build also writes the anonymous sinking-fund reference from the store's sinking-fund
  sheets, under the read rules above.
- `budget-review-workflow`: Review reads and carries the sinking fund as a third fund.
- `budget-web-review-results`: a sinking-fund comparison table.
- `budget-adjustment-sheet`: "Nhập số" rows for sinking-fund codes (`SF|`).
- `budget-site-package`: the package carries the sinking-fund reference file, and the leak check covers it.
- `budget-workflow-verification`: `1. Summary` rows 66–70 tie to sheet 3. Sheet 3 lines left for the PM are listed
  and checked like sheet 2.

## Impact

- **Code:**
  - `build_real_budget_ranges.py` and `real_budget_ranges.py`: the sinking-fund reference.
  - `generate_project_budget.py`: sheet 3 writer, warranty months, and showing the sheets.
  - `review_import.py`: the third fund, and writing 3.1.
  - The Review adjust and results pages in `webapp/`.
  - `build_site_package.py` and its data lists.
  - `verification/checks.py`.
  - The input form builder and labels: "Số tháng bảo hành còn lại".
- **Data:** a new anonymous file in `data/real_budget_ranges/`. It holds per-project values and no names. It is
  rebuilt from the store outside the repository.
- **Deliverable:**
  - New projects get a non-zero sinking fund on sheet 3 and `1. Summary` rows 66–70.
  - Reviews get the approved and new sinking fund.
  - Before archiving: a measured before/after on the standard sample, the site-package Review sample and one more Review,
    plus the PM's sign-off.
- **Not changed:**
  - the management-fund and common-area-fund figures;
  - which code sits in which fund for ERM and ERCS1 (waiting on B8).
