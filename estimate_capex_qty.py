"""
Reusable estimation logic for Capex Qty on a NEW project — turns the two studies in
study_capex_qty_estimation.py into one callable function. In use today: generate_project_output.py
calls estimate_capex_qty() for the Capex sheet's category cross-check and estimate_capex_items() for
its item list; generate_project_budget.py calls estimate_capex_items() for the client deliverable's
Capex lines; estimate_new_project.py imports the Study 1 ratios.

THE LOGIC, and why it's two numbers, not one:

  Study 1 (NFA-based, the primary estimate) — every project reaching this function already has a
  TotalNFA (from Project_Budget_Input.xlsx), so this always applies:

      EstimatedQty[category] = (new_project_TotalNFA_m2 / 1000) * median_ratio[category]

  median_ratio comes from the OLD 8 real project files' actual observed Capex quantities,
  divided by each of those projects' own VERIFIED TotalNFA — n=5 or 6 real projects per category
  (see STUDY1_RATIO_PER_1000_NFA below for the exact n). Small sample, but every number in it is
  a real observed quantity divided by a real verified area — nothing in Study 1 is guessed.

  Study 2 (headcount-based, a cross-check only) — computed the SAME way but divided by headcount
  instead of NFA, anchored on Green Skyline: the ONLY one of the old 8 projects that also has a
  real headcount in the new ~150-project Master List (21 staff). n=1. This is returned ALONGSIDE
  Study 1, never blended into it — averaging a 1-data-point ratio into a 5-6-data-point ratio
  would make the result look more confident than either study actually is. Use it as "does Study
  1's number look right against this other real project," not as an independent estimate.

  REVISED: the first version of this file read data/generation_A_star_schema/Fact_Capex.csv
  directly, which had real bugs — 7 of the 8 old files lay out their Capex sheets with 3
  sub-quantity columns (Required/Standard/Optional) before the TRUE total Quantity column, and
  that ETL read the wrong one; it also double-counted section-header rows as line items, and
  never extracted a 4th sheet category at all ("Capex khu tiện ích" / Amenity Area — every project
  has one except 11D Thi Sách). rescan_capex_from_source.py re-extracts directly from the source
  files with a column-detector that finds "Unit Price" by text and takes Quantity/Total as the
  columns immediately left/right of it — true in every layout seen, regardless of how many
  sub-quantity columns precede it. The ratios below come from that corrected extraction
  (Fact_Capex_Rescanned.csv); some moved a lot — M&E roughly 2.4x higher, Public Area roughly
  3.9x higher, MO roughly 30% lower than the original (wrong) numbers.

  Category caveat, still true: these are the 4 categories the old files actually track (M&E
  Equipment / MO Equipment / Public Area / Amenity Area) — NOT the 12-category, 130-item catalog
  the live Capex sheet fills from Fact_MasterRateCard.csv.

  estimate_capex_items() BELOW solves that mapping problem the way generate_project_output.py's
  Capex sheet actually needed it solved: instead of distributing a category total across an
  unrelated 12-category catalog (which would mean inventing a per-item split with no real basis),
  it picks the single REAL project nearest this one by TotalNFA — among the 7 that have real
  Capex line items in Fact_Capex_Rescanned.csv — and scales THAT project's own real item list
  (real item names, real unit prices, real relative mix) by the NFA ratio between the two
  projects. Every returned item traces to one real source row; only the quantity is estimated,
  and by how much is stated (scale_factor) on every row.
"""
import csv
import os

# Study 1 — median Qty per 1,000 m² verified TotalNFA, from the old 8 real project files,
# rescanned directly from source (see rescan_capex_from_source.py). n = how many of those
# projects have BOTH a real Capex line item in that category AND a clean, hand-verified NFA
# (Generation A's own Dim_Project.NFA_m2 is broken for several projects — see
# study_capex_qty_estimation.py's VERIFIED_NFA dict and its docstring for why).
STUDY1_RATIO_PER_1000_NFA = {
    'M&E Equipment': dict(median=2.054, n=6, range=(1.234, 9.235)),
    'MO Equipment':  dict(median=1.007, n=6, range=(0.589, 5.482)),
    'Public Area':   dict(median=2.272, n=6, range=(0.661, 7.865)),
    'Amenity Area':  dict(median=0.091, n=5, range=(0.046, 0.251)),
}

# Study 2 — Qty per Headcount, anchored on Green Skyline only. n=1 everywhere in this dict —
# stated explicitly on every returned row rather than left implicit.
STUDY2_RATIO_PER_HEADCOUNT = {
    'M&E Equipment': dict(ratio=7.286, n=1),
    'MO Equipment':  dict(ratio=4.143, n=1),
    'Public Area':   dict(ratio=8.429, n=1),
    'Amenity Area':  dict(ratio=0.429, n=1),
}


