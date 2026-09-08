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

  Pool Salt: NOT a ratio at all — computed by the method Savills' own costing spec states for it
  (EXENSIVE LOGIC.xlsx, code ESM4), from the project's total pool water VOLUME. See POOL_SALT_*
  below. When the project's volume is unknown the A&K flat figure is used as an explicit,
  labelled fallback, exactly as it was before this method was implemented.
"""
import os
import csv

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OPEX_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_A_star_schema', 'Fact_OPEX.csv')

AK_TOWER_NFA_M2 = 64_124.0  # same figure as master_comparables.py's HAND_VERIFIED_COMPARABLES

RATIO_CATEGORIES = ['Electricity', 'Water', 'Diesel (Generator Fuel)', 'Repairs & Maintenance (materials only)',
                     'Administrative Expense (office overhead)']

# ESM4 — pool chemicals. input/logic/EXENSIVE LOGIC.xlsx states the whole method for this code:
# salt-electrolysis pools are held at >=4,000 ppm and consume 1-4 kg of salt per m3 of water per
# month at 6,000d/kg. Its worked example — "ho boi nguoi lon 320m3, ho boi tre em 120m3 thi tong
# the tich nuoc ho boi khoang 440m3" — makes the driver total water VOLUME summed over every pool,
# not surface area. The range is 4x wide because consumption depends on bather load, backwash
# frequency and rainfall dilution, none of which this pipeline captures; the midpoint is used and
# the range is reported on every figure so nobody mistakes it for a precise number.
#
# Why this replaced a flat figure: 440 m3 x 2.5 kg x 6,000 x 12 = 79,200,000, against the
# 79,884,000 that A&K Tower actually budgeted — 0.9% apart. The flat "real reference" was itself
# this formula, evaluated once, for somebody else's pool. Reusing it for a project with a
# different pool was reusing A&K's volume, not A&K's evidence.
POOL_SALT_KG_PER_M3_MONTH = 2.5           # midpoint of the spec's stated 1-4 kg/m3/month
POOL_SALT_KG_RANGE = (1, 4)               # the stated range, reported alongside every figure
POOL_SALT_PRICE_PER_KG = 6_000            # stated unit price, VND/kg
POOL_SALT_PPM = 4_000                     # stated salinity the consumption figure assumes


def _load_opex_facts():
    facts = {}
    with open(OPEX_CSV, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            facts.setdefault(row['Project'], {})[row['Category']] = dict(
                monthly_vnd=float(row['MonthlyVND']), source=row['Source'])
    return facts


def estimate_opex(total_nfa_m2, has_pool=False, pool_volume_m3=None):
    """Returns {category: {monthly_vnd, ratio_per_m2, n, source, reference_only}}.
    Electricity/Water/Diesel/Repairs & Maintenance are scaled from A&K Tower's real per-m² ratio
    (n=1). Pool Salt is included only if has_pool is True, and is computed from pool_volume_m3 by
    the spec's ESM4 method; when the volume is unknown it falls back to A&K's flat figure and says
    so in its `source`. Callers that render Pool Salt should prefer its `method` key over any
    ratio-based wording — it is not a ratio category."""
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
        result['Pool Salt'] = _pool_salt(pool_volume_m3, ak['Pool Salt']['monthly_vnd'])
    return result


def _coerce_volume(value):
    """Pool Volume comes off a spreadsheet cell, so it can be a number, a string a user typed, or
    blank. Anything that is not a positive number means 'not known' — which selects the fallback
    rather than silently costing a zero-volume pool."""
    try:
        volume = float(value)
    except (TypeError, ValueError):
        return None
    return volume if volume > 0 else None


def _pool_salt(pool_volume_m3, ak_flat_monthly):
    volume = _coerce_volume(pool_volume_m3)
    if volume is None:
        return dict(
            monthly_vnd=round(ak_flat_monthly), ratio_per_m2=None, n=1,
            method=(f"FALLBACK — no pool volume known for this project, so this is A&K Tower's own flat "
                    f"figure and does NOT change with pool size. The costing spec (ESM4) prices this "
                    f"from volume: enter Pool Volume (m³) on Project Info to use its method. That flat "
                    f"figure corresponds to a pool of roughly "
                    f"{ak_flat_monthly / (POOL_SALT_KG_PER_M3_MONTH * POOL_SALT_PRICE_PER_KG):,.0f} m³."),
            source=(f"A&K Tower real (flat reference, NOT NFA-scaled): {ak_flat_monthly:,.0f} VND/month."),
            reference_only=None, pool_volume_m3=None,
        )
    monthly = volume * POOL_SALT_KG_PER_M3_MONTH * POOL_SALT_PRICE_PER_KG
    low = volume * POOL_SALT_KG_RANGE[0] * POOL_SALT_PRICE_PER_KG
    high = volume * POOL_SALT_KG_RANGE[1] * POOL_SALT_PRICE_PER_KG
    return dict(
        monthly_vnd=round(monthly), ratio_per_m2=None, n='n/a (stated method, not a sample)',
        method=(f"= {volume:,.0f} m³ total pool water x {POOL_SALT_KG_PER_M3_MONTH} kg salt/m³/month x "
                f"{POOL_SALT_PRICE_PER_KG:,} VND/kg = {monthly:,.0f} VND/month "
                f"({monthly * 12:,.0f} VND/year)."),
        source=(f"Method and rates are the ones Savills' own costing spec states for this code "
                f"(input/logic/EXENSIVE LOGIC.xlsx, ESM4): a salt-electrolysis pool held at "
                f"{POOL_SALT_PPM:,} ppm consumes {POOL_SALT_KG_RANGE[0]}-{POOL_SALT_KG_RANGE[1]} kg/m³/month "
                f"at {POOL_SALT_PRICE_PER_KG:,} VND/kg. {POOL_SALT_KG_PER_M3_MONTH} kg is the midpoint of "
                f"that range, so the honest span for this project is {low * 12:,.0f} to {high * 12:,.0f} "
                f"VND/year — consumption varies with bather load, backwash frequency and rainfall "
                f"dilution, none of which are captured as inputs. Acid is NOT included: the spec cites "
                f"~60 litres/year for a 440 m³ pool but gives no price for it. For comparison, the "
                f"flat A&K Tower figure this method replaces was {ak_flat_monthly:,.0f} VND/month, "
                f"for A&K's own pool."),
        reference_only=None,
        pool_volume_m3=volume,
    )
