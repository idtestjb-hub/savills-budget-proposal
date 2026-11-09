## Why

When the PM changes a line's frequency offline in Excel (sheet `4. Điều chỉnh`, cells AE..AX), the remark on the fund
sheet still carries the old frequency sentence. The web adjust table flags the line "Remark chưa theo tần suất mới",
but the only way to fix it today is to open each flagged line and save it again on the web. With many flagged lines
this is slow and easy to miss (user, 2026-11-09: the web keeps the flag and gains a button that fixes the flagged
remarks; rules in `docs/05-decisions.md`, "Stale frequency remark: a fix button on the web").

## What Changes

The six rules approved by the user on 2026-11-09:

- **A button "Cập nhật remark (n dòng)"** on the adjust table toolbar, beside "Lưu điều chỉnh vào bản giao". It shows
  only when at least one line is flagged; n is the number of flagged lines. It is locked while the page holds unsaved
  edits ("Lưu hoặc bỏ thay đổi chưa lưu trước").
- **Which lines:** exactly the lines the web flags today (`remark_stale`): a non-zero line whose last remark sentence
  does not match its current frequency. Zero lines, and lines the tool wrote Monthly or Schedule that the PM has not
  changed, are never touched.
- **What changes:** only the frequency sentence at the end of the remark (the sentence the tool writes, known by its
  fixed lead). The PM's own text above it is kept. A line now Monthly loses the sentence; a remark without one gains it
  at the end.
- **The sentence** is built from the frequency and the amount now on sheet 4 (price per time = annual amount ÷ number
  of times), the same sentence a web save writes.
- **No figure moves:** only column T (Remarks) of `2. Budget-Management Fund` or `2.2 Common area Fund` is written;
  no cell of sheet 4 changes. A remark that is an Excel formula is skipped and listed by code.
- **Writing goes through the existing save path:** the same queue, the dated backup beside the deliverable, the Excel
  recalculation and the page reload; the result line states how many remarks were fixed and which were skipped.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `budget-web-adjust-table`: a new requirement for the fix button.

## Impact

- **Code:** `webapp/adjust.py` (`apply_edits` accepts a remark-only fix edit; a helper builds the fixed remark),
  `webapp/adjust_run.py` (result counts fixed and skipped remarks), `webapp/static/index.html` (button, lock, result
  text). The server route `POST /api/runs/{id}/adjust` is reused unchanged.
- **Data files:** reads and writes only the run's deliverable (column T of the two fund sheets) and its dated backup;
  writes the run's `adjust_result.json` / `adjust_state.json` as every save does. No reference CSV changes.
- **Recorded baselines:** none move (the generator is not touched; the button only runs on a saved deliverable).
- **Also fixed:** a web save that changes a frequency today overwrites a remark that is an Excel formula with the
  sentence alone; under this change that save keeps the formula and reports the line as skipped, as the button does.
