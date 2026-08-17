"""
Full estimation model for a NEW project — all four numbers a first-draft budget needs, given only
what a real prospect can supply up front (TotalNFA, ApartmentNFA, optionally a name for reality-
check exclusion). Combines what already existed in the pipeline (Management Fee, Service) with
what this investigation just derived (Staff headcount+cost, Capex Qty) into one call.

Each of the four uses a DIFFERENT real dataset, at a DIFFERENT sample size — kept visible per
number, not blended into one confidence:

  1. MANAGEMENT FEE   master_comparables.py — 2 nearest real comparables by ApartmentNFA (n=7
                       candidate pool), rate = average of whichever have a real rate.
  2. STAFF             NEW this investigation — headcount estimated from the Master List's real
                       headcount-per-GFA distribution (n=67, by size bucket — bigger buildings
                       need proportionally fewer staff, a real effect, not assumed), then ×
                       median real cost-per-headcount (n=73).
  3. SERVICE            Fact_MasterRateCard.csv — flat citywide Security/Cleaning/Landscape rates,
                       same for every project (n=1 each, a citywide reference card, not a sample).
  4. CAPEX               estimate_capex_qty.py — old-8-files' real Qty ÷ verified NFA (n=3-4 per
                       category), cross-checked against Qty ÷ the STAFF estimate's headcount
                       (n=1, Green Skyline only).

Note the dependency: Capex's headcount cross-check (Study 2) now uses THIS module's own Staff
estimate when the new project has no real headcount yet — the four numbers aren't independent,
Staff feeds Capex.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from master_comparables import (
    MASTER_COMPARABLES, SECURITY_RATE_CITYWIDE, CLEANING_RATE_CITYWIDE, LANDSCAPE_RATE_CITYWIDE,
    nearest_comparables, derive_mgmt_rate,
)
from estimate_capex_qty import estimate_capex_qty, STUDY1_RATIO_PER_1000_NFA

# ---- Staff: real headcount-per-1,000m² GFA, median by size bucket (n=67 real properties total) ----
# Source: derive_staffing_benchmarks.py, data/master_list_verified/Staffing_Benchmark_Analysis.xlsx.
# Bigger buildings need proportionally fewer staff per m² -- a real, measured effect (0.92 -> 0.12
# across the size range), not an assumption -- so this is bucketed, not one flat ratio.
STAFF_HEADCOUNT_PER_1000_GFA = [
    (0,      30_000,  0.918, 12),   # (min_gfa, max_gfa, median_headcount_per_1000sqm, n_in_bucket)
    (30_000, 80_000,  0.307, 15),
    (80_000, 150_000, 0.214, 26),
    (150_000, float('inf'), 0.119, 14),
]
STAFF_COST_PER_HEADCOUNT_MONTHLY = dict(median=19_943_141, n=73)  # VND/month, real, n=73 properties


def estimate_management_fee(apartment_nfa_m2, project_name):
    """Management Fee — unchanged logic from master_comparables.py, exposed here for the combined call."""
    top2 = nearest_comparables(apartment_nfa_m2, exclude_name=project_name, n=2)
    all_ranked = nearest_comparables(apartment_nfa_m2, exclude_name=project_name, n=len(MASTER_COMPARABLES))
    rate, note = derive_mgmt_rate(top2, all_ranked=all_ranked)
    if rate is None:
        raise ValueError("No comparable in the master table has a verified management-fee rate.")
    monthly_revenue = apartment_nfa_m2 * rate
    return dict(rate_vnd_per_sqm=rate, note=note, comparables=[c['name'] for c in top2],
                monthly_revenue=round(monthly_revenue), annual_revenue=round(monthly_revenue * 12))


def estimate_staff_headcount(total_gfa_m2):
    """Staff headcount — real per-size-bucket median ratio, not a flat number."""
    for lo, hi, ratio, n in STAFF_HEADCOUNT_PER_1000_GFA:
        if lo <= total_gfa_m2 < hi:
            headcount = round(total_gfa_m2 / 1000 * ratio)
            return dict(estimated_headcount=headcount, ratio_used=ratio, bucket=f'{lo:,.0f}-{hi:,.0f} m²'
                        if hi != float('inf') else f'>{lo:,.0f} m²', n=n)
    raise ValueError("total_gfa_m2 must be positive.")


def estimate_staff_cost(total_gfa_m2, headcount=None):
    """Staff cost — headcount (real if given, else estimated from GFA) × real median cost/headcount."""
    hc_info = estimate_staff_headcount(total_gfa_m2)
    headcount_given = headcount is not None
    headcount = headcount if headcount_given else hc_info['estimated_headcount']
    monthly_cost = headcount * STAFF_COST_PER_HEADCOUNT_MONTHLY['median']
    return dict(headcount=headcount, headcount_source='real (given)' if headcount_given else 'estimated from GFA',
                headcount_estimate_detail=hc_info, cost_per_headcount=STAFF_COST_PER_HEADCOUNT_MONTHLY['median'],
                cost_per_headcount_n=STAFF_COST_PER_HEADCOUNT_MONTHLY['n'],
                monthly_cost=round(monthly_cost), annual_cost=round(monthly_cost * 12))


def estimate_service_cost():
    """Service — flat citywide reference rates, unconditional (same for every project)."""
    monthly = SECURITY_RATE_CITYWIDE + CLEANING_RATE_CITYWIDE + LANDSCAPE_RATE_CITYWIDE
    return dict(security=SECURITY_RATE_CITYWIDE, cleaning=CLEANING_RATE_CITYWIDE,
                landscape=LANDSCAPE_RATE_CITYWIDE, monthly_total=monthly, annual_total=monthly * 12)


def estimate_new_project(total_gfa_m2, apartment_nfa_m2, project_name, real_headcount=None):
    """The full estimate. Pass real_headcount when the roster already exists; otherwise Staff and
    Capex's cross-check both fall back to the GFA-based estimate."""
    mgmt_fee = estimate_management_fee(apartment_nfa_m2, project_name)
    staff = estimate_staff_cost(total_gfa_m2, headcount=real_headcount)
    service = estimate_service_cost()
    capex = estimate_capex_qty(total_gfa_m2, headcount=staff['headcount'])

    return dict(management_fee=mgmt_fee, staff=staff, service=service, capex=capex,
                net_year1=round(mgmt_fee['annual_revenue'] - staff['annual_cost']))


