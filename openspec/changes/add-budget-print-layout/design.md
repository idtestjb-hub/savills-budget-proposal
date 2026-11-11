## Context

Motivation and the user's choices: see proposal.md. What was measured on 2026-11-11:
- **Sources.** The 2027 form `input/template/2027 Resi Budget Form (IT team).xlsx`, the approved 2026 sample (scan of
  4 A3 pages), and the fictional sample deliverable `Diamond Skyline` for trial exports.
- **Headings.** X9 "No | Stt"; Y9 "CODE"; Z9 "ITEMS"; AB:AC approved last year (total, monthly average); AE actual
  to date; AF expected for the rest of the year; AH:AI report (total, monthly average); AK:AL estimate (total,
  monthly average); AM, AN % change; AO "Remarks | Ghi chú"; AQ:BB the 12 months starting at AH6. Spacer columns AA,
  AD, AG, AJ and AP are 3–4 wide.
- **Rows.** Row 1 holds helper numbers; 2–7 the title block; 9:10 the headings; 11–505 the table (PART 3 at 505);
  506 the TRUE/FALSE check row; 514–526 the signature block (Z, AH, AQ, AT, AW, AZ).
- **Form print setup.** A3 (paperSize 8), landscape, fit to 1 page wide. No print area, print titles, footer or
  breaks.
- **Column B.** Every coded row holds `=IF(AND(AC=0,AM=" ",AO=" "),"Not Use","Use")`, and the sheet already has an
  AutoFilter starting at row 12. The inputs:
  - `AC = AB/12`;
  - `AM = IF(AI>0, %, IF(AND(AI=0,AL=0)," ","Add on"))`;
  - `AO = IF(T>0, T, " ")`.

  So "Not Use" means: prior approved 0, report monthly average 0, estimate 0, and remark T blank. Section rows 11
  and 12 have no B formula.
- **Trial exports** (fictional sample, Not Use and 506 hidden):

  | Range, paper | All columns | AC/AE/AF/AI hidden |
  |---|---|---|
  | X:AO, A4 | 8 pages, 3.4 pt | 12 pages, 4.7 pt |
  | X:BB, A3 | 5 pages, 3.1 pt | 6 pages, 4.0 pt |

  With the D3 rule and rows 506–513 hidden: A4 11 pages, A3 6 pages. Unhidden rows: 28 A4 pages. The full comparison
  with the approved sample is in `reference-layout.md`. The tool's long remarks in AO make rows tall, which is why page counts rise with text
  size.
- **No Excel in the generator.** The generator writes with openpyxl and has no Excel. The web adjust and review steps
  already need Excel (`review.recalc_copy`).

## Goals / Non-Goals

**Goals:**
- One module owns the print layout, so the generator, the adjust step and the PDF export share the same rules.
- The PDF is correct at the time it is made, whatever the PM changed.

**Non-Goals:**
- Other funds' sheets, `1. Summary` and the report sheets.
- Shortening the tool's remarks to reduce page count. That is a separate decision if wanted.
- Filling signer names, dates or stamps.
- Changing column widths or fonts in the form.

## Decisions

### D1. One module, two layers
`print_layout.py` has two layers:
- an openpyxl layer, `apply(wb)`: print setup, row flags, column group, signature block;
- an Excel layer, `export_pdf(deliverable, paper, out)`: copy, recalc, filter, area, break check, ExportAsFixedFormat.

The generator calls `apply` just before `wb.save` in `build_budget()`, after `budget_adjustment.apply`, so the
month formulas are already in place. `webapp/adjust_run.py` calls `apply` before its `wb.save`.

*Alternative:* do everything in Excel. Rejected because the generator must keep running without Excel (RUNNING.md).

### D2. Row flags in the file come from Excel's column B when Excel is there; the PDF always uses Excel's

