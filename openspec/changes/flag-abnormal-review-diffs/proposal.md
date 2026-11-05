## Why

Two of the PM team's stated expectations of the tool are not met in full (review of 2026-11-05):

- "Tự động so sánh và phát hiện chênh lệch bất thường": the Review compares every line and lists the 10 largest
  differences, but nothing on the page or in the analysis says which differences are *abnormal*. The top list is by
  absolute VND, so a small line that moved 300% never shows, and a PM reading 138 codes has to judge each one.
- "Giao diện trực quan, tích hợp tìm kiếm và lọc": since change `adjust-rows-for-zero-tool-codes` the adjust table of
  the CITY GARDEN review carries 102 "Nhập số" rows for codes the tool prices at 0, on top of the 36 priced codes. The
  user finds the table long and asked for a button that shows those rows on demand.

## What Changes

User's decisions on 2026-11-05 (AskUserQuestion): hide the zero-tool codes by default except the abnormal ones, with a
button that shows them all; abnormal = at least 20% and at least 50,000,000 VND/year against the approved figure; measure
on CITY GARDEN afterwards.

- **A rule for an abnormal difference.** On a Review, a line's difference (tool figure minus the approved figure
  converted to the deliverable's VAT basis) is *abnormal* when its absolute value is at least 50,000,000 VND/year **and**
  its absolute % of the approved figure is at least 20%. A line with no approved figure (the % cannot be computed) is
  abnormal when the absolute difference alone reaches 50,000,000 VND/year. Group rows and totals are never flagged.
  The two thresholds are constants in `review.py`; the page's guide and the Review sheet state them.
- **Where the flag shows.** Review sheet of the analysis: the "Chênh" and "%" cells of an abnormal line are filled
  light red and "BẤT THƯỜNG" opens the line's "Ghi chú"; the counts line (row 3) states how many lines are abnormal.
  `review_summary.json` / `.md`: the count, the list of abnormal lines (fund, code) and the rule. Review page: the count
  in the counts line, a tag on the abnormal lines of "10 dòng lệch lớn nhất". Adjust table: a tag "Bất thường" beside the
  code, the two "Chênh so với duyệt" cells filled light red, a filter "Chỉ dòng bất thường", and the count on the
  THU / CHI header rows.
- **Button "Mã công cụ ra 0".** On a Review run the adjust table hides, by default, every code whose tool figure is 0
  (the `zero_row` flag) *unless* it is abnormal; the button on the toolbar shows them all and shows how many are hidden.
  A new-project run has no such rows and no button. Sheet `4. Điều chỉnh` of the deliverable is unchanged: it keeps every
  row.

## Capabilities

### Modified Capabilities
- `budget-review-workflow`: the abnormal-difference rule on the Review sheet and in the summary files.
- `budget-web-adjust-table`: the "Bất thường" tag, filter and counts; the "Mã công cụ ra 0" button.
- `budget-web-review-results`: the count and the tag on the Review page.

## Impact

- Changed: `review.py` (`is_abnormal`, `abnormal` on each assembled row, counts, summary JSON / MD, Review sheet fill
  and remark), `webapp/adjust.py` (`abnormal_keys`), `webapp/server.py` (`abnormal_keys`, `abnormal_rule` in
  `GET /api/runs/<id>/adjust`), `webapp/static/index.html` (button, filter, tags, counts, guide text), `webapp/README.md`,
  `docs/32`, tests.
- Reads: nothing new. Writes: the Review sheet of the analysis workbook (fill and remark text), `review_summary.json`,
  `review_summary.md`. **No figure on the client deliverable moves**; the deliverable's sheet 4 is not touched.
- Runs made before this change have no `abnormal` list in their summary file: the web computes the flag from the
  table's own "Duyệt" and "Thành tiền gốc" with the same rule, so old runs show the tag too.
