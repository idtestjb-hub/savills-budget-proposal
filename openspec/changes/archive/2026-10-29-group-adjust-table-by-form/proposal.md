## Why

The Review sheet in Excel groups its lines as on the 2027 form (EM → EMH, EMA…, a "Cộng" row per group), but the
web adjust table only splits Thu / Chi, so a PM cannot read the table the way the workbook reads. The user asked
(2026-10-28) to group the adjustment items as in Excel.

## What Changes

- `GET /api/runs/{id}/adjust` adds to each item its chain of form groups (`review_import.group_chain`, the same as the
  Review sheet, without the code itself) and its template row; codes not on the form get one group "Mã ngoài form 2027".
- The adjust table sorts each of Thu / Chi by fund (MF, then CA) and template row and nests every group level, each
  with a "Cộng <mã> · <tên tiếng Việt>" row that sums the shown codes in the money columns (N-1, Duyệt, gốc, mới,
  chênh lệch, %). A ▾/▸ button folds a group as an Excel outline; "Mở mọi nhóm" / "Thu gọn mọi nhóm" act on all.
  The group rows refresh while the PM edits.

User's choices on 2026-10-28: every level as on the Review sheet; "Cộng" rows with figures and fold/unfold, open by
default.

## Capabilities

### New Capabilities

### Modified Capabilities
- `budget-web-adjust-table`: the table is grouped as on the 2027 form.

## Impact

- `webapp/adjust.py` (`add_groups`), `webapp/server.py` (GET adjust), `webapp/static/index.html` (table, buttons, CSS).
- No change to saving, to the deliverable or to any figure; the group rows are page sums of the codes on the table.