**Revised at apply (2026-11-11).** On the fictional sample, the Python evaluation below could settle only about 80 of
490 lines. The other lines read prices and frequencies through formulas: the sheet-4 links, the report sheet's
`K/$L$8`, and VLOOKUPs. So the generator now re-applies the layout with Excel's own column B at the end of `build_budget()`, after the file is
in place (`print_layout.refresh_with_excel`, about 20 s). It runs there rather than in `run.py`, so `verify.py`, the
web and the site package all get it. `adjust_run.py` does the same from its recalculated copy.

The Python evaluation stays only as the fallback when no Excel is available. In that case a line it cannot settle is
left visible, never hidden. The verify check is strict: every "Not Use" line is hidden, and every hidden line is
"Not Use".

The original plan, kept for reference:
**In the xlsx.** openpyxl cannot evaluate column B, so `apply` evaluates the same rule from what the tool wrote:
- the prior approved and report figures it put on `2.1 Report-Management Fund`, by code;
- the 12 month amounts;
- the remark in T.

It writes `row_dimensions[r].hidden`, hides rows 506–513 (the check row, then blank spacer rows of about 270 pt in X:BB
that would leave a gap above the signatures), and saves the AutoFilter over A12:AW505 on column B with the values
"Use" and blank. The range is set explicitly; the generated file currently carries A12:AW273. Excel opens
the file with those rows hidden and the filter shown, and the PM can reapply it after editing.

**In the PDF.** `export_pdf` recalculates first, then reapplies the filter. It trusts Excel's column B, not the
Python flags.

**Check.** `verify.py` compares the Python flags with Excel's column B on its recalculated copy. A mismatch fails
verification, so the two cannot drift silently.

*Alternative:* hide nothing in the file and only filter in the PDF. Rejected because the user chose both, and a PM
printing straight from Excel should get the short table.

### D3. Only top-level section rows forced visible
After the filter, both the file and the PDF unhide rows whose X matches `^(PART\s*\d+:?|[A-D]|[IVX]+)$`: PART, a
letter, or a roman numeral without a dot. Dotted sub-groups follow column B. The approved sample prints VI and VII at
0, but leaves out empty II.2, II.3, II.6, IV.4 and V.1–V.32.

Matching uses the pattern, not "X is non-blank", because the sample shows stray text in X on a detail row.

On the fictional sample the pattern forced 1 row (V) visible, and 39 dotted rows were hidden by column B.

*Trade-off:* if the PM presses "Reapply" in Excel, a 0-valued top-level group with "Not Use" in B hides again. This is
documented in the PM note and is harmless to totals.

### D4. Fold columns with an outline group, not a print-only hide
Excel has no "hide only when printing" for columns. The user chose folded-by-default (2026-11-11). `apply` sets
outline level 2 on AC, AE, AF and AI, with hidden=True. The form already uses level 1 on these blocks, so the four
columns nest one level deeper and the existing "+/−" still works. `export_pdf` hides the same four columns on its
copy, whatever state the file was saved in.

### D5. Signature block rebuilt inside X:AO
`apply` does the following on rows 514–526:
1. Unmerges and clears X:BB, keeping the row heights.
2. Writes 8 boxes. Each box is a contiguous merged span inside X:AO:
   - a merge cannot skip columns, so a span may include folded columns. The box then widens when the PM unfolds
     them;
   - widths are balanced on the folded view. The form's columns are uneven (Z is 70 wide, the money columns 26–36,
     the spacers 3), so Z may need to hold one box split by a merge of part of its row, or two boxes may share Z.
     The exact split is chosen at apply time and checked on a PDF;
   - a fixed span table lives in the module, with a test that every span is inside X:AO and that spans do not
     overlap.
3. Box rows:
   - 514: heading, Đề xuất or Phê duyệt;
   - 515: role;
   - 516: (Ký tên, ghi rõ họ tên);
   - 517–525: blank space to sign;
   - 526: "Ngày: ___/___/___".
4. Font Arial, centred. Revised at apply: 12 pt for heading and role, 11 pt for the instruction and date. The
   heading and role wrap; the instruction and date shrink to fit, so they stay on one line in the narrow AM and AN
   boxes. 14 pt did not fit those boxes.

