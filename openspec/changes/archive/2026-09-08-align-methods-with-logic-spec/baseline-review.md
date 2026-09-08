# Baseline review — before re-recording

Written before the baseline is touched. Verification reported **4 differences** and no others.

| Figure | Baseline | Current | Moved by | Intended? |
|---|---|---|---|---|
| `staff_cost_annual` | 3,597,812,105 | 3,543,782,105 | −54,030,000 | **Yes** |
| `total_profit_value` | 5,148,804,513 | 5,202,834,513 | +54,030,000 | **Yes** |
| `margin` | 0.422788 | 0.427224 | +0.004436 | **Yes** |
| `markup` | 0.732464 | 0.745900 | +0.013436 | **Yes** |

## Why

`ESS1`, `ESS4` and `ESS16` are now priced on the method `EXENSIVE LOGIC.xlsx` states for them —
**monthly contract × 12**, where a vendor contract is posts × citywide post rate — instead of the
roster headcount basis they used before. Both workbooks changed together, so the deliverable and
the analysis cost them identically.

The Must-Have toggle contains Security and Cleaning but not Landscape (Conditional) or Cleaning —
Supervisory, so `staff_cost_annual` moves by less than the full alignment:

```
Security  1,313,648,000 -> 1,294,958,000   =  -18,690,000
Cleaning    323,340,000 ->   288,000,000   =  -35,340,000
                                              -----------
                                              -54,030,000   exactly the reported move
```

Revenue and the other cost components are untouched, so profit rises by precisely what cost fell.
The two deltas being identical to the VND is the check that nothing else moved.

## What did NOT move, and had to not move

| Control | Value | Why it matters |
|---|---|---|
| `mgmt_fee_revenue_annual` | 12,178,230,000 | Revenue is out of scope |
| `service_security_annual` | 1,294,958,000 | Service column H was already the contract method — the rest of the pipeline moved **to** it, not it to them |
| `opex_annual`, every `capex_*` | unchanged | Out of scope |
| `EMH2` in the deliverable | 4,291,165,920 | Savills' own payroll, verified unchanged |

## The full alignment, beyond the toggle

Across all categories the Staff TOTAL fell **210,372,000** — 6,348,495,917 → 6,138,123,917 — which
is exactly the divergence measured between the two workbooks before this change. The gap is now
zero:

| | Deliverable | Analysis Cost Priority |
|---|---|---|
| Security | 1,294,958,004 | 1,294,958,000 |
| Cleaning | 288,000,000 | 288,000,000 |
| Landscape | 264,000,000 | 264,000,000 |

`Cleaning — Supervisory` no longer appears as its own Cost Priority row: a supervisor is part of the
same vendor contract, and the contract figure already includes that post.

## A trade-off this accepts, deliberately

The contract method uses **citywide post rates with n=1** (A&K Tower). The roster basis it replaces
differentiated a cleaning supervisor (480,000/day) from a line cleaner (340,000/day). This is
**more faithful to the written method and less granular**. Widening those rates is `R-D02`.

The 4 VND on Security is the deliverable's monthly-split rounding, documented previously.

## Conclusion

Four differences, all accounted for, all following from the intended change. Controls held. The
cross-workbook gap this change existed to close is now zero.

**Cleared to re-record.**
