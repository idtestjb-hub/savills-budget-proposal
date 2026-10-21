## Context

The pipeline reads one input workbook by label (`input_labels.SheetLabels`) and writes three workbooks. Existing-project
mode is a switch on `Project Info`; `existing_staffing.read_existing()` and `existing_utilities.read_utilities()` read
their sheets by block title and column header (`es._section_rows`, `es._read_block`). `verification/isolation.py`
redirects every input and output path of both generators into a work folder, and `run_log.py` already opens the
deliverable in Excel, recalculates it and reads the fund sheets by code. The scan store's reader
(`Savills-local\budget-test\scan-2026-10-07\scan_budgets.py`, outside the repository) finds a fund sheet's code column,
its R / E / PL1 / PL2 anchors, its leaf rows and the value column that ties to the anchors; its v2 adds the VAT rule per
line. The M3 comparison (`compare_m3.py`) matches tool and real lines by code and brings both to one VAT basis.

The demo file (2026 budget of an operating high-rise) is on the 2026 form: `2. Budget-Management Fund` with code column
Y, indicator X, annual AK, months AQ:BB, remark AO; `2.2 Common area Fund` with annual AG and months AL:AW; both ex-VAT
(`F7` = KHOÁN, title row 4 "Excluding VAT"); `0. Info` with one row per product (NFA, units, applied rate) and the
parking rows. Its `2.1 Report` sheets hold a nine-month actual and a three-month expected per code, not twelve monthly
bills.

## Decisions

