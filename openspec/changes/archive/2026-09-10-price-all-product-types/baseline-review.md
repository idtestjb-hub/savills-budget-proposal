# Baseline review — before re-recording

**Task 6.1.** Written before the baseline is touched.

## No tracked figure moved

Verification reported **zero figure differences**. All 24 matched within tolerance.

That is the correct outcome and it was predicted in design D5: this change brings the **deliverable**
up to what the **analysis** already reported. The baseline's 24 figures are all read from the
analysis workbook, so none of them should move.

| Control | Baseline | Current | Held? |
|---|---|---|---|
| `mgmt_fee_revenue_annual` | 12,178,230,000 | 12,178,230,000 | Yes |
| `total_profit_value` | 5,148,804,513 | 5,148,804,513 | Yes |
| `margin` | 0.422788 | 0.422788 | Yes |
| `markup` | 0.732464 | 0.732464 | Yes |

## What did move — the deliverable, which the baseline does not track

| | Before | After |
|---|---|---|
| Deliverable total management-fee revenue | 11,450,400,000 | **12,178,230,000** |
| Gap against the analysis | 727,830,000 | **0** |

`RM.SH` Shophouse (529,650,000) and `RM.KG` Kindergarten (198,180,000) are now written where they
were previously blank. This closes **X-01 / R-B02**, one of the recovery audit's two STOP items.

**Worth noting as a coverage gap:** the change that fixed the largest client-facing error in the
project produced *no movement at all* in the tracked baseline, because the baseline reads only the
analysis workbook. A regression in the deliverable's revenue would not be caught today.

## Why the baseline still needs re-recording

The **sample fixture changed**. Its layout was regenerated so the Product Mix block could grow from
5 products to 9, which pushed every section below it down by four rows.

| | SHA-256 |
|---|---|
| Baseline records | `456348586d082945…` |
| Fixture now | `86b4de705d8ac366…` |

Until the stored hash is updated, every run prints a fixture-changed notice. The figures are
identical, so this is a re-record of the **input identity**, not of any value.

The migration was value-preserving, verified two ways: every scale, parking, amenity and fee value
reads back identical to the old fixture, and all 24 baseline figures reproduce exactly.

## One thing found while migrating

OneDrive injected four `[trash]/*.dat` artifacts into the fixture between writing it and reading it
back — the corruption trap recorded in `docs/03-risks-and-gaps.md` (R-D08). Stripped with the
existing helper, then confirmed stable across five checks three seconds apart, and confirmed the
file still parses. The hash above is the post-strip, stable one.

## Conclusion

No figure moved; every control held. The fixture's identity changed for a stated reason, and the
change was proven value-preserving.

**Cleared to re-record.**
