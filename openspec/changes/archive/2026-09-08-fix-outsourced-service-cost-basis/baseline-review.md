# Baseline review — before re-recording

**Task 5.1.** Every difference verification reported, reviewed individually, before the baseline is
touched. Written first on purpose: re-recording without this is how a real regression gets absorbed
into the expected values.

Verification reported **4 differences** and no others.

| Figure | Baseline | Current | Moved by | Intended? |
|---|---|---|---|---|
| `staff_cost_annual` | 3,949,764,525 | 3,597,812,105 | −351,952,420 | **Yes** |
| `total_profit_value` | 4,796,852,093 | 5,148,804,513 | +351,952,420 | **Yes** |
| `margin` | 0.393887 | 0.422788 | +0.028901 | **Yes** |
| `markup` | 0.649859 | 0.732500 | +0.082641 | **Yes** |

## Why each one moved

**`staff_cost_annual`** — the Cost Basis toggle is "Must-Have Only", which includes Security and
Cleaning but not Landscape (Conditional) or Cleaning — Supervisory (Optional). Those two categories
lost the 21.5% employer contribution:

```
(1,596,082,320 + 392,858,100) x 0.215 / 1.215 = 351,952,420
```

**`total_profit_value`** — revenue is unchanged at 12,178,230,000 and the other two cost components
(OPEX, Capex) are untouched, so profit rises by exactly what cost fell. The two deltas being
identical to the VND is the check that nothing else moved.

**`margin`** — 5,148,804,513 ÷ 12,178,230,000 = 0.422788. Follows arithmetically.

**`markup`** — profit ÷ selected costs. Both numerator and denominator moved, so it rises more
sharply. Follows arithmetically.

## What did NOT move, and had to not move

| Control | Value | Why it matters |
|---|---|---|
| `service_security_annual` | 1,294,958,000 | Service column H is the **vendor citywide reference**. It never carried a loading, so there was nothing to remove. Movement here would have meant the change hit the wrong thing |
| `service_cleaning_annual` | 288,000,000 | Same |
| `service_landscape_annual` | 264,000,000 | Same |
| `mgmt_fee_revenue_annual` | 12,178,230,000 | Revenue is out of scope |
| `opex_annual`, `capex_selected` | unchanged | Out of scope |
| `EMH2` in the deliverable | 4,291,165,920 | Verified byte-for-byte against a regeneration with the pre-change file. Savills' own payroll keeps its contribution |
| Service column I | 2,314,781,550 | The in-house comparison. Briefly broke during implementation and was restored — see below |

## One defect found and fixed during implementation

Changing `category_annual_cells` to the outsourced basis also changed the Service sheet's column I,
which is headed *"Staff (Roster) Equivalent, incl. Employer Insurance"*. It silently began showing
1,905,170,000 — a figure that excludes the insurance its own header promised.

Fixed by returning both bases from `build_staff_sheet()`: the costing sheets take the outsourced
figures, the comparison column takes the in-house ones. Column I is back at 2,314,781,550 and its
header is true again.

This was not caught by the baseline — column I is not one of the 24 tracked figures. It was found by
reading the internal reconciliation output. Worth noting as a gap in what the baseline covers.

## Cross-workbook agreement

The deliverable and the analysis now report the same three figures:

| | Deliverable | Analysis |
|---|---|---|
| Security | 1,313,648,004 | 1,313,648,000 |
| Cleaning (incl. Supervisory) | 475,500,000 | 475,500,000 |
| Landscape | 268,182,000 | 268,182,000 |

The 4 VND on Security is the deliverable's monthly-split rounding: it stores a monthly figure and
the template derives the annual as `F x 12`, so any annual not divisible by 12 leaves a residue of
at most 11 VND. `EMH2` already carried +3 before this change. Inherent to the template's structure,
not introduced here.

## Conclusion

All four differences are accounted for, and each follows from the intended change. The three control
figures held. Internal sums reconcile: 13 staff categories sum exactly to the Staff TOTAL, the
Must-Have/Conditional/Optional split sums exactly to the same, and `B19 = B35 − B14 − B15 − B16`
holds to the VND.

**Cleared to re-record.**
