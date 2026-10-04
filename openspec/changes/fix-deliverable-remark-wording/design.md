## Context

The client-facing text this change touches is written by a handful of composers in
`generate_project_budget.py`: the `1. Summary` narratives (`_recipe_narrative`, keys RM, RPa, the
staff row, ESS1/ESS4), the EMH2 remark (around line 1899), the `0. Info` G21 text (around line 3218),
the `Comparison` title line, and the water/electricity/diesel remark builders (around lines 1187 and
2309-2325). The current internal-artifact check in `verification/checks.py` reads column T of the two
fund sheets against a short keyword list. Findings and cell references: `docs/23`, `docs/24`.

See proposal.md for why.

## Goals / Non-Goals

**Goals:**
- Every rate, count and list in the touched text is true and adds up.
- No cell the pipeline writes contains internal wording, and verification proves it on all sheets.

**Non-Goals:**
- No figure, formula or layout change; remarks are not baselined.
- No change to template-owned text, nor to the pointer "dựa trên trang A2/A3" (awaits `docs/22` D2).
- No decision about naming reference projects in the deliverable (`docs/22` D3). Wording that names one
  stays as it is until that is decided.

## Decisions

**1. Quote the price the line uses, taken from the same value that prices the line.** The RM narrative
reads each RM line's unit price (the figure its own remark already quotes) instead of computing
`year-1 revenue / (12 x NFA)`; the RPa narrative reads the RP1/RP2 unit prices instead of
`revenue / 12 / slots`. Alternative: keep the division and rescale by the average ramp. Rejected: it
re-derives a number the pipeline already holds, and breaks again if the ramp changes.

**2. Wording is proposed in a table and approved before it is written (task 2.1).** The Vietnamese
replacements are client-facing text, so they are reviewed as text, not as code. Candidates:

| Cell | Replace | With |
|---|---|---|
| `2. Budget-Management Fund` T (EMH2) | the last sentence ("Cách tính này thay thế công thức tắt trước đây … 638.780.247 VND, theo ví dụ Wayne Tower"), "(không phải một số ước tính Python riêng)", and "các khoản phụ cấp riêng nhỏ hơn" | Drop the first two; say "các khoản phụ cấp riêng của từng vị trí"; the cell address `'A1…'!AC96` and "dòng 98-99" stay (an auditor uses them) |
| `0. Info` G21 | "…cùng phương pháp derive_product_rate với các sản phẩm khác (2 dự án tương đồng gần nhất, dự phòng theo đơn giá Apartment…)" | "…cùng phương pháp với các sản phẩm khác (2 dự án tham chiếu gần nhất; dùng đơn giá căn hộ nếu không có dự án tham chiếu cho sản phẩm này)…" |
| `Comparison` A2 | "…the real projects in master_comparables.py ranked by…" | "…the real projects in the reference list, ranked by…" |
| `1. Summary` K30 | "Dự ước 3 nhân viên vệ sinh bao gồm: 3 Vệ sinh khu vực công cộng, 1 Giám sát" | "Dự ước 3 nhân viên vệ sinh tính tiền: 3 Vệ sinh khu vực công cộng. Giám sát (1 vị trí) không nằm trong khoản này" |
| `1. Summary` K22 | "(19 vị trí, chưa gồm bảo vệ/vệ sinh/cây xanh — thuê ngoài)" | "(19 vị trí làm việc mỗi ngày, chưa gồm …)" |
| `2. Budget-Management Fund` T (EMA7) | "27 nhân sự BQL" | "27 nhân sự BQL (tính theo số người, gồm cả vòng nghỉ 7/6)" |
| T and K for EEW.C (water) | "Đơn giá nước lấy theo các dự án chung cư cùng quy mô" when the price is the guideline's example | "Đơn giá nước theo ví dụ trong hướng dẫn lập ngân sách, năm 2026" |
| T for EEW.C, EEE.C, EED.C | "(n=1 — một dự án tham chiếu duy nhất; thay đổi này tách riêng đơn giá, không mở rộng mẫu tham chiếu), nên việc áp dụng đúng phương pháp của bộ tiêu chuẩn không đồng nghĩa với số liệu đã chính xác" | "(chỉ một dự án tham chiếu), nên đây là ước tính ban đầu; cần đối chiếu với số liệu của dự án này khi có" |
| 9 cells naming "AI Guideline", 8 cells with "n=1" | the document name; the shorthand | "hướng dẫn lập ngân sách của Savills"; "chỉ một dự án tham chiếu" |

**3. One whole-workbook scan replaces the column-T keyword check.** Forbidden words live in one list in
`verification/checks.py` (function and file names of the tool, "Python", "thay đổi này", "AI Guideline",
"derive_", ".py", ".csv", ".md"); the exempt template cells in a second list (today: `2.2 Common area
Fund`!T15 "demo", the `[Lưu ý nội bộ…]` notes at T460:T465, and whatever else the first run flags that
the standard form itself contains). The scan reports cells scanned and cells exempt. An exempt cell
whose text differs from the template's fails too, so the exemption cannot hide a pipeline-written cell.
Alternative: scan only the sheets the pipeline writes. Rejected: `0. Info` and `Comparison` are
pipeline-written and were the ones missed.

**4. Proof that no number moved.** Before editing, generate the sample deliverable and keep it; after,
generate again and compare every cell: formulas and numeric values identical, text different only in the
cells in the table above. This is a stronger statement than a green `verify.py`, which does not look at
remark text.

## Risks / Trade-offs

- The word list will flag legitimate text now and then (a project called "…md…"). Exemptions are explicit
  and per cell, so a false positive is fixed by listing one cell, not by loosening the list.
- Quoting the priced unit rate in K14 means a reader who divides the narrative's revenue by area gets a
  different number, which is correct: the narrative says year-1 revenue is ramped.
- Rewording a caveat can soften it. Each rewritten caveat keeps both facts (single reference project;
  dated price) and the check in task 2.2 compares the facts, not just the words.
- "AI Guideline" appears in the deliverable's internal logic comments too; only cell text changes here.

## Open Questions

- Replacement name for the internal guideline in client text: "hướng dẫn lập ngân sách của Savills"
  (proposed) or no source named. Resolved in task 2.1.
- Whether raw cell addresses (`'A1…'!AC96`) stay in client remarks. Proposed: stay (auditors use them).
  Resolved in task 2.1.
