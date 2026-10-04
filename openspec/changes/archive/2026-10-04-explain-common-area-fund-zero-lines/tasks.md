## 1. Record the zero reasons written on `2. Budget-Management Fund`

- [x] 1.1 In `generate_project_budget.py`, add one per-run dict `code → Vietnamese reason text`
  (the text before `_write_remark` appends the VAT sentence)
- [x] 1.2 Record into it from the `_FLAGGED_NO_METHOD` loop, the EMH1 remark (only on the branch
  that writes it, i.e. no Savills fee terms entered) and the ESI1 remark

## 2. Write the matching remarks on `2.2 Common area Fund`

- [x] 2.1 After `2. Fund` is filled, scan `2.2`'s code column (Y) and, for each recorded code
  found, write `Để ở mức 0 (phần phân bổ từ '2. Budget-Management Fund'): <reason> …` through
  `_write_remark` (design D2, D4); skip a cell that already holds non-whitespace template text.
  Amended: allocation rows only; EM#/ES#/EE# (the sheet's own contingency rows) get the reason
  without the allocation wording (design D4 amendment)
- [x] 2.2 Write the figure-free EMA15 remark on `2.2` covering EMA1–EMA4 (design D3)
- [x] 2.3 Generate the standard sample in an isolated workdir and read back `2.2`: 32 zero
  Required lines + EMA15 carry the remark; no VND figure differs from the 2026-10-04 run

## 3. Vietnamese unit labels

- [x] 3.1 In `_energy_narrative_vi`, translate the consumption and tariff unit labels (design D5)
- [x] 3.2 Read back the EEW/EEE/EED remarks on `1. Summary` and `2. Budget-Management Fund`:
  "m3/tháng", "kWh/tháng", "lít/tháng", "VND/lít"; the analysis workbook still shows English units

## 4. Verification

- [x] 4.1 `verification/checks.py`: add `2.2 Common area Fund` to
  `_REQUIRED_CLASSIFICATION_ENFORCED_SHEETS`; replace the stale "not failed here" note and comment.
  Also: scan each sheet's whole used range instead of rows 1–495 / 1–300 (design D4a); `verify.py`
  failure/OK messages name both sheets
- [x] 4.2 In `_REMARK_RECIPE_ANCHORS`: EEW `m3/month` → `m3/tháng`; add `kWh/tháng` to EEE and
  `lít/tháng` to EED (design D6)
- [x] 4.3 Negative test on a copy of the generated deliverable: blank one `2.2` zero-line remark →
  `check_required_line_items` fails and names `2.2` and the code; blank `2.2`'s EMA15 remark →
  fails for EMA1–EMA4
- [x] 4.4 Negative test: an EEW, EEE or EED narrative carrying its English unit ("m3/month",
  "kWh/month", "litre/month") fails the remark-content check
- [x] 4.5 `python verification/verify.py` PASS end to end; both baselines unchanged (no re-record)

## 5. Docs

- [x] 5.1 `docs/05-decisions.md` entry; `docs/project-status.md` updated
- [x] 5.2 Note in `docs/14-required-line-item-gaps.md` that `2.2` now carries its own reasons
