## Context

- The management-fee hand-check lives in `verification/baseline.py`. It reads the project's areas from
  the input file by label (`read_sample_scale`), then opens a copy of the analysis workbook in Excel
  and multiplies each product's area by its fee in the `Management Fee` pricing table. The product
  list in that loop is written out by hand as three names. The tool's own list has nine
  (`PRODUCT_ROWS` in `generate_project_budget.py`), and the input form has one row for each.
- The "every Required code is filled" check lives in `verification/checks.py`
  (`check_required_line_items`). It accepts any non-empty remark on a zero Required line as the
  reason. Two lists in the same file, `_TEMPLATE_OWNED_TEXT_CELLS` (wording scan) and
  `_TEMPLATE_OWNED_T_ROWS` (line-remark scan), exempt the RP5 cell on `2.2 Common area Fund` because
  its "demo" text is the form's, not the tool's.
- `2.2 Common area Fund` is written by `fill_common_area_fund_sheet`. It copies zero reasons from
  `2. Budget-Management Fund`, but RP5 has no counterpart reason there (RP5 on that sheet is not a
  Required code and carries no remark), so the existing copy step does not reach it.
- Read on 2026-10-05 from a Diamond Skyline copy outside SharePoint (stored values, read-only), and
  against the Required reference (`data/master_list_verified/AI_Guideline_Required_Classification.csv`):
  RP5 on `2.2 Common area Fund` is the only code on either exemption list that is Required. ESA6, ESA11,
  ESA12, ESA16, VAT1, VAT2, CIT1, CIT1a, CIT1b and CIT2 are all Optional there, so the Required check
  never looks at them. Task 1.2 repeats the read with Excel's recalculated values before any edit.

## Goals / Non-Goals

**Goals:**
- The hand-check gives the right answer for a project with any mix of the nine products.
- The RP5 line on the client copy states why it is zero, and verification treats that remark like
  every other remark the tool writes.
- Verification can no longer pass a Required zero on the word "demo".

**Non-Goals:**
- No figure changes. RP5 stays at 0 VND; pricing visitor parking is a separate question (it needs a
  visitor-volume input the form does not have).
- The form itself is not edited. The word "demo" stays in the form, and docs/22 item C5 and its
  slide are not edited by this change.
- No change to the other form-owned cells on the two lists (VAT1, VAT2, CIT1, CIT1a, CIT1b, CIT2
  and the four ESA remarks).

## Decisions

**D1. Iterate over the tool's own product list, not a second hand-written list.**
The hand-check imports `PRODUCT_ROWS`, reads every product's area from the input file by label, and
sums over all of them. `read_sample_scale` returns one extra entry, a dictionary of product → area,
and keeps the existing keys that the parking check uses. A missing label already raises with the
label's name, which is the behaviour the spec asks for.
*Alternative:* add "Officetel" to the hand-written tuple. Rejected: it fixes today's project and
leaves the next product (Office, Retail, Villas) to fail the same way.

**D2. A product with an area but no fee counts 0 and is named.**
Chosen by the user on 2026-10-05. Leaving a product unpriced can be deliberate (the tool's own
remarks say so), so it does not fail the check on its own. The check's description lists each such
product, so a silent omission cannot recur. The anchoring rule stays: if a priced product's area in
the input differs from the workbook's by more than 0.5 m², the check fails.
*Alternative:* fail on any unpriced product. Rejected by the user.

**D3. The pipeline writes the RP5 reason itself (user decision 2026-10-05).**
One short step in `fill_common_area_fund_sheet`, next to the zero-reason copy: find the RP5 row by
its code in column Y, and write the reason only when column T is empty or exactly "demo". It uses
the same remark writer as other lines, so the VAT-treatment sentence is appended on an inclusive-of-VAT
run. This is needed because, once the exemption is removed (D4), the remark is checked for VAT
sentence and Vietnamese like all other remarks.
Reason, wording approved by the user on 2026-10-05: "Để ở mức 0: Doanh thu giữ xe hai bánh vãng lai
theo ngày phụ thuộc vào số lượt khách vãng lai mỗi ngày, mà hiện chưa có số liệu đầu vào nào cung cấp,
nên không tự đặt ra con số." (daily visitor parking revenue for two-wheelers needs an assumption about
visitor numbers, and no input in the tool supplies one, so no figure is invented). The writer also
requires that the line's rate cell is still blank or 0, because "left at zero" would be false for a
priced line.
*Alternatives:* (a) keep "demo" and mark RP5 "pending the template owner" in the check: rejected by
the user, because the client copy would still carry the word. (b) fail verification until the template
owner changes the form: rejected, verification would stay red for something the team cannot fix.

**D4. The two exemptions are removed, and the placeholder is matched by exact text.**
`('2.2 Common area Fund', 'T15')` leaves the wording-scan list and `('2.2 Common area Fund', 'RP5')`
leaves the line-remark list. A new small mapping `(sheet, code) → placeholder text` holds the one
entry ("demo"), and the Required check treats a remark equal to that text as no reason. Matching is
on sheet, code and exact text, never on the word "demo", in line with how the file already lists
exempt cells (explicitly, never by pattern). If the pipeline ever stops writing the reason, three
checks fail together (Required, wording scan, line-remark scan), and each names the cell.

## Risks / Trade-offs

- [The removal makes verification fail if the new remark is written wrongly (English, no VAT
  sentence, an internal word)] → this is the point; task 3.1 writes it to pass all three checks and
  task 4.2 runs the full verification.
- [The form's owner later replaces "demo" with other text] → the pipeline then leaves that text
  alone (D3), the Required check accepts any non-empty text other than the placeholder, and the
  wording scan checks it. No code change needed.
- [docs/22 item C5 and its slide still say "demo" reaches the client] → true of the form, no longer
  true of the tool's output. Left for the user to decide (see proposal, Impact).
- [One client-visible wording change with no PM sign-off step] → no number moves; the before/after
  comparison in task 4.1 proves T15 is the only cell that differs.

## Migration Plan

No data migration. Roll back by reverting the three code files. Nothing is committed or pushed in the
inner repository until the user asks.
