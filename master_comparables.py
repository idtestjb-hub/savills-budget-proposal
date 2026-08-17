"""
Master comparables table — real TotalNFA / Units / management-fee rate for every real project
this session has verified. TWO real sources, merged into one ranking pool:

  1. The original 7 hand-verified projects (input/budget_planning/'s 8 real files, Parking
     Building excluded — no apartment product). Each hand-read from its own "0. Info" sheet.
  2. data/master_list_verified/Dim_Property_Residential.csv — ~75 additional real properties
     with both a real GFA/NFA and a real management-fee rate, from the 2026 Master List
     (transform_master_list.py). This is what raises N from 7 to ~80+ candidates.

Used by generate_project_output.py to find the nearest comparable(s) to a NEW prospect and derive
a management-fee rate — nearest_comparables() + derive_mgmt_rate() for the whole-property/Apartment
rate (unchanged since the Green Skyline demonstration earlier this session), PLUS (new)
derive_product_rate() for a per-product-type rate (Officetel/Shophouse/Shopping Mall), so revenue
is no longer Apartment-NFA-only — see PRODUCT_RATE_COLUMNS and each comparable's 'rates' dict.

NFA DEFINITION CHANGE, stated plainly: the original 7-project table matched on ApartmentNFA
(apartment product only). The Master List's Residential sheet only records whole-building
GFA/NFA — it doesn't split NFA out by product type the way the 8 real files' own "0. Info"
sheets do. Comparable matching below now runs on TOTAL building NFA for every candidate — this
stays the matching basis for per-product rates too (derive_product_rate scopes WHICH comparables
qualify by rates[product], but still ranks/averages the nearest ones by the same TotalNFA delta).

PER-PRODUCT RATES, real but thin: Dim_Property_Residential.csv has Fee_Apartment/Fee_Officetel/
Fee_Shophouse/Fee_Retail columns, but only 11/4/8/2 of ~105 rows (respectively) actually have
them filled in — most rows only have a single blended MgmtFeeRate_Primary across all products.
'Shopping Mall' is matched against 'Retail' as the closest real proxy (no exact column exists).
'Nursery / Nhà trẻ' has no per-product column anywhere in the source — no real rate exists for it
in this dataset. generate_project_output.py falls back to the project's own derived Apartment rate
for any product with zero qualifying comparables, and labels that fallback explicitly — it never
silently drops a product's NFA from revenue, and never silently substitutes without saying so.

A REAL BUG, caught and fixed, worth recording: "TotalNFA" for the 7 hand-verified projects was
first set to each project's grand-total row (INCLUDING parking) — e.g. Green Skyline 99,252.45 —
while Project_Budget_Input.xlsx's own `total_nfa` only sums the 5 Product Mix rows (Apartment/
Officetel/Shophouse/Shopping Mall/Nursery), which never asks for parking at all. Result: a
prospect built by copying a real project's OWN numbers exactly still wouldn't match that project
in nearest_comparables() — a real, sizeable gap (Green Skyline's case: 99,252 vs 92,100, a
7,152 m² mismatch from parking alone), which silently picked different, worse comparables. Fixed
by re-reading each project's own "Các loại hình sản phẩm" (product-types) subtotal row directly
— the one figure that's defined the same way the input template collects it. Verified directly
against source for all 7: 11D Thi Sách and A&K Tower's existing figures already WERE product-only
(no fix needed — confirmed by re-opening their real Info sheets, where the parking section is a
separate row entirely); Lumi Prestige & Elite, Lumi Signature, and Green Skyline were fixed
(134,117/195,269/99,252 → 124,955/184,707/92,100). Fiato G2/605 are deliberately left at
Apartment+Shophouse only (35,836.27) — their real "product subtotal" row also folds in a garden-
floor line item and CĐT-private parking the input template has no field for, so matching what the
template can actually collect is more consistent than matching that project's own subtotal label.

The ~78 Master-List-sourced comparables below (auto-parsed, not hand-verified) use whatever their
own "NFA" column represents in that source — likely whole-building, but not independently checked
project-by-project the way the 7 above now are. Worth knowing if a Master-List comparable's match
looks off in the same way Green Skyline's did.

VAT note (real, not glossed over): the "Đơn giá phí PQL áp dụng" rate is quoted INCL. VAT on some
project files and EXCL. VAT on others — the source files are not consistent about this. Rates
below are tagged with what the source file actually says. Averaging across the two conventions
introduces a small (~10%, VN VAT rate) apples-to-oranges bias; flagged here rather than silently
normalized, since normalizing would require assuming which is correct without a documented rule.
The Master List's own Residential sheet is uniformly quoted INCL. VAT (see transform_master_list.py).

mgmt_rate = None means no verified per-m² rate was found (either the file uses a different Info
sheet layout not yet parsed — A&K Tower, Fiato F-Zone G2 — or the project doesn't sell apartments
at all — Parking Building, excluded entirely below).
"""
import os
import csv

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MASTER_LIST_CSV = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified', 'Dim_Property_Residential.csv')