*Alternative:* two blocks, one for A4 and one for A3. Rejected because there is one print area per sheet, a second
block would print twice on A3, and the sample itself places the block under No-to-Remarks.

### D6. PDF export
`export_pdf` runs in its own process, `webapp/print_run.py`. The design first planned a background job like
`adjust_run`; at apply it became a synchronous `POST /api/runs/{id}/print`:
- the endpoint waits for that process, with a 300 s timeout;
- it holds the same one-job-at-a-time lock as runs, so Excel is never driven twice at once;
- the page shows "Đang xuất PDF…" while it waits, then downloads the file.

Steps:
1. Refuse if `~$<name>` exists.
2. Copy the deliverable into the run's work folder and open it with `DispatchEx`, invisible, with alerts off.
3. `CalculateFull`, reapply the AutoFilter on B, apply D3, hide rows 506–513, hide AC/AE/AF/AI.
4. Set PrintArea `$X$2:$AO$526` (A4, paperSize 9) or `$X$2:$BB$526` (A3, paperSize 8), landscape,
   FitToPagesWide 1, FitToPagesTall False, PrintTitleRows `$9:$10`, CenterFooter "Page &P of &N".
5. Keep the signature block together. Read `HPageBreaks` after `DisplayPageBreaks = True`. If a break row falls in
   515–526, add a manual break at 514. Then re-read the breaks once more to confirm. (HPageBreaks was unreliable in
   the hidden-Excel trials. If it still misbehaves, a fallback is to export, find the page holding "Đề xuất" with
   PyMuPDF, check the same page also holds the 8th "Ngày:", and if not re-export with a break at 514.)
6. ExportAsFixedFormat to `<deliverable stem> - In A4.pdf` or `- In A3.pdf` in the run folder, replacing an older one.
7. Close without saving and quit.

The PDFs are optional output kinds, `deliverable_pdf_a4` and `deliverable_pdf_a3`:
- `history.OPTIONAL_OUTPUT_KINDS` holds them;
- they are in `VIEWER_KINDS` and not in `SITE_HIDDEN_KINDS`;
- they do not count towards a run being complete (`history.is_complete`).

The endpoint is `POST /api/runs/{id}/print` with body `{paper: "A4"|"A3"}`.

### D7. Defaults written into the file
The default paper in the file is A3 X:BB, which keeps the form's existing A3 setting and gives the larger of the two
ranges. A PM who wants A4 from Excel uses the web button, or changes the print area themselves. The PM note says so.

## Risks / Trade-offs

- **Text stays small: 4.0–4.7 pt.** This comes from the form's widths (Z = 70, AO = 48.5) and the user's chosen
  ranges. → The two folded columns help, and a later option is to narrow Z and AO for print only on the PDF copy.
  Not done now because it changes the form's look.
- **The tool's long remarks make tall rows and more pages:** 12 pages on A4 against 4 in the sample. → Out of scope
  (Non-Goals). Flagged for the PM review.
- **The Python flags may differ from Excel's column B,** for example a VLOOKUP into the Report sheet the tool did not
  write. → The `verify.py` comparison in D2 catches it. The PDF is never affected because it trusts Excel.
- **The server may lack Excel.** → The same dependency as adjust and review. The button fails with a clear message.
  Check Excel on the Hub server before deploying.
- **Removing the Savills "Xem xét" box** differs from the 2027 form. → The user's explicit choice. Recorded in
  docs/05-decisions.md at apply.
- **HPageBreaks is unreliable in hidden Excel.** → The PyMuPDF fallback in D6.

## Migration Plan

- **Before the change.** No data migration is needed. Deliverables generated earlier keep their old layout; a new
  run or an adjustment brings the new layout.
- **Deploy.** Deploy through the normal Hub release for budget-web, after the 5 releases pending at `bf0ed32`.
  Do not stack it on their notes.
- **Rollback.** Revert the commit. Old deliverables are unaffected, and the PDFs are extra files.
