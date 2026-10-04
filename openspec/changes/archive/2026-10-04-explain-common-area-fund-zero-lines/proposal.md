## Why

Two pieces of client-facing text on the deliverable are still incomplete after the 2026-09-21
changes:

1. On `2.2 Common area Fund`, 32 lines the AI Guideline marks *Bắt buộc / Required* show 0 VND with
   an empty Remarks cell. The zero itself is correct: each line is a share of the matching
   `2. Budget-Management Fund` line, and that line is 0 VND with a stated reason. But a reader of
   `2.2` sees an unexplained zero on a Required line, and verification only reports this sheet
   instead of failing on it (`checks.py`, `_REQUIRED_CLASSIFICATION_ENFORCED_SHEETS`).
2. The energy remarks are Vietnamese except for their unit labels, which still read "m3/month",
   "kWh/month" and "litre/month". The project rule is Vietnamese-only remarks.

## What Changes

- Every Required line on `2.2 Common area Fund` that is 0 VND because its `2. Budget-Management
  Fund` counterpart was left at 0 VND with a stated reason in the same run gets that same reason in
  Vietnamese in its own Remarks cell (column T), marked as an allocation from `2. Budget-Management
  Fund`. The list of lines comes from the reasons actually written on `2. Budget-Management Fund`
  in that run, not from a fixed list, so a line that later gets priced (for example EMH1 once the
  PM enters Savills' fee terms) stops getting a zero reason on both sheets at once.
- EMA1–EMA4 keep their existing arrangement (the reason sits on EMA15's remark); `2.2`'s EMA15 row
  gets the matching remark.
- Verification fails when a Required line on `2.2 Common area Fund` is zero with no stated reason,
  the same rule `2. Budget-Management Fund` already has.
- The Vietnamese energy remarks show "m3/tháng", "kWh/tháng" and "lít/tháng". The internal analysis
  workbook (English) and the source data in `Fact_OPEX.csv` keep their English units.
- No figure moves. Remarks only; no baseline is re-recorded.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `guideline-required-line-items`: the stated-reason rule and its verification now cover
  `2.2 Common area Fund` as well as `2. Budget-Management Fund`.
- `deliverable-remarks`: unit labels inside a Vietnamese remark are Vietnamese.

## Impact

- `generate_project_budget.py`: the flagged-zero remark writers (`_FLAGGED_NO_METHOD` block, the
  EMH1/ESI1 remarks, the EMA15 catch-all) also write to `2.2 Common area Fund`; the energy remark
  phrase (`_energy_narrative_vi`, shared by the summary and line-level remarks) translates unit labels.
- `verification/checks.py`: `_REQUIRED_CLASSIFICATION_ENFORCED_SHEETS` gains `2.2 Common area
  Fund`; the energy remark anchors require the Vietnamese units (`m3/tháng`, `kWh/tháng`,
  `lít/tháng`).
- Client deliverable: about 33 new Vietnamese remark cells on `2.2 Common area Fund`; three energy
  remarks change wording. No VND figure on any sheet changes.
- Not touched: `Fact_OPEX.csv`, `estimate_opex.py`, the analysis workbook, the Fact/Dim join keys.