- **D1 One source file, read directly, by the scan store's rules.** `review_import.read_prior_budget(path)` opens the
  workbook read-only (values only); a workbook openpyxl refuses because of broken defined names is read from a
  stripped copy written into the work folder, as the scan store does. The fund sheets are chosen by name (the
  Management Fund budget sheet and the Common area Fund sheet, with the scan store's `fund_of` / `kind_of` name rules);
  a report, scenario or year-2 sheet is never read. On each: the code column is the one with the most code-like
  strings; the indicator column is the one to its left; the anchors are the rows coded `R`, `E`, `PL1`, `PL2`; a leaf
  is a coded row without an indicator between R and PL1 (plus the scan store's exceptions `EM#`, `ES#`, `EE#`,
  `ESR`); the value column is the first column headed "Total/Estimate budget of year" whose leaf sums tie to the
  sheet's own R and E rows, else the first so headed, flagged; the twelve months are the date-headed columns to the
  right of it. PDF, xlsb and a workbook with no fund sheet stop with a message naming the file.
- **D2 The approved figure is the year column, cross-checked.** Each line's approved figure is the value column.
  The twelve months are read beside it; when their sum differs from the year column by more than 1 VND, the line is
  flagged "12 tháng không khớp cột năm" and the year column is kept. *(User's choice 2026-10-20; the alternative was the sum of the twelve months.)*
- **D3 One VAT basis: the deliverable's.** The Review sheet compares on the basis of the client deliverable
  (inclusive unless the template's `F7` reads KHOÁN, as `run_log.py` decides). The file's basis comes from the sheet
  title ("Excluding VAT / Chưa gồm thuế GTGT" or `F7` = KHOÁN means ex-VAT; "Including" means inclusive; neither
  means unknown, flagged, treated as the deliverable's basis). When the two bases differ, the approved figure is
  converted per line with the scan store's rule: no VAT on salary lines (EMH2, EMH3, EMH4, EMH6, EMH8, EMH11, EMH12,
  EMO1), taxes and fees (EMH10, EMA17, CIT*, VAT*), bank fees (EMB1) and bank interest (RO2*); 8% in the reduced
  periods of NĐ 15/2022 to NĐ 174/2025 (to 12/2026) and 10% otherwise, averaged over the file's twelve months. The
  sheet shows the figure as read, the factor and the converted figure in three columns, so nothing is hidden.
  The rates per month come from `Ref_UtilityTariffs.csv` (`utility_tariffs.vat_rate`); months before that table
  starts use the scan store's dated periods. A rate the import entered on the file's basis is used by the tool as
  entered (the existing rule of `Actual Rate`: never converted), so the management-fee rows carry a remark saying
  so. *(User's choice 2026-10-20; the alternative was ex-VAT as the M3 comparison.)*
- **D4 Which lines, and codes the 2027 form does not carry.** Sections R and E of both fund sheets; section D (VAT,
  CIT, PL) is not compared. A code is matched to the same fund sheet of the 2027 template. A code the template's
  sheet does not carry is kept in the approved column and its section total (so the approved column still ties to
  the file's own R and E rows), listed under a heading "Mã không có trên form 2027" with the tool column blank, and
  listed in `IMPORT NOTES`. No automatic mapping: `review_import.CODE_ALIASES` is an empty table where a mapping the
  Head of PM confirms (old `ESA*` codes, for instance) goes later. A code repeated on one side is summed; lines with a
  figure but no code become one "(không mã)" row per section.
- **D5 The tool's figure is read from the recalculated deliverable.** `review.py` opens a copy of the deliverable in
  Excel, recalculates, and reads the leaf rows of both fund sheets exactly as `run_m3.tool_lines` does (annual cell
  whose formula is `=SUM(` over the month cells; group rows are SUBTOTALs and skipped), plus the sheet's own R and E
  rows. Section D starts at the `D` row, or at `PL1` on a sheet without one (the Common area Fund sheet has none;
  the first demo run counted its VAT and CIT rows into E, 12.1 million VND, and was corrected). The Review sheet's tool totals per section must equal those R and E rows within 1 VND, or the command prints
  the difference and exits non-zero. This is why the sheet is built by `review.py` after the run and not by
  `generate_project_output.py`: the figures do not exist until Excel has computed them.
- **D6 "How the tool got its figure", one label per line, in this order:** `Mang sang theo luật` for EMH2, EMH3,
  EMH4 in Existing mode; `Mang sang theo biểu giá` for EEE.C and EEW.C; `PM nhập` for a line fed by an operating input
  the import filled (management-fee rows of a product with an actual rate, RP1 and RP2 when parking revenue was
  entered); `Ước lượng: <method>` for every other line with a figure, the method being the catalogue's `method` in
  short Vietnamese (`review_import.METHOD_VI`, falling back to the English method text); `Chưa có phương pháp` when
  the approved line has a figure, the tool has none and the catalogue has no method for the code (absent,
  `not-estimated`, `unclear`, `manual-per-project`); `Công cụ ra 0` when the tool has a method but produced 0 against
  an approved figure; `Chỉ công cụ` when the file has 0 and the tool a figure. The tool's figure is shown as it is;
  an approved figure is never copied into the tool column. *(User's choice 2026-10-20; the alternative was to copy the approved figure where the tool has no method, which
  would change the deliverable.)*
- **D7 What the import fills on the form.** `Project Mode` = Existing project; `Prior Budget Year` = the file's
  budget year (the year with most months of its period); `Budget Start Month` = the first month of the file's period
  plus twelve months; `Minimum Wage Region` blank unless `--facts` gives it. `Prior-Year Roster`, block `STAFF LINES`:
  approved EMH2, EMH3, EMH4 from the Management Fund sheet (VND/year). `Prior-Year Utilities`, block `UTILITY LINES`:
  approved EEE.C and EEW.C from the Management Fund sheet with the file's VAT basis; no monthly bills, so the utilities
  module's approved-amount fallback applies and the Utility Bridge says so. `Project Info`: NFA and units per product
  from `0. Info` (rows named after the nine products, Nursery also as Kindergarten / Nhà trẻ), motorbike and car bays
  from the parking rows' bay counts, each actual rate per product with its VAT basis from `0. Info`, `Stable
  Operation?` = Yes, `Actual Car Parking Revenue` = approved RP2 ÷ 12 and motorbike = approved RP1 ÷ 12, and the
  collect-on-behalf block from the approved RO3.<x> (water) and RO4.<x> (electricity) lines ÷ 12, the product by
  the catalogue's suffix. Every scale field the file does not carry is listed in `IMPORT NOTES`: a numeric one is
  written as 0 (what the tool reads as "not given", and what the M3 runs entered; a blank stops the generator with
  a bare TypeError), a text one stays blank; `--facts` (JSON of label → value, optional `_sources`) fills them and
  is recorded in the notes with the source text given. `City / Province` is one of them, and the water tariff
  needs it. *(The rates-and-parking part was put to the user, who chose the file, 2026-10-20.)*
- **D8 The `Prior-Year Budget` sheet.** Written by the import into the form (a fresh form from the builder, or a
  dated copy of `--input`, never the original). Block `PRIOR-YEAR BUDGET` with columns Fund Sheet, Section, Code,
  Item, Approved (VND/year), Includes VAT (Yes/No), the twelve months, Source Sheet, Source Row, Remark; block
  `IMPORT NOTES` with one row per note (kind, code or field, text). Read back by `review.py` through the same
  block-and-header reader as the other Existing sheets. The generators do not read it, so it changes no figure.
- **D9 The `Review` sheet.** Last sheet of `Project_Budget_Output.xlsx`, Vietnamese headings. Header block: file
  read, sheets, period, VAT bases, counts (lines read, lines with a figure, codes not on the form, lines unreadable).
  Summary table: Thu, Chi, Thặng dư of the Management Fund: approved (converted) vs tool, difference and %. Then per
  fund sheet, per section: one row per code (Mã, Hạng mục, Duyệt NS <year> như file, Hệ số VAT, Duyệt quy đổi, Công
  cụ NS <year>, Chênh, %, Cách công cụ ra số, Ghi chú), a subtotal row per section and a total per fund sheet. The
  item name is the catalogue's `item_vi` when the code is catalogued, else the file's own item text. Remarks: the
  import flags of the line and, for the carried-forward lines, the one-sentence adjustment the bridges already state.
- **D10 One command, isolated.** `python review.py <file> [--input form] [--facts json] [--workdir dir]` builds the
  form in the work folder (default `reports/review/<yyyymmdd-hhmm>/` under `Budget_Agent`, overridable), runs both
  generators through `verification.isolation.redirected_paths` so nothing in the live `reports/` or `sample_output/`
  moves, reads the deliverable through Excel, writes the Review sheet into the work folder's analysis workbook, prints
  the summary (totals, the ten largest differences, the counts) and writes `review_summary.md` and
  `review_summary.json` beside the outputs.
- **D11 New-prospect mode untouched.** No generator, builder or verification module changes. The A/B on the standard
  sample and the five fixtures must show no differing cell outside sheets that did not exist before.
- **D12 Tests on invented workbooks.** The reader is tested on a small workbook the test builds with the form's
  column conventions (code column, indicator, R / E / PL1 / PL2 rows, a year column that ties, twelve month columns,
  an untied second column, a code not on the 2027 form, a line without a code, a line whose months do not match);
  the form filler on the standard fixture; the Review sheet builder on a dictionary of figures, without Excel. No real
  file or name enters `tests/`.

## Risks

- A fund sheet whose leaf sums do not tie to its R and E rows (8 of 54 in the store) is read with the header-only
  value column and the approved column then cannot tie; the command says so and still writes the sheet.
- The deliverable's R and E rows include lines the import could not match (collect-on-behalf pairs, for example);
  the tool column keeps them under "Chỉ công cụ", so the tie to the deliverable holds.
- The tool's estimates for contracts (security, cleaning, M&E) will differ from the approved figures by design; the
  Review sheet is the evidence for the next change, not a defect of this one.
- Excel must be installed where `review.py` runs (as for the run log). Without it the command stops before the
  Review sheet and says so; the filled form and the three workbooks are still written.
