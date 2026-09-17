## Why

`read_input()` locates every field in the intake workbook by **fixed cell address** — `pi['B25']`
for car parking slots, `rs['B12']` for the roster month, and eighteen others. The labels sit in
column A right next to them, unused.

This broke during the previous change, and it broke **silently**. Growing the Product Mix block from
5 products to 9 pushed every section below it down four rows. `read_input()` kept reading the old
addresses, so it read the PARKING block as product data:

```
Shop Apartment    gfa=380     <-- actually Car Parking Slots
Villas            gfa=1600    <-- actually Moto Parking Slots
```

No error. No warning. The figures happened to survive because pricing requires NFA and column C was
empty there — but that was luck, not design. Had the shifted rows carried a number in the right
column, the budget would have been wrong and nothing would have said so.

Fixing it took a coordinated edit across four places — the form's row constants, seven addresses in
`read_input()`, an Excel formula anchor, and a regenerated test fixture — and every one of them had
to be right or the failure would have been silent again. That is too much coupling for a layout
that Savills may reasonably want to change.

## What Changes

- `read_input()` finds each field by its **label**, scanning the sheet for the text that already
  sits beside it, instead of by hardcoded address.
- A label that cannot be found is a **loud failure** naming the missing label — never a silent
  default, and never a value read from whatever happens to be at that address.
- The form's row layout becomes free to change without touching the reader.
- **Old input workbooks keep working.** The labels are the same in both layouts, so a file created
  before the Product Mix grew reads correctly without migration.

Scope, by sheet:

| Sheet | Today | After |
|---|---|---|
| `Project Info` | 14 fixed addresses + products at row 14+ | label lookup; products found by the block's own header |
| `Roster Setup` | 7 fixed addresses; holidays scanned over rows 20–30 | label lookup; holidays found by their section header |
| `Staffing Demand` | already scans rows and reads labels from column A | unchanged — it is already robust |

Deliberately **not** in scope:

- **Changing the form's layout.** This change makes layout changes safe; it does not make one.
- **Excel defined names.** A more idiomatic solution, but it only works for files the current form
  generates — every existing input workbook would need regenerating, which is exactly the migration
  this change exists to avoid. Recorded as a possible successor.
- **`generate_roster.py`'s `Setup!B26/B27`.** A different sheet in a different workbook, on a module
  outside the live pipeline path.
- Any change to what the pipeline computes. **No budget figure should move.**

## Capabilities

### New Capabilities

- `input-workbook-reading`: how the pipeline locates fields in the intake workbook, and what it does
  when a field is missing.

### Modified Capabilities

<!-- None. budget-workflow-verification and outsourced-service-costs and product-revenue-pricing
     are unaffected: this changes how inputs are located, not what is computed from them. -->

## Impact

**Code**

- `generate_project_budget.py` — `read_input()`: the twenty-one fixed addresses across `Project Info`
  and `Roster Setup`, plus the product block's fixed start row.

**Risk profile — worth being explicit.** This is a refactor of the one function every figure depends
on. Its correctness criterion is unusually clean: **the recorded baseline must not move at all.**
Any movement means a field is being read from somewhere different, which is the whole failure this
change exists to prevent.

**A limitation to state up front.** Label lookup fixes the Python side only. The generated form also
contains Excel formulas that reference `Project Info` cells by address — the Staffing Demand ratio
rows anchor on `$B$7`, `$B$8`, `$B$10` and `$B$31`. Those live inside the workbook, and Excel
adjusts them automatically when a user inserts rows in Excel. They are not made safer by this
change, and `build_project_input_form.py` still writes them by address.

**Verification**

- The baseline should be **unchanged**. If it moves, the change is wrong.
- The old fixture, kept from the previous change, becomes a useful second test: it has the
  pre-migration layout, and label lookup should read it correctly without modification.

**Not affected**

- No dependency changes. No production data changes. No template changes. No figure changes.