if __name__ == '__main__':
    # A genuinely novel scale -- not Green Skyline's or any other real project's own numbers, so
    # nearest_comparables() demonstrates matching against OTHER real projects, not matching itself.
    result = estimate_new_project(total_gfa_m2=70000, apartment_nfa_m2=55000,
                                   project_name='Example New Prospect')
    print(f"Management Fee: {result['management_fee']['rate_vnd_per_sqm']:,} VND/m²/mo  "
          f"(from {result['management_fee']['comparables']})  "
          f"Annual revenue: {result['management_fee']['annual_revenue']:,} VND")
    print(f"Staff: {result['staff']['headcount']} headcount ({result['staff']['headcount_source']}, "
          f"n={result['staff']['headcount_estimate_detail']['n']} bucket)  "
          f"Annual cost: {result['staff']['annual_cost']:,} VND")
    print(f"Service: {result['service']['annual_total']:,} VND/year (flat citywide reference)")
    print("Capex Qty estimate:")
    for cat, v in result['capex'].items():
        print(f"  {cat}: Study1={v['study1_qty']} (n={v['study1_n']})  "
              f"Study2 cross-check={v['study2_qty']} (n={v['study2_n']})")
    print(f"Net Year-1 (Mgmt Fee Revenue - Staff Cost): {result['net_year1']:,} VND")