def estimate_capex_qty(total_nfa_m2, headcount=None):
    """
    total_nfa_m2 : float, required — the new project's own TotalNFA (m²). Study 1 has no
                   fallback for a missing scale, since every project reaching this function has
                   already entered one on Project_Budget_Input.xlsx.
    headcount    : float, optional — the new project's real (from Staffing Demand) or already-
                   estimated (from derive_staffing_benchmarks.py's real-population distribution)
                   headcount. When given, Study 2's cross-check number is computed too.

    Returns {category: {study1_qty, study1_n, study1_range, study2_qty, study2_n}} — both
    numbers per category, never pre-merged into a single "answer."
    """
    if total_nfa_m2 is None or total_nfa_m2 <= 0:
        raise ValueError("total_nfa_m2 must be a positive number — Study 1 has no fallback for a missing scale.")

    result = {}
    for category, s1 in STUDY1_RATIO_PER_1000_NFA.items():
        entry = dict(
            study1_qty=round(total_nfa_m2 / 1000 * s1['median'], 1),
            study1_n=s1['n'], study1_range=s1['range'],
            study2_qty=None, study2_n=None,
        )
        if headcount is not None:
            s2 = STUDY2_RATIO_PER_HEADCOUNT.get(category)
            if s2:
                entry['study2_qty'] = round(headcount * s2['ratio'], 1)
                entry['study2_n'] = s2['n']
        result[category] = entry
    return result


RESCANNED_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'generation_A_star_schema',
                              'Fact_Capex_Rescanned.csv')

# Verified TotalNFA for the projects that have real Capex line items — same figures as
# study_capex_qty_estimation.py's VERIFIED_NFA and master_comparables.py's HAND_VERIFIED_COMPARABLES.
# Fiato 605 reuses Fiato G2's TotalNFA (same physical apartment building, different budget-phase
# file — not independently re-verified for 605). Parking Building excluded: no apartment product,
# not a meaningful NFA comparable for a residential prospect.
VERIFIED_NFA_FOR_ITEMS = {
    '11d thi sach': 16783.14, 'a&k tower': 64124.00, 'lumi prestige & elite': 134117.40,
    'lumi signature': 195269.50, 'green skyline': 99252.45,
    'fiato airport - f zone g2': 35836.27, 'fiato airport - f zone mf pre/y1/y2': 35836.27,
}


def _load_rescanned_items():
    by_project = {}
    with open(RESCANNED_CSV, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if not row['Qty'] or not row['UnitPrice']:
                continue
            by_project.setdefault(row['Project'], []).append(row)
    return by_project


def estimate_capex_items(total_nfa_m2, exclude_name=None):
    """Real per-item Qty estimate: finds the nearest real project by TotalNFA (among those with
    real Capex line items) and scales its own real item quantities by the NFA ratio. Returns
    (items, source_info) — items is a list of dicts (category, item, unit, unit_price, qty,
    source_project, source_qty, scale_factor); source_info describes which real project was used
    and why. Returns ([], None) if no candidate is available (e.g. exclude_name matches all of them)."""
    by_project = _load_rescanned_items()
    candidates = [(name, VERIFIED_NFA_FOR_ITEMS[name.strip().lower()]) for name in by_project
                  if name.strip().lower() in VERIFIED_NFA_FOR_ITEMS
                  and not (exclude_name and name.strip().lower() in exclude_name.strip().lower())]
    if not candidates:
        return [], None
    nearest_name, nearest_nfa = min(candidates, key=lambda c: abs(c[1] - total_nfa_m2))
    scale = total_nfa_m2 / nearest_nfa

    items = []
    for row in by_project[nearest_name]:
        source_qty = float(row['Qty'])
        scaled_qty = max(1, round(source_qty * scale)) if source_qty > 0 else 0
        items.append(dict(
            category=row['Category'], item=row['Item'], unit=row['Unit'],
            unit_price=float(row['UnitPrice']), qty=scaled_qty,
            source_project=nearest_name, source_qty=source_qty,
        ))
    source_info = dict(source_project=nearest_name, source_nfa=nearest_nfa,
                        target_nfa=total_nfa_m2, scale_factor=round(scale, 4))
    return items, source_info


if __name__ == '__main__':
    # Example: a new prospect with 90,000 m² TotalNFA, and a headcount of 24 already estimated
    # from derive_staffing_benchmarks.py's real distribution (or read from its own roster).
    est = estimate_capex_qty(total_nfa_m2=90000, headcount=24)
    for cat, v in est.items():
        s2 = f"{v['study2_qty']} (n={v['study2_n']})" if v['study2_qty'] is not None else 'n/a'
        print(f"{cat:16s} Study1={v['study1_qty']:>6} (n={v['study1_n']}, real range {v['study1_range']})   "
              f"Study2 cross-check={s2}")
