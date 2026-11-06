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
  (study1_ratios() below computes them with n). Small sample, but every number in it is
  a real observed quantity divided by a real verified area — nothing in Study 1 is guessed.

  Study 2 (headcount-based, a cross-check only) — computed the SAME way but divided by headcount
  instead of NFA, anchored on registry row R05: the ONLY one of the old 8 projects that also has a
  real headcount in the new ~150-project Master List (21 staff). n=1. This is returned ALONGSIDE
  Study 1, never blended into it — averaging a 1-data-point ratio into a 5-6-data-point ratio
  would make the result look more confident than either study actually is. Use it as "does Study
  1's number look right against this other real project," not as an independent estimate.

  REVISED: the first version of this file read data/generation_A_star_schema/Fact_Capex.csv
  directly, which had real bugs — 7 of the 8 old files lay out their Capex sheets with 3
  sub-quantity columns (Required/Standard/Optional) before the TRUE total Quantity column, and
  that ETL read the wrong one; it also double-counted section-header rows as line items, and
  never extracted a 4th sheet category at all ("Capex khu tiện ích" / Amenity Area — every project
  has one except registry row R01). rescan_capex_from_source.py re-extracts directly from the source
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
import statistics

import reference_projects

# Study 1 — median Qty per 1,000 m² capex NFA, per category, over the registry rows with the capex_items role
# (change widen-utility-and-capex-sources: computed from Fact_Capex_Rescanned.csv instead of constants). One building
# counts once: a row whose capex NFA, district and city repeat an earlier row's (a second budget-phase file of the same
# building, e.g. the pre-opening and operation files of one project) is skipped, which is what the original study did.
# On the original seven this reproduces the old constants (M&E 2.054 n=6, MO 1.007 n=6, Public 2.272 n=6, Amenity
# 0.091 n=5).
STUDY1_CATEGORIES = ('M&E Equipment', 'MO Equipment', 'Public Area', 'Amenity Area')
_STUDY1_CACHE = {}


def study1_ratios():
    """{category: dict(median, n, range=(min, max), keys)} from the admitted capex projects' own item quantities."""
    path = os.path.abspath(RESCANNED_CSV)
    if path in _STUDY1_CACHE:
        return _STUDY1_CACHE[path]
    seen, nfa_by_key = set(), {}
    for r in reference_projects.by_role(reference_projects.ROLE_CAPEX_ITEMS):
        if not r['capex_nfa']:
            continue
        building = (round(r['capex_nfa'], 2), r['district'], r['city'])
        if r['district'] and building in seen:
            continue
        seen.add(building)
        nfa_by_key[r['key']] = r['capex_nfa']
    qty = {}
    for key, rows in _load_rescanned_items().items():
        if key not in nfa_by_key:
            continue
        for row in rows:
            qty.setdefault(row['Category'], {}).setdefault(key, 0.0)
            qty[row['Category']][key] += float(row['Qty'])
    out = {}
    for category in STUDY1_CATEGORIES:
        per = {k: q / (nfa_by_key[k] / 1000) for k, q in qty.get(category, {}).items() if q > 0}
        if not per:
            continue
        vals = sorted(per.values())
        out[category] = dict(median=round(statistics.median(vals), 3), n=len(vals),
                             range=(round(vals[0], 3), round(vals[-1], 3)), keys=sorted(per))
    _STUDY1_CACHE[path] = out
    return out

# Study 2 — Qty per Headcount, anchored on registry row R05 only. n=1 everywhere in this dict —
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
    for category, s1 in study1_ratios().items():
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

# The projects whose real Capex line items may be scaled, and the NFA each was measured against, come from the
# reference-project registry (role capex_items, column CapexNFA_m2). That NFA is the source file's grand total where
# that is what the study measured, so it can differ from the comparables' product-only TotalNFA for the same project.
# The parking reference has line items too but no residential NFA, so it carries no capex_items role.
def _capex_nfa_by_key():
    return {r['key']: r['capex_nfa'] for r in reference_projects.by_role(reference_projects.ROLE_CAPEX_ITEMS)
            if r['capex_nfa']}


_SKIPPED_REPORTED = set()


