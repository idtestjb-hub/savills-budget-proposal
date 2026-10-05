## Why

A real-project test on 2026-10-05 (Diamond Skyline, which has an Officetel product) found two weak
spots in verification, and one of them reaches the client copy:

1. The management-fee revenue hand-check adds up only Apartment, Shophouse and Nursery. A project
   with any other priced product (here Officetel, 1,800 m² × 18,250 VND/m²/month × 12 =
   394,200,000 VND a year) is reported as a failure although the deliverable is right. The check
   is wrong, not the figures.
2. On `2.2 Common area Fund`, the line RP5 (daily motorbike/bicycle visitor parking, revenue) is
   0 VND and its only remark is the standard form's placeholder "demo". That word goes straight
   into the client copy (docs/22 item C5), and the "every Required code has a stated reason" check
   accepts it as the reason, so the check passes on a word that explains nothing.

## What Changes

- The hand-check covers every product the tool can price (all nine product rows), reading each
  product's area from the input file by label. A product with an area in the input but no price in
  the fee table counts 0 and is named as "unpriced" in the check's description. A product whose
  input area differs from the workbook's by more than 0.5 m² still fails the check, as today.
- The tool writes its own Vietnamese reason into `2.2 Common area Fund` column T on the RP5 line
  (same "Để ở mức 0: …" form as the other lines left at zero), only when that cell is empty or holds
  exactly the form's text "demo". Any other text already there is left alone.
- `verification/checks.py` stops exempting that cell and that line from the wording scan and the
  line-remark scan, so the new remark is checked like every other pipeline remark.
- The "every Required code is filled" check no longer accepts the exact form placeholder "demo" as
  a stated reason. The match is on the exact text for that sheet and code, never on the word.
- No figure on any sheet changes. One remark on the client deliverable changes (RP5, `2.2`, T15).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `budget-workflow-verification`: the management-fee revenue hand-check must cover every priced
  product and say which products it left unpriced.
- `guideline-required-line-items`: a Required line left at zero on `2.2 Common area Fund` whose
  remark the form ships as a placeholder gets its own stated reason, and verification does not
  accept the placeholder as a reason.

## Impact

- Code: `verification/baseline.py` (`read_sample_scale`, `hand_checks`); `verification/checks.py`
  (`_TEMPLATE_OWNED_TEXT_CELLS`, `_TEMPLATE_OWNED_T_ROWS`, `check_required_line_items`);
  `generate_project_budget.py` (`fill_common_area_fund_sheet`, one new remark write).
- Client deliverable: one remark on `2.2 Common area Fund`, cell T15, changes from "demo" to a
  Vietnamese reason. No number moves. The convention "a change that moves a figure needs the PM's
  sign-off" does not apply; the changed wording is recorded here and in `docs/project-status.md`.
- Outside this change, not edited here: docs/22 item C5 and its slide ask the template owner to
  fix the "demo" text in the form. The form itself still has the word; only the tool's output is
  fixed. Whether C5 stays in the question list is for the user to decide.
- No new dependencies. The inner repository is not committed or pushed until the user asks.
