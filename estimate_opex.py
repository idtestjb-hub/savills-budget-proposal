"""
Estimates OPEX/Utilities (Electricity, Water, Diesel/Generator Fuel, Pool Salt, Repairs &
Maintenance) for a NEW project from data/generation_A_star_schema/Fact_OPEX.csv — real
per-project monthly costs, rescanned directly from source (see rescan_opex_from_source.py for
exactly how/why, including a real broken-formula false alarm, a real cross-file duplication
caught, and why elevator/system maintenance CONTRACTS are deliberately excluded — Vietnamese law
funds those from a separate one-time fund, not the ongoing management fee this models).

Methodology, and its real limits stated plainly, same standard as estimate_capex_qty.py:
  Electricity/Water/Diesel/Repairs & Maintenance: per-m² TotalNFA ratio, derived from A&K Tower
  ALONE (n=1) — the only real residential-type property with independently-verified OPEX data
  (Parking Building is real too, but a different building type — a parking structure's utility
  profile doesn't scale with residential floor area the same way, so it's shown for reference,
  never blended into the ratio). n=1 is stated as exactly that, not dressed up as more confident
  than it is. Repairs & Maintenance here is deliberately narrow — materials/spare-parts only, NOT
  maintenance contracts (elevator, MSB electrical panel, etc.), which are legally funded from a
  separate one-time fund in Vietnam, not the recurring management-fee budget.

  Pool Salt: a FLAT real reference (NOT scaled by any ratio) — included only when the new project
  has a pool, since no real data ties pool-salt cost to pool area/volume across more than one
  property.
"""
import os
import csv

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OPEX_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_A_star_schema', 'Fact_OPEX.csv')

AK_TOWER_NFA_M2 = 64_124.0  # same figure as master_comparables.py's HAND_VERIFIED_COMPARABLES

RATIO_CATEGORIES = ['Electricity', 'Water', 'Diesel (Generator Fuel)', 'Repairs & Maintenance (materials only)',
                     'Administrative Expense (office overhead)']


def _load_opex_facts():
    facts = {}
    with open(OPEX_CSV, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            facts.setdefault(row['Project'], {})[row['Category']] = dict(
                monthly_vnd=float(row['MonthlyVND']), source=row['Source'])
    return facts


def estimate_opex(total_nfa_m2, has_pool=False):
    """Returns {category: {monthly_vnd, ratio_per_m2, n, source, reference_only}}.
    Electricity/Water/Diesel/Repairs & Maintenance are scaled from A&K Tower's real per-m² ratio
    (n=1). Pool Salt is included, unscaled, only if has_pool is True."""
    facts = _load_opex_facts()
    ak = facts['A&K Tower']
    parking = facts.get('Parking Building', {})

    result = {}
    for category in RATIO_CATEGORIES:
        ak_monthly = ak[category]['monthly_vnd']
        ratio_per_m2 = ak_monthly / AK_TOWER_NFA_M2
        estimated = ratio_per_m2 * total_nfa_m2
        entry = dict(
            monthly_vnd=round(estimated),
            ratio_per_m2=round(ratio_per_m2, 2),
            n=1,
            source=(f"A&K Tower real: {ak_monthly:,.0f} VND/month ÷ {AK_TOWER_NFA_M2:,.0f} m² NFA = "
                    f"{ratio_per_m2:,.2f} VND/m²/month (n=1 — the only residential property with real, "
                    f"independently-verified data for this category)."),
            reference_only=None,
        )
        if category in parking:
            entry['reference_only'] = (
                f"Parking Building real (different building type, not blended into the ratio above): "
                f"{parking[category]['monthly_vnd']:,.0f} VND/month flat.")
        result[category] = entry

    if has_pool and 'Pool Salt' in ak:
        result['Pool Salt'] = dict(
            monthly_vnd=round(ak['Pool Salt']['monthly_vnd']),
            ratio_per_m2=None, n=1,
            source=(f"A&K Tower real (flat reference, NOT NFA-scaled — no real data ties pool-salt cost "
                     f"to pool area/volume across more than one property): "
                     f"{ak['Pool Salt']['monthly_vnd']:,.0f} VND/month."),
            reference_only=None,
        )
    return result
