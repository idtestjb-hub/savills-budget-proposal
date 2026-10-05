## Why

Reading every remark of one generated project (`docs/23-doc-ghi-chu-diamond-skyline-2026-10-04.md`)
found text in the client deliverable that is wrong, confusing, or written for the tool's developers
rather than for the Developer reading it, while `verify.py` stayed green:

- `1. Summary` K14 and K15 quote a monthly fee and parking price that are the year-1 average after the
  occupancy ramp, not the unit price the lines are priced at: "4,306 VND/m²/month" where the apartment
  rate is 15,900; "29,792" and "297,917" where the parking prices are 110,000 and 1,100,000.
- The EMH2 remark carries another project's figure ("638.780.247 VND, theo ví dụ Wayne Tower"), a
  remark about the tool's earlier method, and the words "ước tính Python riêng".
- `0. Info` G21 names a function (`derive_product_rate`) and `Comparison` A2 names a file
  (`master_comparables.py`).
- `1. Summary` K30 says "3 nhân viên vệ sinh bao gồm: 3 …, 1 Giám sát", which reads as four.
- The water remark gives two sources for one price; the water, electricity and diesel remarks use
  change-process language ("thay đổi này tách riêng đơn giá, không mở rộng mẫu tham chiếu") and name
  an internal document ("AI Guideline") and a statistical shorthand ("n=1").
- `1. Summary` K22 says "19 vị trí" while the EMA7 remark says "27 nhân sự BQL": different counts of
  the same group, neither with its basis stated (19 positions on duty per day; 27 people once the
  7-in-6 rest rotation is counted).

Verification did not catch these because the internal-artifact check reads only column T of the two
fund sheets against a short keyword list, and the narrative checks look at structure, not at the
numbers or wording inside.

## What Changes

- K14 and K15 quote the unit prices the RM and RP lines use.
- The EMH2 remark describes what the figure is made of and stops there: no other project, no history of
  the previous method, no mention of the language the tool is written in.
- `0. Info` G21 and `Comparison` A2 say what the rate or comparison is, in plain terms.
- K29 and K30 list the posts so that the list adds up to the stated total, and show the supervisor
  as a separate, unpriced post.
- K22 and the EMA7 remark each state their counting basis.
- The water remark gives one source for its price; the three consumption remarks keep their dated-price
  and single-reference caveats, rewritten in terms a Developer can read.
- Verification scans every text cell of the client deliverable on every sheet for internal wording
  (function and file names, "Python", change-process phrases, internal document names), with the
  template's own text on an explicit exemption list.
- **Not in this change:** the pointer "dựa trên trang A2/A3" in K29/K30 (its fate depends on the open
  decision about the template-example sheets, `docs/22` D2); the dropped second Accountant row in A1
  and anything else that moves a figure (`docs/24`); the template-owned text ("demo", the
  "[Lưu ý nội bộ]" notes, the K16/K17 typo).
- No figure moves. Remarks are not a baselined figure, so no baseline is re-recorded.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `deliverable-remarks`: adds requirements on what quoted rates and counts mean, that listed items add up,
  that client-facing text contains no internal wording on any sheet, and that verification scans for it.

## Impact

- `generate_project_budget.py`: the narrative composers (`_recipe_narrative` for RM, RPa, the staff and
  the security/cleaning rows), the EMH2 remark, the `0. Info` G21 text, the `Comparison` sheet title
  line, and the water/electricity/diesel remark builders.
- `verification/checks.py`: the artifact check becomes a whole-workbook scan with an exemption list.
- No generated number, formula, sheet layout, template file, baseline file or input form changes.
