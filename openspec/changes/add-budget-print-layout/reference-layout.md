# Reference layout: approved sample vs the 2027 form

Read on 2026-11-11. This file records only layout and roles: no person names, project names or amounts.

## Sources

| Source | Kind | Coverage |
|---|---|---|
| `input/budget_planning/Ngân sách thực tế dự án lập hằng năm (có số liệu báo cáo)/Budget 2026/1A - Dự toán ngân sách Quỹ vận hành năm 2026 (Final).pdf` | Approved Management Fund budget 2026, signed and stamped, scanned | 4/4 pages |
| `input/template/2027 Resi Budget Form (IT team).xlsx` (2026-09-17) | Current Resi form. `202608 - 2027 Resi Budget Form.xlsx` is older | 24/24 sheets; sheet 2 is A1:BN536 |
| `Budget_Agent/sample_output/Diamond Skyline - Sample Consulting Budget.xlsx` | Fictional sample deliverable | Used for trial exports only |

## Comparison

| Item | Approved sample (PDF) | 2027 form / current deliverable |
|---|---|---|
| Paper | A3 landscape, 4 pages | A3 (paperSize 8), landscape, fit 1 page wide. No print area, print titles, footer or page breaks |
| Columns printed | No, Code, Items; approved last year (total only); expected report (total only); estimate (total, monthly average); 2 × % change; Remarks | X No, Y Code, Z Items; AB:AC approved (total, avg); AE actual; AF expected rest of year; AH:AI report (total, avg); AK:AL estimate; AM, AN %; AO Remarks; AQ:BB 12 months |
| Group spacers | Narrow blank columns between groups | AA, AD, AG, AJ, AP (width 3–4) |
| Title block | Page 1 only: fund title, project, budget year, start/end month | Rows 2–7 (X:AL) |
| Repeated header | Column headings on every page | Rows 9:10 (not set) |
| Rows printed | Lines in use. Lines with a prior-year figure or a remark print even when the estimate is 0. Top-level groups (VI, VII) print at 0; empty dotted sub-groups (II.2, II.3, II.6, IV.4, V.1–V.32) do not | Column B `=IF(AND(AC=0,AM=" ",AO=" "),"Not Use","Use")` with an AutoFilter. On the fictional sample: 87 Use / 404 Not Use, none hidden |
| Page breaks | Automatic, not by group | None set |
| Footer | "Page x of y", centred | None |
| Check row | — | Row 506 prints a red "TRUE"; rows 507–513 are blank spacers about 270 pt high |
| Signature block | Last page, 8 boxes in one row under the table. Đề xuất: Trưởng Ban Quản lý. Phê duyệt: Trưởng Ban quản trị, 2 × Phó Ban quản trị, 4 × Ban quản trị. Each box: heading, role, "(Ký tên, ghi rõ họ tên)", typed name, "Ngày: __/__/__"; owners' committee stamp | Rows 514–526, 6 boxes. Đề xuất: Trưởng Ban Quản lý (Z). Xem xét: Đại diện VPC Savills (AH). Phê duyệt: Ban quản trị × 4 (AQ, AT, AW, AZ). An A4 print of X:AO keeps only the first 2 |
| Initials | Handwritten initials bottom-right of pages 1–3 (not printed) | — |
| Fonts | Scan; readable | Arial 10 in the table, 20 for the title, 14 for the signature block |

## Column check (rows 9–10)

- X9 is "No | Stt". AO9 is "Remarks | Ghi chú".
- BB10 is the 12th month: AQ10 is the start month (AH6), and each next column adds one month. BB reads "Dec/yyyy"
  only when the budget starts in January. The form's default start is September, so BB reads Aug.
- A:W is the working area: C frequency, F unit price, H:S schedule, T the internal remark that AO shows, U:V checks.
  The line code is in Y.

## Trial exports (fictional sample; copies, never saved)

| Setup | A4 X:AO | A3 X:BB |
|---|---|---|
| All rows | 28 pages | 18 pages |
| Not Use and 506 hidden, all columns | 8 pages, body text about 3.4 pt | 5 pages, about 3.1 pt |
| Same, AC/AE/AF/AI hidden | 12 pages, about 4.7 pt | 6 pages, about 4.0 pt |
| Same, plus only top-level groups forced visible and 506–513 hidden | 11 pages | 6 pages |

For comparison, the approved sample on A3 with No-to-Remarks and 4 numeric columns is about 6.8 pt in the same trial
setup. The tool's remarks in AO are long, so rows are tall and the page count is higher than the sample's 4.