PRODUCT_RATE_COLUMNS = {
    # Maps generate_project_budget.py's PRODUCT_ROWS names to Dim_Property_Residential.csv's
    # per-product Fee_ columns. 'Shopping Mall' has no direct match in the source data — 'Retail'
    # is the closest real proxy (commercial space priced separately from apartments), used with
    # that substitution stated explicitly wherever it's shown. 'Nursery / Nhà trẻ' has no column
    # at all anywhere in the source (transform_master_list.py never extracted one) — no real
    # per-product rate exists for it in this dataset, full stop.
    'Apartment': 'Fee_Apartment', 'Officetel': 'Fee_Officetel', 'Shophouse': 'Fee_Shophouse',
    'Shopping Mall': 'Fee_Retail',
}

# The 7 hand-verified projects — nfa switched to TotalNFA (whole-building), same verified figures
# used in estimate_capex_qty.py's VERIFIED_NFA dict. mgmt_rate/mgmt_rate_vat are unchanged: those
# were always read from the "Apartment" row specifically, real per-project rates either way.
# 'rates' (new) always has just {'Apartment': mgmt_rate} — the source Info sheets were read for
# their Apartment row only; whether they also had Officetel/Shophouse-specific rows was never
# checked, so those stay unpopulated here rather than guessed.
HAND_VERIFIED_COMPARABLES = [
    dict(name='11D Thi Sách', nfa=16783.14, units=157, total_units=162,
         mgmt_rate=None, mgmt_rate_vat=None,
         source='TotalNFA: Dim_Property_v2_verified.csv. Info sheet layout not yet parsed for a per-m² rate.'),
    dict(name='A&K Tower', nfa=64124.00, units=1155, total_units=1162,
         mgmt_rate=None, mgmt_rate_vat=None,
         source='TotalNFA: Dim_Property_v2_verified.csv. Uses "Info "/"Master Info" sheet layout, not "0. Info"; '
                'no per-m² rate parsed yet.'),
    dict(name='Lumi Prestige & Elite', nfa=124954.90, units=1575, total_units=1600,
         mgmt_rate=21000, mgmt_rate_vat='excl. VAT',
         source='NFA: "0. Info" sheet, "Các loại hình sản phẩm" (product-types) subtotal row — Apartment+Shophouse, '
                'NOT the 134,117 grand total (that included parking; fixed 2026-08-13). Rate: same sheet, row "Apartment".'),
    dict(name='Lumi Signature', nfa=184707.00, units=2375, total_units=2410,
         mgmt_rate=17000, mgmt_rate_vat='excl. VAT',
         source='NFA: "0. Info" sheet, "Các loại hình sản phẩm" (product-types) subtotal row — Apartment+Shophouse, '
                'NOT the 195,269 grand total (that included parking; fixed 2026-08-13). Rate: same sheet, row "Apartment".'),
    dict(name='Green Skyline', nfa=92100.09, units=1251, total_units=1297,
         mgmt_rate=15000, mgmt_rate_vat='incl. VAT',
         source='NFA: "0. Info" sheet, "Các loại hình sản phẩm" (product-types) subtotal row — Apartment+Shophouse+'
                'Nursery, NOT the 99,252 grand total (that included parking; fixed 2026-08-13). Rate: same sheet, row "Apartment".'),
    dict(name='Fiato Airport - F Zone G2', nfa=35836.27, units=393, total_units=432,
         mgmt_rate=None, mgmt_rate_vat=None,
         source='TotalNFA: Dim_Property_v2_verified.csv. Uses "Master Info (Fiato)" sheet layout, not "0. Info"; '
                'no per-m² rate parsed yet.'),
    dict(name='Fiato Airport - F Zone MF Pre/Y1/Y2', nfa=35836.27, units=393, total_units=469,
         mgmt_rate=18000, mgmt_rate_vat='excl. VAT',
         source='TotalNFA reused from F Zone G2 (same physical apartment building, different budget-phase file — '
                'not independently re-verified for this file). Rate: "0. Info" sheet, row "Apartment", read 2026-08-12.'),
    # Parking Building excluded: no apartment product (its own Info sheet shows 0 for every
    # apartment field), so it can never be a meaningful comparable.
]
for _c in HAND_VERIFIED_COMPARABLES:
    _c['rates'] = {'Apartment': _c['mgmt_rate']}


