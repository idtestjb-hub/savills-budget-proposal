## Context

`webapp/adjust.py` `read_items` sets `remark_stale` on each item (`remark_stale`, around line 272): the line is
non-zero, it is not a tool-written Monthly/Schedule line left as is, and the last line of the remark differs from
`freq_sentence(item)` (None for Monthly, where a leftover sentence is stale). The web shows the note under the remark
(`index.html`, "Remark chưa theo tần suất mới").

A web save posts `edits` to `POST /api/runs/{id}/adjust`; the server dry-runs `apply_edits` on the deliverable, then
queues `webapp/adjust_run.py`, which checks the Excel lock file, backs up the deliverable, applies the edits, saves,
recalculates a copy in Excel and writes `adjust_result.json`. A frequency edit goes through `_write_freq`, which
replaces the remark's last sentence with `lf.with_sentence(current, freq_sentence(item, amount, freq))`; a formula
remark is read as '' there and so overwritten.

`_fund_remark` already returns '' for a formula remark, so a formula remark on a non-Monthly line is flagged stale
today (empty last line ≠ wanted sentence).

## Goals / Non-Goals

**Goals:** one click fixes every flagged remark; nothing but the frequency sentence in column T changes; same backup,
lock check and recalculation as any save; the PM sees how many were fixed and which were skipped.

**Non-Goals:** changing what is flagged; fixing remarks the web does not flag; rewriting the PM's own text; changing
the frequency sentence wording; an Excel-side macro.

## Decisions

**D1. A remark-only edit on the existing route.** An edit `{key, fix_remark: true}` (no other keys) means: rewrite the
frequency sentence of this code's remark from the saved sheet-4 state, and write nothing on sheet 4. `apply_edits`
handles such edits in their own branch: it validates the key, skips `_validate`, `_write_freq`, the sheet-4 cells and
`_pm_remark`. Alternative considered: the browser resends each flagged line with its current adjustment values and a
recomputed remark — rejected, it would rewrite sheet-4 input cells (risking a moved figure) and would need a copy of
the sentence rules in JavaScript.

**D2. The fixed remark.** `fixed_remark(item, current)` = `lf.with_sentence(current, freq_sentence(item))`, where
`item` is the code as `read_items` builds it from the saved workbook (the same amount the web shows as "Thành tiền
mới"). This is the rule a web frequency save applies (D8 of the archived `add-line-frequency`), so a fixed line is no
longer flagged on reload. The server re-checks `remark_stale` before writing: a line that is not stale any more (the
PM fixed it in Excel meanwhile) is left alone and not counted.

**D3. Formula remarks are skipped.** When column T holds a formula (`=...`), the edit writes nothing and the code is
returned in a `skipped` list with the reason "remark là công thức Excel". The same guard is added to `_write_freq`:
a frequency save keeps a formula remark and reports the code as skipped, instead of overwriting it.

**D4. Result.** `apply_edits(wb, edits, report=None)` still returns the written codes, so existing callers and tests
are unchanged; when the caller passes a dict as `report`, it is filled with `remarks_fixed` (codes) and
`remarks_skipped` (code + reason), from both the fix edits and the frequency saves of D3. `adjust_run.py` passes one. `adjust_result.json` gains
`remarks_fixed` (count and codes) and `remarks_skipped`; the web result line reads "Đã cập nhật remark n dòng" and
lists skipped codes. The Excel recalculation still runs (rule 5) and its R / E / surplus must equal the previous save.

**D5. The button.** Shown when `items.filter(remark_stale).length > 0`, label "Cập nhật remark (n dòng)". Disabled,
with a title explaining why, while any row is dirty or a save is running. On click it posts the fix edits for every
flagged key and follows the job exactly as the save button does (progress bar, log, reload).

## Risks / Trade-offs

- [The deliverable is open in Excel on the server] → the existing lock check stops the save with its message.
- [A remark ending with a line that merely looks like a sentence, typed by the PM] → `lf.is_sentence` recognises only
  the tool's fixed leads ("Hàng quý", "6 tháng/lần", "Hàng năm", "Chi theo lịch từng tháng", "<n> lần/năm, … VND/lần");
  such a PM line would be replaced, as on a web save today. Accepted (same rule as D8).
- [A recalculation for a save that moves no figure costs about a minute] → accepted for one path and one backup rule.
