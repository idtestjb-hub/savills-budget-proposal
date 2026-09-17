## Why

The AI Guideline's `AI GUIDELINE` instruction column exists on exactly 6 sheets of the standard
form (confirmed by direct extraction, `docs/12-sample-remark-rescan.md`). The prior change
`apply-guideline-remark-model` implemented two of them — `1. Summary`'s composed section
narratives and most of `2. Budget-Management Fund`'s line-level remarks — and explicitly recorded
the other three as known, deferred gaps: `0. Info` (per-product area basis), `A2`/`A3` (canonical
Security/Cleaning position job descriptions), and `B2.6` (a waste-collection line this pipeline
does not price at all yet). A deliverable that only partly follows its own guideline is a
half-finished job a PM cannot fully stand behind in front of a client.

## What Changes

- **`0. Info` per-product remark** — for each priced product row (Apartment/Officetel/Office/
  Shophouse), write the guideline's area-basis note ("area per construction drawings, as updated
  by the Investor in `<year>`") into that row's Remark column. Since this pipeline has no input
  today for a per-product drawing/legal citation, add one new intake field ("Area basis / drawing
  reference") on the Project Info form — free text, blank by default. When left blank, the
  narrative states the area is PM-supplied without inventing a drawing reference. Display only, no
  figure change.
- **`A2`/`A3` canonical position descriptions** — transcribe the guideline's own canonical
  Security (~20) and Cleaning (~10) position library (name, bilingual duty description,
  applicability condition) into a new reference dataset, map this pipeline's own collapsed roster
  position names (e.g. "Security - Main Gate (Morning)") onto that canonical set, and write the
  matched description as the line-level remark for every canonical position the project's roster
  actually includes. A roster position with no confident canonical match keeps its current remark
  rather than a guessed description. Display only, no figure change.
- **`B2.6` waste-collection line** — **BREAKING for the deliverable's totals**: this line is
  currently unpriced anywhere in the pipeline. Add real costing (headcount/unit-count basis per
  the guideline's own `2.63 kg/unit/day`, QĐ 67 3-part unit price: collection, transport,
  treatment) plus its remark. This is a new client-facing cost, not a text-only change, and moves
  the year-1 surplus by a real, currently-unmeasured amount.
- **Verification** — extend the existing remark-content check to also require: a per-product `0.
  Info` remark whenever the area-basis field is populated; an `A2`/`A3` remark for every roster
  position matched to a canonical name; a `B2.6` remark and figure whenever the project has
  apartment units.

## Capabilities

### New Capabilities

- `waste-collection-costing`: prices the `B2.6` domestic-waste-collection line from unit count and
  the guideline's QĐ 67 unit-price basis, and writes its guideline-driven remark. The only
  figure-moving piece of this change — everything else here is display-only.

### Modified Capabilities

- `deliverable-remarks`: broadens scope beyond the `1. Summary` composed narrative to also cover
  the two remaining **display-only** AI Guideline sheets — `0. Info`'s per-product area-basis
  remark and `A2`/`A3`'s canonical position descriptions.

## Impact

- **Affected code**:
  - `build_project_input_form.py` — one new intake field (area basis / drawing reference),
    appended after existing fields (no row-shift risk, same pattern as the earlier "months
    prepaid" field).
  - `generate_project_budget.py` — `0. Info` per-product remark write; `A2`/`A3` canonical-name
    matching and remark write; new `B2.6` costing + remark; `read_input()` reads the new field.
  - `data/master_list_verified/` — a new reference dataset for the canonical Security/Cleaning
    position library (name, VI/EN description, applicability condition), transcribed from the AI
    Guideline file, not invented.
  - `verification/checks.py` + `verify.py` — extended remark-content checks; a new baseline entry
    for `B2.6`'s figure.
- **Affected data**: none outside Generation A deliverable-writing. No Generation B table, no
  Fact/Dim join key change — the Copilot Studio package's live data is unaffected.
- **Baselines**: `B2.6`'s new figure is a genuine addition to `deliverable_baseline.json`, not a
  correction to an existing one — recorded fresh, no PM sign-off required in the same sense as a
  figure *moving* (nothing existed to move), but still worth a PM read before archive since it is
  new client-facing cost.
- **Risk**: Low for the `0. Info` and `A2`/`A3` display-only tracks. Medium for `B2.6` — a new
  priced line the client has not seen before; measure it on Wayne Tower and show the PM the
  concrete VND amount before archiving.