def _load_master_list_comparables():
    """The ~75 additional real properties from the 2026 Master List with both a real NFA and a
    real management-fee rate. Auto-parsed (transform_master_list.py), not individually
    hand-verified the way the 7 above are — real data, but a different level of scrutiny, noted
    in each entry's source string."""
    out = []
    if not os.path.exists(MASTER_LIST_CSV):
        return out
    with open(MASTER_LIST_CSV, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if not (row['NFA_m2'] and row['MgmtFeeRate_Primary']):
                continue
            vat = 'incl. VAT' if row.get('MgmtFeeVAT') == 'incl_VAT' else (row.get('MgmtFeeVAT') or None)
            rates = {}
            for product, col in PRODUCT_RATE_COLUMNS.items():
                v = row.get(col)
                if v:
                    rates[product] = float(v)
            out.append(dict(
                name=row['Name'], nfa=float(row['NFA_m2']),
                units=int(float(row['ApartmentUnits'])) if row['ApartmentUnits'] else None,
                total_units=int(float(row['TotalUnits'])) if row['TotalUnits'] else None,
                mgmt_rate=float(row['MgmtFeeRate_Primary']), mgmt_rate_vat=vat, rates=rates,
                source='2026 Master List (transform_master_list.py) — auto-parsed, not individually hand-verified.',
            ))
    return out


def _merge_comparables():
    """Hand-verified entries take priority over a same-named Master List row (more precise,
    individually checked) — the Master List row is dropped, not duplicated, when both exist."""
    hand_verified_names = {c['name'].strip().lower() for c in HAND_VERIFIED_COMPARABLES}
    merged = list(HAND_VERIFIED_COMPARABLES)
    for c in _load_master_list_comparables():
        if c['name'].strip().lower() in hand_verified_names:
            continue
        merged.append(c)
    return merged


MASTER_COMPARABLES = _merge_comparables()

# Flat citywide rates — Fact_MasterRateCard.csv has exactly ONE row each for these, not
# project-keyed. Earlier framing in this session called these "A&K Tower's rate", which
# overstated precision — they're the same number for every project, real but not comparable-specific.
SECURITY_RATE_CITYWIDE = 17_500_000   # VND/position/month — Service/Security "24/24 position (all roles)"
CLEANING_RATE_CITYWIDE = 8_000_000    # VND/position/month — Service/Cleaning "8/24 position (all roles)"
LANDSCAPE_RATE_CITYWIDE = 11_000_000  # VND/position/month — Service/Landscape "8/24 position (all roles)"
RATE_CARD_SOURCE = 'Fact_MasterRateCard.csv — flat citywide reference, same for every project.'


def nearest_comparables(input_nfa, exclude_name=None, n=2):
    """Return the n real projects closest to input_nfa (TotalNFA, whole-building) by delta,
    excluding exclude_name (case-insensitive substring match, so a new prospect never matches
    itself)."""
    candidates = [c for c in MASTER_COMPARABLES
                  if not (exclude_name and c['name'].strip().lower() in exclude_name.strip().lower())]
    ranked = sorted(candidates, key=lambda c: abs(c['nfa'] - input_nfa))
    return ranked[:n]


def derive_mgmt_rate(comparables, all_ranked=None):
    """Average the real rates among `comparables` that aren't None. If none of them have a rate,
    fall back to the next-nearest ranked candidates that do, and say so explicitly (never silently
    substitute)."""
    rated = [c for c in comparables if c['mgmt_rate']]
    note = None
    if not rated and all_ranked:
        for c in all_ranked:
            if c not in comparables and c['mgmt_rate']:
                rated.append(c)
                note = f"Neither of the 2 nearest comparables had a real rate — fell back to {c['name']} (next-nearest with one)."
                break
    if not rated:
        return None, 'No comparable in the master table has a verified management-fee rate.'
    rate = round(sum(c['mgmt_rate'] for c in rated) / len(rated))
    vats = {c['mgmt_rate_vat'] for c in rated}
    if len(vats) > 1:
        note = (note + ' ' if note else '') + f"Averaged across mixed VAT conventions ({', '.join(sorted(v for v in vats if v))}) — see module docstring."
    return rate, note


def derive_product_rate(all_ranked, product, n=2):
    """Same idea as derive_mgmt_rate, but scoped to ONE product's own real rate (c['rates'][product])
    instead of the whole-property mgmt_rate — for products other than Apartment, most comparables
    simply don't have this (see PRODUCT_RATE_COLUMNS), so this averages the n nearest (by the same
    TotalNFA ranking everything else uses) among only those that do, and says plainly when the pool
    is thin. all_ranked must already be sorted by NFA delta (nearest_comparables(..., n=len(MASTER_COMPARABLES))).
    Returns (rate, comparables_used, note); rate is None if literally no comparable in the whole
    table has ever recorded a real rate for this product (true today for 'Nursery / Nhà trẻ' — no
    such column exists anywhere in the source data)."""
    have_rate = [c for c in all_ranked if c.get('rates', {}).get(product)]
    if not have_rate:
        return None, [], f'No comparable in the master table has a verified {product} rate.'
    used = have_rate[:n]
    rate = round(sum(c['rates'][product] for c in used) / len(used))
    note = None
    if len(have_rate) < n:
        note = f'Only {len(have_rate)} comparable(s) in the whole {len(all_ranked)}-project table have a real {product} rate — averaged across all of them, not just the nearest {n}.'
    return rate, used, note
