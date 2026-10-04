## Context

`2.2 Common area Fund` has carried a live share of each `2. Budget-Management Fund` line since
`activate-common-area-fund-cost-share` (archived 2026-09-21). The verification run of 2026-10-04
reports 32 Required codes on `2.2` at 0 VND with an empty Remarks cell (column T, header row 9,
confirmed on the standard form): EMH1, EMH3, EMA1–4, EMB1, EMB4, EMO2, EMO6, EM#, ESC1/2/4/5,
ESS10/12/17/18/19/23, ESI1, ESI2, ESM6/7/9/10/12/13, ESR, ES#, EE#. Every one of them is 0 VND on
`2. Budget-Management Fund` too, where it carries a Vietnamese reason written by:

- the `_FLAGGED_NO_METHOD` / `_FLAGGED_NO_METHOD_VI` loop (`generate_project_budget.py` ~2516–2646);
- the EMH1 remark, written only when no Savills fee terms were entered (~2490);
- the ESI1 remark (~2496);
- EMA15's catch-all remark, which `checks.py` (`_REQUIRED_CODE_DISCLOSED_ON`) accepts for EMA1–4.

Two template cells on `2.2` (ESS19, ESM10) hold a single space; every other one is empty.

The energy remarks come from `_energy_narrative_vi`, which inserts `usage_unit` and `tariff_unit`
from `estimate_opex()`. Those come from `Fact_OPEX.csv`'s English `Unit` column ("m3/month",
"kWh/month", "litre/month"), which the English analysis workbook also displays.

## Goals / Non-Goals

**Goals:**
- Each zero Required line on `2.2` explains itself in Vietnamese, in the same words as
  `2. Budget-Management Fund`.
- Verification enforces the rule on `2.2`.
- Vietnamese remarks carry Vietnamese unit labels.

**Non-Goals:**
- Pricing any of these codes (each needs its own data or PM decision).
- Changing the allocation basis of `2.2` (open PM question).
- Changing `Fact_OPEX.csv`, `estimate_opex.py` or the analysis workbook.

## Decisions

**D1. One record of zero reasons, filled where `2. Fund` writes them.** Each place above that
writes a zero reason on `2. Budget-Management Fund` also records `code → reason text` (the text
before `_write_remark` appends the VAT sentence) in one dict for the run. After `2. Fund` is done,
one pass writes the `2.2` remarks from that dict. Alternative rejected: a fixed list of 32 codes,
which would go stale the moment a code is priced (EMH1 is priced whenever a PM enters fee terms).

**D2. Wording: a full copy, marked as an allocation** (user decision 2026-10-04, "chép đủ lý do").
`2. Fund` writes `Để ở mức 0: <reason> …`; `2.2` writes
`Để ở mức 0 (phần phân bổ từ '2. Budget-Management Fund'): <reason> …`, i.e. the same text with
the opening phrase extended. `_write_remark` then appends the VAT sentence as on every other remark,
so the existing VAT and Vietnamese-content checks cover the new cells unchanged. None of these
reasons quotes a VND figure, so copying them onto a sheet with different amounts cannot mislead.

**D3. EMA1–4 stay disclosed on EMA15.** `2.2`'s EMA15 line is not zero (it is a share of the
`2. Fund` catch-all), so its `2. Fund` remark, which is written for that sheet's own figures, is not
copied. Instead `2.2`'s EMA15 gets a short remark without figures: it is the allocated share of
`2. Budget-Management Fund`'s EMA15, and EMA1–EMA4 have no itemised source, so they are folded into
it. This keeps `_REQUIRED_CODE_DISCLOSED_ON` valid on both sheets.

**D4. Rows on `2.2` are found by code, not by row number.** The pass scans `2.2`'s code column (Y)
for each recorded code, the same way `checks.py` does, because `2.2`'s row numbers differ from
`2. Fund`'s. A recorded code not found on `2.2` is skipped. A cell already holding non-whitespace
template text is never overwritten.

*Amended during implementation (2026-10-04).* The Context above was wrong on three of the 32:
EM#, ES# and EE# on `2.2` are the sheet's own contingency lines (F blank or 0), not XLOOKUP
allocations. The "phần phân bổ" wording is therefore written only on rows whose F is the
XLOOKUP-into-`2. Fund` allocation. The three contingency rows get the same reason with the plain
`Để ở mức 0:` lead-in, because "no formula or percentage basis stated" is equally true of them (user
decision). Any other non-allocation row is skipped.

**D4a. The check scans each sheet's whole used range** (added during implementation). It used to
stop at row 495 (`2. Fund`) and 300 (`2.2`), which hid PL2, ERCS, ERCS1, PL1 and PL2CA and reported
them as template mismatches. Measured on the sample before switching: none of them fails (PL rows
non-zero, ERCS a header, ERCS1 now carries its reason).

**D5. Units are translated only at the Vietnamese text boundary.** `_energy_narrative_vi` maps
the unit strings it receives ("m3/month" → "m3/tháng", "kWh/month" → "kWh/tháng",
"litre/month" → "lít/tháng"; "VND/litre" → "VND/lít" for the diesel tariff). A unit not in the map
falls back to replacing "/month" with "/tháng" and "litre" with "lít". The source data stays English.

**D6. Verification.** `_REQUIRED_CLASSIFICATION_ENFORCED_SHEETS` gains `2.2 Common area Fund`;
the "not failed here" note and its explanatory comment are replaced by an accurate one. In
`_REMARK_RECIPE_ANCHORS`, EEW's `m3/month` becomes `m3/tháng`, EEE gains `kWh/tháng` (its existing
`kWh` anchor also matches the English "kWh/month", so it cannot catch a regression) and EED gains
`lít/tháng` (it has no unit anchor today).

## Risks / Trade-offs

- [A future zero-reason writer on `2. Fund` forgets to record its reason] → the `2.2` check
  fails on the next verification run and names the code, so the gap cannot pass silently.
- [Longer remarks on `2.2` grow row heights] → handled by the existing
  `_normalise_all_remark_columns` sweep; checked visually on the generated sample.
- [Remark wording is client-facing] → display only, no figure moves; the Head-of-PM wording review
  that is already outstanding for the earlier remark changes covers these too.
