# Changelog

Changes as the people using the Budget Agent see them: the budget web, the generated workbooks and the site packages.
Newest first. Each release is tagged on GitHub with the same name. Entries before v2026.11.20 were written afterwards
from the commit history and have no tag.

## v2026.11.20 (2026-11-20)

- **Printing:** the budget web's "In PDF A4" and "In PDF A3" buttons print sheet 2 with its own print setup. A4 now
  really comes out as A4 on machines whose Windows region uses Letter paper. Before, Excel quietly switched the paper to
  Letter. A PDF of the wrong paper size is refused with a clear message, not handed out.
- **Run log on the page:** the log box shows file names only. Folder paths on the server, like `C:\...`, no longer
  appear. The run log kept on the server still has the full paths.
- **Sinking fund:** sheets 3 and 3.1 price the sinking fund on every run. Sheet 3 shows the same budget year as the run's
  budget period.
- **Project facts everywhere:** every project fact entered on the web appears on sheet 0. Info, in the site package and
  on the web.
- **Outside link with per-project access:** a project user who opens the outside link sees and runs only their own
  project's data. Lines that name other projects are held back.
- **Email code login on the outside link (not yet deployed):** besides the Cloudflare login, the outside link can accept a
  one-time 6-digit code sent by email. It stays off until it is switched on.
- **Site packages:** a package can be built without last year's approved budget. The site then uploads that budget, or
  uses the new-project tabs. The leak check scans all shipped code for project names.

## Earlier history (no tag)

### November 2026, 1–12

- **Site packages:** one click-to-run folder per managed site, holding only that site's own data. The package is zipped
  only when its leak check passes. It also carries the system overview page.
- **Review:** lines with an abnormal difference (20% or more, and 50 million VND a year or more) are flagged on the sheet,
  on the page and in the adjust table. Lines the tool cannot price are left for the PM to fill in.
- **Prices and sources:** each line has a payment frequency, taken by default from the real budgets. Energy use and capex
  come from hand-checked projects. Reference projects are joined by key.
- **Adjust table:** column headers show the year.

### October 2026

- **Budget web:** an input page with a "Tạo ngân sách" button, SSO login, and a viewer role that sees only the client
  deliverable. Tabs added: Review for operating projects, adjustment, projects already created, the budget library, and
  the guide.
- **Budget Review:** reads last year's approved budget. It shows approved, actual and expected columns for year N-1,
  grouped as on the 2027 form. Facts are pre-filled from earlier runs, and every run is logged.
- **Adjustment:** a sheet "4. Điều chỉnh" on the client deliverable. It supports quantity × unit price adjustments.
- **Pricing rules signed off by the Head of PM:**
  - real-budget ranges from a store of 55 projects;
  - contingency;
  - Savills' fee, with the fee narrative;
  - cleaning staff and security posts sized from the fee-paying area;
  - asset insurance from the insured value;
  - villa-only and no-parking projects;
  - paid holidays by the law in force;
  - calendar working days;
  - dated VAT rates.
- **Operating projects:** last year's staffing is carried forward. Common-area electricity and water come from actual
  spend. Entered rates, the stable-operation switch and recorded parking revenue are used when given.
- **Other:** a service-level table, a budget period with its own start month, and aggregate rows read by formula.

### August–September 2026

- **First version:** fills Savills' 2027 Resi budget form from one input workbook. It writes the client deliverable,
  the internal analysis and the shift roster.
- **Workbook contents:**
  - remarks giving the source of every figure, in Vietnamese;
  - capex as a sinking-fund column;
  - fee rollover and Year 1 strategy sheets;
  - real employer insurance;
  - the common-area fund.
- **Safeguards:**
  - generated files are cleaned of OneDrive corruption;
  - an existing input form is not overwritten unless forced;
  - `verify.py` checks that the summary ties to the detail sheets and reports how much of the cost each method covers.