def _load_rescanned_items():
    """{RefKey: [rows]} of the priced line items. Rows without a known RefKey are skipped and counted once in the run
    log (the file is keyed by RefKey since change reference-projects-by-key; the Project column is a label)."""
    by_key = {}
    known = set(reference_projects.keys())
    skipped = 0
    with open(RESCANNED_CSV, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if 'RefKey' not in (reader.fieldnames or []):
            raise RuntimeError(f'{os.path.basename(RESCANNED_CSV)} has no RefKey column; run migrate_reference_keys.py.')
        for row in reader:
            if not row['Qty'] or not row['UnitPrice']:
                continue
            key = (row.get('RefKey') or '').strip()
            if key not in known:
                skipped += 1
                continue
            by_key.setdefault(key, []).append(row)
    if skipped and RESCANNED_CSV not in _SKIPPED_REPORTED:
        _SKIPPED_REPORTED.add(RESCANNED_CSV)
        print(f'Capex: bỏ qua {skipped} dòng hạng mục không có RefKey trong {os.path.basename(RESCANNED_CSV)}.')
    return by_key


def estimate_capex_items(total_nfa_m2, exclude_name=None):
    """Real per-item Qty estimate: finds the nearest real project by NFA (among the registry rows with the capex_items
    role that have line items) and scales its own real item quantities by the NFA ratio. Returns (items, source_info):
    items is a list of dicts (category, item, unit, unit_price, qty, source_project, source_qty, scale_factor);
    source_info describes which real project was used (its registry display name and key) and why. Returns ([], None)
    if no candidate is available (e.g. the project being budgeted is the only candidate). The project being budgeted
    is excluded by its registry key when `exclude_name` names a reference project, and by display-name substring as
    before otherwise."""
    by_key = _load_rescanned_items()
    nfa_by_key = _capex_nfa_by_key()
    exclude_key = reference_projects.key_for_name(exclude_name) if exclude_name else None
    ex = exclude_name.strip().lower() if exclude_name else ''
    candidates = [(key, nfa_by_key[key]) for key in by_key
                  if key in nfa_by_key and key != exclude_key
                  and not (ex and reference_projects.display_name(key).strip().lower() in ex)]
    if not candidates:
        return [], None
    nearest_key, nearest_nfa = min(candidates, key=lambda c: abs(c[1] - total_nfa_m2))
    nearest_name = reference_projects.display_name(nearest_key)
    scale = total_nfa_m2 / nearest_nfa

    def scaled(rows, name, factor):
        out = []
        for row in rows:
            source_qty = float(row['Qty'])
            out.append(dict(
                category=row['Category'], item=row['Item'], unit=row['Unit'],
                unit_price=float(row['UnitPrice']), qty=max(1, round(source_qty * factor)) if source_qty > 0 else 0,
                source_project=name, source_qty=source_qty,
            ))
        return out

    items = scaled(by_key[nearest_key], nearest_name, scale)
    # A category the nearest project has no list for (it lumps it into another sheet, or has none) is taken from the
    # nearest project that does list it, scaled by that project's own NFA ratio — the project rule "when one reference
    # lumps lines together, take the detailed rows from another reference" (change widen-utility-and-capex-sources,
    # user decision 2026-11-06 for the amenity area).
    borrowed = {}
    have = {row['Category'] for row in by_key[nearest_key]}
    for category in STUDY1_CATEGORIES:
        if category in have:
            continue
        donors = [(k, n) for k, n in candidates if any(r['Category'] == category for r in by_key[k])]
        if not donors:
            continue
        d_key, d_nfa = min(donors, key=lambda c: abs(c[1] - total_nfa_m2))
        d_name = reference_projects.display_name(d_key)
        d_scale = total_nfa_m2 / d_nfa
        items += scaled([r for r in by_key[d_key] if r['Category'] == category], d_name, d_scale)
        borrowed[category] = dict(source_project=d_name, source_key=d_key, source_nfa=d_nfa,
                                  scale_factor=round(d_scale, 4))
    source_info = dict(source_project=nearest_name, source_key=nearest_key, source_nfa=nearest_nfa,
                        target_nfa=total_nfa_m2, scale_factor=round(scale, 4), borrowed=borrowed)
    return items, source_info


if __name__ == '__main__':
    # Example: a new prospect with 90,000 m² TotalNFA, and a headcount of 24 already estimated
    # from derive_staffing_benchmarks.py's real distribution (or read from its own roster).
    est = estimate_capex_qty(total_nfa_m2=90000, headcount=24)
    for cat, v in est.items():
        s2 = f"{v['study2_qty']} (n={v['study2_n']})" if v['study2_qty'] is not None else 'n/a'
        print(f"{cat:16s} Study1={v['study1_qty']:>6} (n={v['study1_n']}, real range {v['study1_range']})   "
              f"Study2 cross-check={s2}")
