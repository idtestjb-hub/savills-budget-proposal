## ADDED Requirements

### Requirement: The adjust table fixes the flagged frequency remarks with one button
The web adjust table SHALL show a toolbar button "Cập nhật remark (n dòng)" whenever n ≥ 1 lines carry the note
"Remark chưa theo tần suất mới", and SHALL NOT show it when no line does. The button SHALL be locked while the page
holds unsaved edits or a save is running. Pressing it SHALL, through the same save path as "Lưu điều chỉnh vào bản giao"
(lock-file check, dated backup beside the deliverable, Excel recalculation, page reload), rewrite for each flagged line
only the frequency sentence at the end of its remark in column T of `2. Budget-Management Fund` or `2.2 Common area
Fund`:
- the sentence SHALL be the one a web save writes for the line's current frequency and amount on sheet
  `4. Điều chỉnh` (price per time = annual amount ÷ number of times);
- the PM's own text before the sentence SHALL be kept; a line now Monthly SHALL lose the sentence; a remark without a
  sentence SHALL gain it at the end;
- a remark that is an Excel formula SHALL be left unchanged and listed by code as skipped;
- no cell of sheet `4. Điều chỉnh` and no figure of the deliverable SHALL change: the totals R, E and surplus of both
  funds after the recalculation SHALL equal those of the previous save.

Lines not flagged (zero lines, lines the tool wrote Monthly or Schedule and the PM did not change, lines whose remark
already matches) SHALL NOT be touched. After the reload the result SHALL state how many remarks were fixed and list
the skipped codes, and no fixed line SHALL be flagged any more. A web save that changes a frequency SHALL also keep a
formula remark unchanged and report it as skipped. Data files: the run's deliverable and its backup, the run's
`adjust_result.json` and `adjust_state.json`; no recorded baseline figure moves.

#### Scenario: Three lines changed offline
- **WHEN** the PM changed ESM25 to Half a Year from T1 and ESC4 to Yearly in T6 in Excel, set ESM3 back to Monthly, and
  opens the adjust table
- **THEN** the three lines show "Remark chưa theo tần suất mới" and the toolbar shows "Cập nhật remark (3 dòng)"
- **AND** after pressing it, ESM25's remark ends with "6 tháng/lần, 2 lần/năm × <annual ÷ 2> VND/lần, chi vào T1, T7",
  ESC4's ends with "Hàng năm, 1 lần/năm × <annual> VND/lần, chi vào T6", ESM3's sentence is gone, the PM text above
  each sentence is unchanged, the result reads "Đã cập nhật remark 3 dòng" and no line is flagged

#### Scenario: Unsaved edits lock the button
- **WHEN** the PM has typed an inflation on another line and not saved it
- **THEN** the button is locked and its tooltip asks to save or discard the unsaved changes first

#### Scenario: A formula remark
- **WHEN** one flagged line's remark cell holds an Excel formula
- **THEN** that cell is unchanged, the result lists the code as skipped ("remark là công thức Excel"), and the other
  flagged lines are fixed

#### Scenario: Nothing flagged
- **WHEN** no line carries the note
- **THEN** the button is not shown
