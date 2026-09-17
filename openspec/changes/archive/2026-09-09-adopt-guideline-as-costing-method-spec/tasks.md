# Tasks — adopt-guideline-as-costing-method-spec

No pipeline script is edited by this change and no budget figure moves. The deliverable is one new
reference file plus the accepted specs. All money referenced in the catalogue states currency (VND)
and unit, per `openspec/config.yaml`.

## 1. Source preparation

- [x] 1.1 Produce readable working copies of both `docs/` workbooks — `AI Guideline - 2027 Resi Budget Form (IT team) .xlsx` and `Ngân sách mẫu … năm 1 + năm 2 … tiền khai trương.xlsx` — using `common_utils_v2.repair_workbook()`. Verify: both open in openpyxl and in Excel, and a spot-check of five cells matches between the repaired copy and the original opened in Excel.
- [x] 1.2 Dump, per budget code, the AI GUIDELINE instruction text next to it — column `W` on `2. Budget-Management Fund`, `L` on `1. Summary` and `0. Info`, `DJ` on `Master Info`. Verify: the dump lists all 492 codes with their instruction cell (blank where none), saved to the scratchpad as the extraction worksheet.
- [x] 1.3 Confirm the catalogue file path and format: `data/master_list_verified/Costing_Method_Catalogue.csv`, columns per `design.md` D1. Verify: an empty CSV with the agreed header row exists at that path and is listed in the same folder as the other verified reference tables.

## 2. Build the method catalogue

Work section by section so each task is one sitting. For every code, fill `code`, `item_en`,
`item_vi`, `section`, `method`, `method_detail`, `inputs`, `occupancy_scaled`, `remark_components`,
`legal_citation`, `guideline_sheet`, `exensive_logic`, `precedence_note`.

- [x] 2.1 Catalogue the **revenue** codes the pipeline fills or the downstream family will fill — `RM` and its `RM.*` product rows, `RM.0A`, `RM.PA`, `RPa`, `RP1`/`RP2`/`RP5`/`RP6`, `RI`. Verify: each has a non-empty `method` or is marked `method = unclear` with the instruction quoted; `RM.0A`, `RM`, `RPa`, `RP1`, `RP2` are marked `occupancy_scaled = yes`.
- [x] 2.2 Catalogue the **management & administration** codes — `EMH` (incl. `EMH1` Savills fee), `EMA`, `EMB`, and the "other & contingency" line. Verify: `EMH1`'s entry records that its basis is a pending PM decision (D1 / `docs/05` B1) and that it is currently left blank by design.
- [x] 2.3 Catalogue the **outsourced service** codes — `ESC` (events + PCCC drill + décor), `ESS` security, `ESS` cleaning, other service, `ESI` insurance, `ESM` M&E, accreditation, service contingency. Verify: `ESC`'s `remark_components` lists all three mandated parts; `ESI`'s `legal_citation` is `NĐ 105/2025`; each entry names its `guideline_sheet`.
- [x] 2.4 Catalogue the **energy** codes — `EEW`, `EEE`, `EED`, `EEG`, energy contingency. Verify: `EEW`/`EEE`/`EED` carry `method = consumption-x-tariff` with `exensive_logic = agrees`; `EEG` has no method in the guideline column (blank) so it is recorded `method = unclear`, `exensive_logic = not-covered`, and `EE#` contingency is `linked-remark`; `EEE`'s `legal_citation` is `QĐ 1279/QĐ-BCT`; `EEE` and `EEW` are `occupancy_scaled = yes`; `EEE`'s `method_detail` records the 40%-at-zero-occupancy floor.
- [x] 2.5 Catalogue the **capex, repairs, sinking-fund and remaining** codes the pipeline touches — `EN` (24-month depreciation), `ER` repairs, `ESH`, `ESP`, and the sinking-fund `E.S` line; plus household waste (`QĐ 67/2025`). Verify: `EN`'s `method_detail` states the 24-month write-off; the waste line carries `legal_citation = QĐ 67/2025`.
- [x] 2.6 Add the catalogue header block naming the source file and its version/date (D6), and a note that `202608 - 2027 Resi Budget Form` is superseded and retained only as backup. Verify: reading the CSV shows the source file name and guideline date.

## 3. Reconcile against EXENSIVE LOGIC.xlsx (Decision 2 / D7)

- [x] 3.1 For every catalogued code, set `exensive_logic` to one of `agrees` / `differs` / `not-covered` / `mechanics-only` by comparing the catalogue method to `input/logic/EXENSIVE LOGIC.xlsx`. Verify: no catalogued code has an empty `exensive_logic` value.
- [x] 3.2 For each `differs` row, write a one-line `precedence_note` stating what EXENSIVE LOGIC says and why the guideline method is taken instead. Verify: every `differs` row has a non-empty `precedence_note`; the count of `differs` rows is reported in the change's completion notes.
- [x] 3.3 Confirm the active `cost-energy-from-consumption-and-tariff` change is unaffected — its three codes must come out `agrees`, not `differs`. Verify: `EEE`, `EEW`, `EED` rows show `exensive_logic = agrees`.

## 4. Spec integration

- [x] 4.1 Confirm nothing in the pipeline or `verify.py` reads the catalogue yet — it is a standing reference file only until a downstream change consumes it. Verify: `grep` for the catalogue filename across `source_code/` returns only this change's artifacts.
- [x] 4.2 Run `openspec validate adopt-guideline-as-costing-method-spec --strict`. Verify: reports valid.
- [x] 4.3 Add a check that the catalogue's code list can be diffed against the current template's 492 codes (D6 drift detection) — a short script or a documented one-liner. Verify: running it against the 25-sheet form reports zero missing/extra for catalogued sections.

## 5. Record the downstream change family

- [x] 5.1 Write `docs/08-guideline-change-family.md` listing the follow-on changes from `design.md` D5 — skeleton re-base, occupancy ramp, energy (active), per-product management fee, blank lines, multi-year/pre-opening — each with a one-line scope and its dependency on the catalogue. Verify: the file exists and `docs/05-decisions.md` D6–D8 link to it.
- [x] 5.2 Update `docs/05-decisions.md` implementation-order table so the catalogue extraction row points at this change as complete once merged. Verify: the table row references `adopt-guideline-as-costing-method-spec`.

## 6. Review and sign-off

- [x] 6.1 PM reviews the catalogue against a sample of 10 guideline instructions spanning all sections, confirming each row faithfully reflects the source text. Verify: sign-off recorded in `docs/05-decisions.md` under D6/D7 with the date and the sampled codes.
- [x] 6.2 Mark the change ready to archive. Verify: `openspec status --change adopt-guideline-as-costing-method-spec` shows all artifacts done and validation clean.

## Downstream (not this change — scaffolded separately, each after its own review)

- Skeleton re-base onto the 25-sheet form (D6) — adds occupancy sheets, `B2.6` waste, `Master Info`.
- Occupancy ramp (D8) — month-by-month `RM`, `RM.0A`, `RP*`, `RPa`, `EEE` floor and other `occupancy_scaled` codes.
- Energy from consumption × tariff — already active as `cost-energy-from-consumption-and-tariff`.
- Per-product management fee on one NFA basis — the open B3.
- Blank lines — `ESI` insurance, `ER` repairs, household waste, `ESC` three-part events.
- Multi-year / pre-opening output — depends on the ramp.
