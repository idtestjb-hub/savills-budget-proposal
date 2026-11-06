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
rate (unchanged since the first demonstration earlier this session), PLUS (new)
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
first set to each project's grand-total row (INCLUDING parking) — e.g. one project at 99,252.45 —
while Project_Budget_Input.xlsx's own `total_nfa` only sums the 5 Product Mix rows (Apartment/
Officetel/Shophouse/Shopping Mall/Nursery), which never asks for parking at all. Result: a
prospect built by copying a real project's OWN numbers exactly still wouldn't match that project
in nearest_comparables() — a real, sizeable gap (that project's case: 99,252 vs 92,100, a
7,152 m² mismatch from parking alone), which silently picked different, worse comparables. Fixed
by re-reading each project's own "Các loại hình sản phẩm" (product-types) subtotal row directly
— the one figure that's defined the same way the input template collects it. Verified directly
against source for all 7: two of them (R01, R02) already had figures that already WERE product-only
(no fix needed — confirmed by re-opening their real Info sheets, where the parking section is a
separate row entirely); three others (R03, R04, R05) were fixed
(134,117/195,269/99,252 → 124,955/184,707/92,100). the two airport-zone rows (R06, R07) are deliberately left at
Apartment+Shophouse only (35,836.27) — their real "product subtotal" row also folds in a garden-
floor line item and CĐT-private parking the input template has no field for, so matching what the
template can actually collect is more consistent than matching that project's own subtotal label.

The ~78 Master-List-sourced comparables below (auto-parsed, not hand-verified) use whatever their
own "NFA" column represents in that source — likely whole-building, but not independently checked
project-by-project the way the 7 above now are. Worth knowing if a Master-List comparable's match
looks off in the same way R05's did.

VAT note (real, not glossed over): the "Đơn giá phí PQL áp dụng" rate is quoted INCL. VAT on some
project files and EXCL. VAT on others — the source files are not consistent about this. Rates
below are tagged with what the source file actually says. Averaging across the two conventions
introduces a small (~10%, VN VAT rate) apples-to-oranges bias; flagged here rather than silently
normalized, since normalizing would require assuming which is correct without a documented rule.
The Master List's own Residential sheet is uniformly quoted INCL. VAT (see transform_master_list.py).

mgmt_rate = None means no verified per-m² rate was found (either the file uses a different Info
sheet layout not yet parsed — R02 and R06 — or the project doesn't sell apartments
at all — R08, excluded entirely below).
"""
import os
import csv
import math
import unicodedata

import reference_projects
import budget_period
import utility_tariffs

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MASTER_LIST_CSV = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified', 'Dim_Property_Residential.csv')


def _nfc(s):
    """Normalize to NFC. Source strings (this file's own, and any CSV's District/City_Province-style
    columns) aren't guaranteed to already be in one consistent Unicode form for Vietnamese text —
    same issue, same fix, as verification/checks.py's identical helper. Kept as a local copy rather
    than imported from there: checks.py depends on this module's siblings (generate_project_budget.py
    etc.), not the other way around, so importing a verification-only module from here would be
    backwards. Defined here, near the top, rather than near nearest_comparables() below (its original
    spot) — moved 2026-09-16 so the module-level loaders above can use it too, before they run."""
    return unicodedata.normalize('NFC', s) if isinstance(s, str) else s

PRODUCT_RATE_COLUMNS = {
    # Maps generate_project_budget.py's PRODUCT_ROWS names to Dim_Property_Residential.csv's
    # per-product Fee_ columns. 'Shopping Mall' has no direct match in the source data — 'Retail'
    # is the closest real proxy (commercial space priced separately from apartments), used with
    # that substitution stated explicitly wherever it's shown. 'Nursery / Nhà trẻ' has no column
    # at all anywhere in the source (transform_master_list.py never extracted one) — no real
    # per-product rate exists for it in this dataset, full stop.
    'Apartment': 'Fee_Apartment', 'Officetel': 'Fee_Officetel', 'Shophouse': 'Fee_Shophouse',
    'Shopping Mall': 'Fee_Retail',
    # Added 2026-09-08 with the per-product revenue rows. 'Retail' reads the same column as
    # 'Shopping Mall' — both are commercial retail space priced separately from apartments, and the
    # source data has one Fee_Retail column covering them. 'Villas' has its own column.
    # Coverage is thin: Fee_Retail is filled on 2 of 105 properties and Fee_Villa on 2, so both will
    # often find no rate among the nearest comparables and fall back to the Apartment rate, stated
    # in the output. 'Office' and 'Shop Apartment' have no column anywhere in the source data.
    'Retail': 'Fee_Retail', 'Villas': 'Fee_Villa',
}

# The hand-verified comparables come from the reference-project registry
# (data/master_list_verified/Dim_ReferenceProject.csv, change reference-projects-by-key): one row per real budget the
# tool prices from, identified by a stable key (R01, R02, ...). The registry's TotalNFA is whole-building NFA on the
# product-types subtotal where the source "0. Info" sheet gave one; mgmt_rate/mgmt_rate_vat were read from the
# "Apartment" row of that sheet. 'rates' always has just {'Apartment': mgmt_rate}: the Info sheets were read for their
# Apartment row only; whether they also had Officetel/Shophouse rows was never checked, so those stay unpopulated.
# The registry is the only place the code learns these projects' names; on the office data they are the real names,
# in a site package they are pseudonyms, and nothing here depends on which.
HAND_VERIFIED_COMPARABLES = reference_projects.hand_verified_comparables()
for _c in HAND_VERIFIED_COMPARABLES:
    _c['rates'] = {'Apartment': _c['mgmt_rate']}
    # The only properties with a real detailed budget workbook behind them; everything else in MASTER_COMPARABLES is
    # Master-List: auto-scraped, filtered to "parses cleanly", never individually checked against a source document.
    # Marked so nearest_comparables() can prefer them within a tier (task 8.1, rank-comparables-by-location,
    # 2026-09-17, the user's rule).
    _c['hand_verified'] = True
# Every row carries a real, sourced district/city (the registry's LocationSource column), backfilled 2026-09-17 per
# task 6.1 of rank-comparables-by-location by web research against each building, never inferred from the project
# name alone. Two rows are genuinely in Hà Nội, not HCMC: real, confirmed exceptions in this otherwise HCMC-metro pool,
# kept out of the ranking by their ExcludedFromRanking reason (see _merge_comparables()).


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
                # District/City_Province already exist in the source CSV, just never read before
                # (change rank-comparables-by-location, 2026-09-15) — real data, same rows the fee
                # columns above come from, not a separate or less-verified source.
                district=row.get('District') or None, city=row.get('City_Province') or None,
                source='2026 Master List (transform_master_list.py) — auto-parsed, not individually hand-verified.',
            ))
    return out


PROJECT_LOCATION_CSV = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified', 'Fact_ProjectLocation.csv')


def _to_float_or_none(v):
    """Parse a CSV cell as a float; blank, missing, or non-numeric all become None rather than
    raising — the same "never guess, never crash on a gap" treatment every other optional field
    in this pipeline gets."""
    try:
        return float(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


def _load_project_locations():
    """name (normalized) -> (ward, city_province, lat, lon), from the real ward/coordinate data the
    PM added 2026-09-16 (docs/ProjectLocation.xlsx, 162 named properties, both sheets). lat/lon are
    parsed to float here (or None) so callers never need to convert a CSV string themselves.

    WARD is a finer granularity than `district` above (Dim_Property_Residential.csv's own column) —
    a ward sits inside a district, and the two naming systems don't correspond string-for-string
    (post-reform ward names like 'Thanh My Tay' vs pre-reform district names like 'Bình Thạnh'). This
    loader therefore only fills the CITY/PROVINCE field below (same granularity as the existing
    `city` field, safe to merge) — it does not touch `district` and does not introduce a ward-level
    tier. `lat`/`lon` ARE used now (change rank-comparables-by-location, task 2.4) — as the intra-tier
    distance tie-break in nearest_comparables(), not as a new tier; see that function's docstring."""
    out = {}
    if not os.path.exists(PROJECT_LOCATION_CSV):
        return out
    with open(PROJECT_LOCATION_CSV, encoding='utf-8-sig') as f:
        for row in csv.DictReader(line for line in f if not line.startswith('#')):
            key = _nfc(row['asset_name']).strip().lower()
            if key:
                out[key] = (row.get('new_ward') or None, row.get('new_province_city') or None,
                            _to_float_or_none(row.get('latitude')), _to_float_or_none(row.get('longitude')))
    return out


def _merge_comparables():
    """Hand-verified entries take priority over a same-named Master List row (more precise,
    individually checked) — the Master List row is dropped, not duplicated, when both exist.

    After merging, fills `city` from the real ward/coordinate data (Fact_ProjectLocation.csv,
    change rank-comparables-by-location task 1.3) for any candidate that has NEITHER a district nor
    a city yet — never overwrites an existing value, and never touches `district` (see
    _load_project_locations()'s own docstring on why ward can't just become district). Verified
    2026-09-16: raises "has a real district or city" coverage on the live ranking pool from 63/85
    (74%) to 79/85 (93%); the 7 hand-verified comparables get exactly one hit (R05) — the
    other 6 still need task 6.1's human backfill, unchanged by this. `ward`/`lat`/`lon` are stored on
    every matched candidate regardless of whether city was already known, so a future ward-level tier
    decision has the data already loaded rather than needing a second file read.

    Drops any `HAND_VERIFIED_COMPARABLES` entry carrying `excluded_from_ranking` (task 8.5,
    2026-09-17 — your instruction: Hà Nội and Hồ Chí Minh "are 2 separated city") — registry rows R03
    and R04 stay in HAND_VERIFIED_COMPARABLES itself (real, sourced data, kept for
    the record) but never reach MASTER_COMPARABLES, so nearest_comparables() can never select them
    for any project, verified-priority or not."""
    hand_verified_names = {c['name'].strip().lower() for c in HAND_VERIFIED_COMPARABLES}
    merged = [c for c in HAND_VERIFIED_COMPARABLES if not c.get('excluded_from_ranking')]
    for c in _load_master_list_comparables():
        if c['name'].strip().lower() in hand_verified_names:
            continue
        merged.append(c)

    locations = _load_project_locations()
    for c in merged:
        hit = locations.get(_nfc(c['name']).strip().lower())
        if not hit:
            continue
        ward, province_city, lat, lon = hit
        c['ward'], c['lat'], c['lon'] = ward, lat, lon
        if not c.get('district') and not c.get('city') and province_city:
            c['city'] = province_city

    return merged


MASTER_COMPARABLES = _merge_comparables()

# Flat citywide rates — Fact_MasterRateCard.csv has exactly ONE row each for these, not
# project-keyed. Earlier framing in this session called these "the utilities base project's rate", which
# overstated precision — they're the same number for every project, real but not comparable-specific.
SECURITY_RATE_CITYWIDE = 17_500_000   # VND/position/month — Service/Security "24/24 position (all roles)"
CLEANING_RATE_CITYWIDE = 8_000_000    # VND/position/month — Service/Cleaning "8/24 position (all roles)"
LANDSCAPE_RATE_CITYWIDE = 11_000_000  # VND/position/month — Service/Landscape "8/24 position (all roles)"
RATE_CARD_SOURCE = 'Fact_MasterRateCard.csv — flat citywide reference, same for every project.'


def _location_tier(candidate_district, candidate_city, input_district, input_city):
    """0 = same district as the input project, 1 = same city/province (different district),
    2 = no location match. Missing data on either side (candidate or input) always falls through
    to tier 2 — a blank is never treated as a match (change rank-comparables-by-location, 2026-09-15)."""
    if not input_district and not input_city:
        return 2
    c_district, i_district = _nfc(candidate_district), _nfc(input_district)
    if c_district and i_district and c_district.strip().lower() == i_district.strip().lower():
        return 0
    c_city, i_city = _nfc(candidate_city), _nfc(input_city)
    if c_city and i_city and c_city.strip().lower() == i_city.strip().lower():
        return 1
    return 2


DISTANCE_TIER_KM = 1.0        # within this, a real comparable's distance is trusted (task 2.5)
MAX_DISTANCE_RATE_SWING = 0.20  # cap on how far a within-DISTANCE_TIER_KM match may move a rate

# change prefer-similar-size-comparables, 2026-09-18 — a JUDGMENT CALL, not sourced from any
# Savills guideline or reference dataset (checked: none states a size-similarity threshold). Ranks
# ahead of verified-status in nearest_comparables()'s sort key — see that function's docstring and
# the change's design.md D1/D2 for why. Flagged for PM review/retuning, same spirit as the fill-up
# curve's disclosed-assumption anchors.
SIZE_SIMILARITY_BAND = 0.50   # a same-tier candidate within ±50% of the input's Total NFA is
                               # preferred over one outside it, even if the latter is hand-verified

# Task 8.6, 2026-09-17 switched real-distance comparison off ("we do that later"). Change
# apply-head-of-pm-decisions-2026-10 (group 4, task 4.1, decision B12, signed off 2026-10-11) turns it back on,
# with the ±20% swing cap on EVERY product's rate and on the blended fallback rate (see
# derive_product_rate_capped() and derive_mgmt_rate_capped()). The flag stays the one switch: while False,
# nearest_comparables() never reads lat/lon at all (district/city tier, then size band, then verified status,
# then NFA delta) and comparable_match_basis() never claims a "closest by real distance" label. A project with
# no coordinates gives the same ranking and the same rates either way.
DISTANCE_COMPARISON_ENABLED = True


def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two lat/lon points. Plain geometry (the standard
    haversine formula) — not a business rule, so unlike the location-tier ordering below, no
    approval or measurement is needed to use it: it doesn't assert anything about management fees,
    only about the shape of the Earth."""
    r = 6371.0088  # mean Earth radius, km
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _has_coords(c):
    return c.get('lat') is not None and c.get('lon') is not None


def comparable_match_basis(comparables, input_district=None, input_city=None,
                            input_lat=None, input_lon=None, input_nfa=None, lang='en'):
    """One short phrase describing why `comparables` were actually selected — reflects the BEST
    (lowest) location tier genuinely present among them, not a static claim of what the matching
    basis always is. A reader-facing comparables table should use this instead of a hardcoded
    "ranked by Total NFA" string, which becomes wrong the moment location narrows the pool (change
    rank-comparables-by-location, 2026-09-15). `lang='vi'` for client-facing text, `'en'` (default)
    for internal/PM-facing text — this module has both conventions elsewhere (English source
    strings, Vietnamese client remarks written by the two generators).

    Also states whether real distance (not NFA) actually decided the ordering shown — true only
    when DISTANCE_COMPARISON_ENABLED, the input project has coordinates, AND at least one shown
    comparable is within DISTANCE_TIER_KM of it (task 2.4, revised task 2.5); otherwise the
    within-tier ordering was NFA delta, exactly as the label said before task 2.4. While
    DISTANCE_COMPARISON_ENABLED is False (task 8.6, 2026-09-17), this always reads False — the label
    never claims real-distance matching decided an ordering that distance was never consulted for.

    Also states whether any shown comparable is one of the 8 hand-verified, individually-checked
    projects (task 8.1, 2026-09-17) — real and worth disclosing either way, since a reader comparing
    two Comparison sheets should be able to tell a rate backed by a real detailed budget workbook
    from one backed only by the auto-scraped Master List.

    Also states, when `input_nfa` is supplied, whether any shown comparable's Total NFA differs from
    the project's own by more than `SIZE_SIMILARITY_BAND` (change prefer-similar-size-comparables,
    2026-09-18) — the ranking now prefers a same-band comparable over a badly-sized one, but the pool
    can still be thin enough that no comparable clears the band, and a reader SHALL be told when
    that's the case rather than left to assume a closer match was found than actually was."""
    tiers = {_location_tier(c.get('district'), c.get('city'), input_district, input_city)
             for c in comparables}
    best = min(tiers) if tiers else 2
    used_distance = bool(
        DISTANCE_COMPARISON_ENABLED and input_lat is not None and input_lon is not None
        and any(_has_coords(c) and _haversine_km(input_lat, input_lon, c['lat'], c['lon']) <= DISTANCE_TIER_KM
                for c in comparables))
    any_verified = any(c.get('hand_verified') for c in comparables)
    oversized = []
    if input_nfa:
        oversized = [c for c in comparables
                     if abs(c['nfa'] - input_nfa) / input_nfa > SIZE_SIMILARITY_BAND]
    if lang == 'vi':
        prefix = {0: 'cùng quận/huyện, ', 1: 'cùng tỉnh/thành, ', 2: ''}[best]
        verified_mid = 'dự án đã xác minh chi tiết, sau đó ' if any_verified else ''
        basis = 'gần nhất theo khoảng cách thực tế (km)' if used_distance \
            else 'gần nhất theo Tổng diện tích NFA (toàn bộ tòa nhà)'
        size_note = ''
        if oversized:
            names = ', '.join(c['name'] for c in oversized)
            size_note = (f' (Lưu ý: {names} có Tổng diện tích NFA lệch hơn '
                         f'{SIZE_SIMILARITY_BAND:.0%} so với dự án này — không có dự án nào phù hợp '
                         f'hơn trong dữ liệu hiện có)')
        return prefix + verified_mid + basis + size_note
    prefix = {0: 'same District, then ', 1: 'same City/Province, then ', 2: ''}[best]
    verified_mid = 'individually-verified project, then ' if any_verified else ''
    basis = 'closest by real distance (km)' if used_distance else 'closest Total NFA (whole-building)'
    size_note = ''
    if oversized:
        names = ', '.join(c['name'] for c in oversized)
        size_note = (f' (note: {names} differs from this project\'s Total NFA by more than '
                     f'{SIZE_SIMILARITY_BAND:.0%} — no closer-sized comparable exists in the '
                     f'current data)')
    return prefix + verified_mid + basis + size_note


def nearest_comparables(input_nfa, exclude_name=None, n=2, input_district=None, input_city=None,
                         input_lat=None, input_lon=None):
    """Return the n real projects closest to input_nfa (TotalNFA, whole-building), excluding
    exclude_name (case-insensitive substring match, so a new prospect never matches itself).

    When input_district/input_city are supplied, a same-district comparable ranks ahead of a
    same-city-but-different-district one, which ranks ahead of everyone else (change
    rank-comparables-by-location, 2026-09-15) — this tier ordering is unchanged by task 2.4 below,
    and is still the one judgment call ("district beats size") flagged for Head-of-PM sign-off.

    WITHIN each of those three tiers (task 2.4, 2026-09-16, revised task 2.5, 2026-09-16): a
    candidate that has real coordinates on BOTH sides (this input project's input_lat/input_lon, and
    the candidate's own lat/lon — stored on every MASTER_COMPARABLES record that
    Fact_ProjectLocation.csv matched) AND sits within DISTANCE_TIER_KM (1 km) of the input project is
    ranked by real great-circle distance, ahead of every candidate that doesn't clear both those bars
    — which keeps ranking by NFA delta exactly as before. Beyond DISTANCE_TIER_KM, a coordinate pair
    is NOT trusted as "near" and the candidate ranks by NFA delta like any other (task 2.5: your own
    call — "if the distance is more than [1km] then the comparison base on basic information as
    is"). This is a strict tie-break INSIDE a tier, not a new tier: it never lets a farther-district
    candidate beat a same-district one, so it changes nothing about the ordinal claim already queued
    for sign-off, only what "closest" means once you're already comparing same-district (or
    same-city) candidates to each other, and only within 1km. No weight is invented to blend km
    against NFA — a candidate is sorted by one measure or the other, never a combination of both.

    WITHIN each tier and coordinate-precision bucket, a candidate whose `nfa` sits within
    `SIZE_SIMILARITY_BAND` (±50%) of `input_nfa` now ranks ahead of one that doesn't (change
    prefer-similar-size-comparables, 2026-09-18) — checked BEFORE hand-verified status, so a badly
    -sized verified comparable no longer automatically beats a similarly-sized unverified one. Most
    real intake forms carry no District/City, which collapses location tier to a constant for every
    candidate — without this size preference, hand-verified status alone would decide most real
    projects' comparable set regardless of how far off in size the only verified candidates happen
    to be. If no candidate clears the band, ranking falls back to nearest-by-NFA exactly as before —
    this is a preference, not a filter, and never returns an empty set.

    Omitting all four location arguments — or a project whose district/city matches no candidate and
    has no within-DISTANCE_TIER_KM coordinate match — collapses location tier and coordinate-
    precision to a constant for every candidate, so the sort degenerates to size-tier, then
    verified-status, then `abs(nfa - input_nfa)`. See `derive_product_rate_capped()` below for the
    companion rate-swing cap that applies whenever this near-match tie-break actually changes which
    comparables get picked.

    WITHIN each tier, and WITHIN whichever of task 2.4's two precision buckets a candidate already
    falls into (has a real, within-DISTANCE_TIER_KM coordinate match, or doesn't), a `hand_verified`
    candidate (one of the 8 real detailed-budget projects — see HAND_VERIFIED_COMPARABLES above) now
    ranks ahead of a non-hand_verified one (task 8.1, 2026-09-17 — your rule: "prioritize the 8
    verified projects when both are in range"). Verified-status is checked AFTER the coordinate
    precision bucket, not before it: a first draft of this put it before, which let a hand-verified
    candidate with NO coordinates outrank a real, close, non-verified one purely on verified-status —
    concretely, it let two coordinate-less Hà Nội projects (registry rows R03, R04) beat
    a master-list HCMC project sitting 0.08km from a real HCMC query with a real Apartment rate. That
    would have reversed task 2.4's "prefer the more precise measure" principle rather than refining it,
    and since both of derive_product_rate_capped()'s two branches would have agreed on the same
    geographically-wrong pick, its ±20% swing cap would never have caught it either. Caught by testing
    this exact scenario before shipping it, not assumed safe from reading the code. With verified-rank
    scoped inside the precision bucket instead, it cannot do that: it only breaks ties among candidates
    that were already judged equally precise, so a real nearby comparable always still wins over a
    distant (even verified) one. Where this DOES have real reach is the far more common real case —
    tier 2 ("no location match"), which is where almost every real project sits today, since most
    intake forms carry no District/City (measured-effect.md: zero effect on Wayne Tower or the standard
    sample from the district/distance work alone) — there, a hand-verified candidate now displaces a
    Master-List one at the same NFA-delta tie-break, which is where this rule was actually aimed.

    DISTANCE_COMPARISON_ENABLED (task 8.6, 2026-09-17 — your instruction: disable it for now, revisit
    later) gates task 2.4/2.5's whole coordinate-distance mechanism off at the source. While False,
    input_lat/input_lon are accepted but never read here — every candidate falls straight to the
    "basic information" branch (district/city tier, then verified-status, then NFA-delta), exactly as
    if no project ever had coordinates. This is the one switch: DISTANCE_TIER_KM, MAX_DISTANCE_RATE_SWING,
    _haversine_km(), and derive_product_rate_capped()'s cap logic are all untouched and resume exactly
    where they left off the moment this flag goes back to True."""
    exclude_key = reference_projects.key_for_name(exclude_name) if exclude_name else None
    candidates = [c for c in MASTER_COMPARABLES
                  if not (exclude_key and c.get('key') == exclude_key)
                  and not (exclude_name and c['name'].strip().lower() in exclude_name.strip().lower())]
    input_has_coords = DISTANCE_COMPARISON_ENABLED and input_lat is not None and input_lon is not None

    def sort_key(c):
        tier = _location_tier(c.get('district'), c.get('city'), input_district, input_city)
        # change prefer-similar-size-comparables, 2026-09-18 — checked BEFORE verified_rank so a
        # badly-sized hand-verified comparable no longer automatically beats a similarly-sized one
        # that isn't. See design.md D1: this is the same "a closer match beats verified-status"
        # principle task 8.1 already applied to coordinate precision, one dimension earlier.
        size_tier = 0 if (input_nfa and abs(c['nfa'] - input_nfa) / input_nfa <= SIZE_SIMILARITY_BAND) else 1
        verified_rank = 0 if c.get('hand_verified') else 1
        if input_has_coords and _has_coords(c):
            dist = _haversine_km(input_lat, input_lon, c['lat'], c['lon'])
            if dist <= DISTANCE_TIER_KM:
                return (tier, size_tier, 0, verified_rank, dist)
        return (tier, size_tier, 1, verified_rank, abs(c['nfa'] - input_nfa))

    ranked = sorted(candidates, key=sort_key)
    return ranked[:n]


COMPARABLE_VAT_BASIS_CSV = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified', 'Ref_ComparableVATBasis.csv')
VAT_BASES = ('incl', 'excl')


class VatBasisError(ValueError):
    """Ref_ComparableVATBasis.csv is malformed. The message names the row."""


def load_vat_basis(path=None):
    """{(RefKey or project name casefolded, product): 'incl' | 'excl'} from the hand-checked table (change
    apply-head-of-pm-decisions-2026-10, group 4, decision D8/M2-a). A missing file gives an empty table, so every
    comparable is then treated as including VAT and flagged. A row with an unknown basis or no source stops."""
    path = path or COMPARABLE_VAT_BASIS_CSV
    if not os.path.exists(path):
        return {}
    table = {}
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        need = ['project_key', 'product', 'basis', 'source_text', 'checked_on']
        missing = [c for c in need if c not in (reader.fieldnames or [])]
        if missing:
            raise VatBasisError(f'Ref_ComparableVATBasis.csv is missing columns: {", ".join(missing)}.')
        for row_no, r in enumerate(reader, start=2):
            key, product, basis = (r['project_key'] or '').strip(), (r['product'] or '').strip(), (r['basis'] or '').strip()
            if not key or not product:
                raise VatBasisError(f'Ref_ComparableVATBasis.csv row {row_no}: project_key and product are required.')
            if basis not in VAT_BASES:
                raise VatBasisError(f'Ref_ComparableVATBasis.csv row {row_no} ({key}, {product}): basis "{basis}" '
                                    f'must be incl or excl.')
            if not (r['source_text'] or '').strip():
                raise VatBasisError(f'Ref_ComparableVATBasis.csv row {row_no} ({key}, {product}): source_text is blank. '
                                    f'Every entry needs its source.')
            ref_key = (r.get('RefKey') or '').strip()
            if ref_key:
                table[(ref_key, product)] = basis
            table[(key.casefold(), product)] = basis
    return table


def vat_basis_of(vat, comparable, product):
    """'incl', 'excl' or None (not in the table) for a comparable and product. `vat` is dict(pct=..., table=...)."""
    table = (vat or {}).get('table', {})
    if comparable.get('key') and (comparable['key'], product) in table:
        return table[(comparable['key'], product)]
    return table.get((comparable['name'].strip().casefold(), product))


def _on_incl_vat(vat, comparable, product, rate):
    """The rate on an including-VAT basis: an excl. rate times (1 + VAT of the budget period's first month); an
    incl. or unknown rate as it is. Without `vat` (older callers and tests) nothing is converted."""
    if vat and vat_basis_of(vat, comparable, product) == 'excl':
        return rate * (1 + vat['pct'] / 100)
    return rate


def vat_flags_for(vat, used_by_product):
    """{product: [comparable names used in that product's average that are not in the VAT table]}, for the analysis."""
    if not vat:
        return {}
    out = {}
    for product, used in used_by_product.items():
        names = [c['name'] for c in used if vat_basis_of(vat, c, product) is None]
        if names:
            out[product] = names
    return out


def derive_mgmt_rate(comparables, all_ranked=None, vat=None):
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
    rate = round(sum(_on_incl_vat(vat, c, 'Apartment', c['mgmt_rate']) for c in rated) / len(rated))
    vats = {c['mgmt_rate_vat'] for c in rated}
    if len(vats) > 1:
        note = (note + ' ' if note else '') + f"Averaged across mixed VAT conventions ({', '.join(sorted(v for v in vats if v))}) — see module docstring."
    return rate, note


def derive_mgmt_rate_capped(project_nfa, exclude_name, input_district=None, input_city=None,
                            input_lat=None, input_lon=None, n=2, vat=None):
    """The blended whole-property rate over the n nearest comparables, with the same ±20% swing cap as
    derive_product_rate_capped(): when the within-1km distance tie-break changed which comparables are used, the
    rate is clamped to ±MAX_DISTANCE_RATE_SWING of what the basic-information ranking (no coordinates) gives.
    Returns (rate, comparables, note, all_ranked) like derive_mgmt_rate(), with all_ranked the coordinate-aware
    full ranking."""
    n_full = len(MASTER_COMPARABLES)
    loc = dict(input_district=input_district, input_city=input_city)
    all_ranked = nearest_comparables(project_nfa, exclude_name=exclude_name, n=n_full,
                                     input_lat=input_lat, input_lon=input_lon, **loc)
    used = all_ranked[:n]
    rate, note = derive_mgmt_rate(used, all_ranked=all_ranked, vat=vat)
    if rate is None or input_lat is None or input_lon is None:
        return rate, used, note, all_ranked
    basic_ranked = nearest_comparables(project_nfa, exclude_name=exclude_name, n=n_full, **loc)
    basic_rate, _basic_note = derive_mgmt_rate(basic_ranked[:n], all_ranked=basic_ranked, vat=vat)
    if basic_rate is None or {c['name'] for c in used} == {c['name'] for c in basic_ranked[:n]}:
        return rate, used, note, all_ranked
    lo, hi = basic_rate * (1 - MAX_DISTANCE_RATE_SWING), basic_rate * (1 + MAX_DISTANCE_RATE_SWING)
    if lo <= rate <= hi:
        return rate, used, note, all_ranked
    clamped = round(hi if rate > hi else lo)
    clamp_note = (f"A within-{DISTANCE_TIER_KM:g}km real comparable would have implied a blended {rate:,.0f} "
                  f"VND/m²/month — clamped to {clamped:,.0f} (±{MAX_DISTANCE_RATE_SWING:.0%} of the "
                  f"{basic_rate:,.0f} 'basic information as is' figure).")
    return clamped, used, ((note + ' ') if note else '') + clamp_note, all_ranked


def derive_product_rate(all_ranked, product, n=2, vat=None):
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
    rate = round(sum(_on_incl_vat(vat, c, product, c['rates'][product]) for c in used) / len(used))
    note = None
    if len(have_rate) < n:
        note = f'Only {len(have_rate)} comparable(s) in the whole {len(all_ranked)}-project table have a real {product} rate — averaged across all of them, not just the nearest {n}.'
    return rate, used, note


def derive_product_rate_capped(project_nfa, exclude_name, product, input_district=None, input_city=None,
                                input_lat=None, input_lon=None, n=2, vat=None):
    """derive_product_rate(), but caps the effect of task 2.5's within-DISTANCE_TIER_KM tie-break
    (your rule, 2026-09-16: "if the project [is] nearly within 1km ... the swing should go up-to max
    20%, if the distance is more than [that] ... the comparison base on basic information as is").

    Runs nearest_comparables() TWICE for the same project: once exactly as given (which may prefer a
    within-1km comparable by real distance), and once with input_lat/input_lon withheld — "basic
    information as is", i.e. district/city/NFA only, the pre-task-2.4 mechanism. If both selections
    land on the same comparable set, there is nothing to cap (most projects, most of the time — a
    within-1km match is rare, see measured-effect.md's coverage section) and this returns exactly
    what derive_product_rate() would have. Only when a within-1km match actually SWAPPED which
    comparables get used does this clamp the resulting rate to within MAX_DISTANCE_RATE_SWING (20%)
    of what the basic-information rate would have been — never further, per your rule.

    Returns (rate, used, note, all_ranked) — all_ranked is the coordinate-aware full ranking (NOT the
    basic one), for callers that need the full list for something else (e.g. derive_mgmt_rate's
    fallback, or printing the selected comparables)."""
    n_full = len(MASTER_COMPARABLES)
    all_ranked = nearest_comparables(project_nfa, exclude_name=exclude_name, n=n_full,
                                      input_district=input_district, input_city=input_city,
                                      input_lat=input_lat, input_lon=input_lon)
    rate, used, note = derive_product_rate(all_ranked, product, n=n, vat=vat)

    if rate is None or input_lat is None or input_lon is None:
        return rate, used, note, all_ranked

    basic_ranked = nearest_comparables(project_nfa, exclude_name=exclude_name, n=n_full,
                                        input_district=input_district, input_city=input_city)
    basic_rate, basic_used, _basic_note = derive_product_rate(basic_ranked, product, n=n, vat=vat)
    if basic_rate is None or {c['name'] for c in used} == {c['name'] for c in basic_used}:
        return rate, used, note, all_ranked   # same selection either way — nothing to cap

    lo, hi = basic_rate * (1 - MAX_DISTANCE_RATE_SWING), basic_rate * (1 + MAX_DISTANCE_RATE_SWING)
    if lo <= rate <= hi:
        return rate, used, note, all_ranked   # within the cap already — no clamp needed
    clamped = round(hi if rate > hi else lo)
    clamp_note = (f"A within-{DISTANCE_TIER_KM:g}km real comparable would have implied {rate:,.0f} "
                  f"VND/m²/month — clamped to {clamped:,.0f} (±{MAX_DISTANCE_RATE_SWING:.0%} of the "
                  f"{basic_rate:,.0f} 'basic information as is' figure — your rule, 2026-09-16).")
    note = (note + ' ' if note else '') + clamp_note
    return clamped, used, note, all_ranked


BLENDED_FALLBACK_NOTE = 'No comparable has a real Apartment rate — fell back to the whole-property blended rate.'


def apartment_range(project, vat_pct, vat_inclusive=True):
    """(RangeResult, applied rate or None) for the RM.AP real-budget range (change
    price-fee-and-parking-from-portfolio, design D3/D4): the median apartment management-fee rate of the real budgets
    of Savills-managed projects, the project itself left out by name key or NFA, converted to the deliverable's VAT
    basis at the budget period's first month. None, None when the values file is absent (rollback)."""
    import real_budget_ranges as rbr
    rows = rbr.load_values()
    res = rbr.price_line('RM.AP', rows, nfa=project.get('total_nfa') or 0, vat_rate=vat_pct / 100.0,
                         vat_inclusive=vat_inclusive, self_name=project.get('name'))
    return res, rbr.applied_rate(res, vat_pct, vat_inclusive)


RANGE_SOURCE_NOTE = ('The Apartment rate is the median of the real-budget range of Savills-managed projects; the '
                     'two nearest comparables are shown for reference and drive the benchmark verdict only.')


def resolve_product_rates(project, vat_table=None, vat_inclusive=True):
    """The one place each product's applied management-fee rate (VND/m²/month) is decided — change
    `use-operating-project-actuals`, P5. Both generators call this once per run and read every rate
    they write or show from its result, so the deliverable's RM.* rows, its '0. Info' fee table and
    Comparison sheet, and the analysis workbook's Management Fee / Comparison / Summary sheets cannot
    disagree. Before P5 the deliverable derived the Apartment rate twice and the other products' rates
    three times, and the analysis derived both again on its own.

    Order of sources, the same for both workbooks:
      Apartment  derive_product_rate_capped() (the ±20% within-1km swing cap applies); when no
                 comparable carries an Apartment rate at all, the blended whole-property rate
                 (derive_mgmt_rate over the 2 nearest comparables) — before P5 only the deliverable
                 had this step.
      others     derive_product_rate_capped(): the same coordinate-aware ranking with the same ±20% swing
                 cap (group 4); when no comparable carries that product's rate, the project's applied
                 Apartment rate. The blended fallback is capped the same way (derive_mgmt_rate_capped).
      entered    (P1) a rate the PM entered on the Product Mix row, read into
                 project['operating']['rates'], ranks ahead of both and is not capped. An entered
                 Apartment rate is then also the applied Apartment rate the fallback uses. The
                 comparable-derived rate is still computed and kept as `comparable_rate` for the
                 Comparison sheets and the printout.

    `project` is read_input()'s dict (name, total_nfa, district, city, lat, lon, products).
    Returns a dict:
      apartment_rate, apartment_used, apartment_note, apartment_source ('comparable' or
        'blended-fallback'); apartment_used is [] on the blended fallback
      comparables  the comparables the Comparison sheets show: apartment_used, or the 2 nearest
                   comparables on the blended fallback
      rate_note    the note the Comparison sheets show (apartment_note, plus BLENDED_FALLBACK_NOTE)
      all_ranked   the coordinate-aware full ranking
      products     {product: dict(rate, used, note, source, is_fallback, vat, comparable_rate)} for
                   every product with area, in the order of project['products']; source is
                   'entered', 'comparable', 'apartment-fallback' or (Apartment only)
                   'blended-fallback'; vat is the entered VAT basis (None otherwise); comparable_rate
                   is the comparable-derived rate (None when no comparable has one)
      apartment_comparable_rate  the Apartment rate the comparables give, whether or not one was entered
      apartment_entered          dict(rate, vat) when the PM entered the Apartment rate, else None
      vat_pct, vat_flags         (group 4) the VAT rate excl.-VAT comparable rates were multiplied by (the general rate
                                 of the budget period's first month), and {product: [comparable names used that are
                                 not in Ref_ComparableVATBasis.csv]}, which are treated as including VAT. A rate the
                                 PM entered is never converted.
      apartment_rates_on_basis   (group 9) each of `comparables`' real Apartment rate on the basis the average used
                                 (excl.-VAT rates converted as above), None where it has none; the benchmark verdict
                                 and the peer projections compare against these, not the rates as quoted.
    Raises ValueError when no comparable has any management-fee rate."""
    loc = dict(input_district=project.get('district'), input_city=project.get('city'))
    bp = project.get('budget_period')
    first_y, first_m = (bp.months[0] if bp is not None else budget_period.DEFAULT_START)
    vat = dict(pct=utility_tariffs.vat_rate(first_y, first_m),
               table=load_vat_basis() if vat_table is None else vat_table)
    apt_rate, apt_used, apt_note, all_ranked = derive_product_rate_capped(
        project['total_nfa'], project['name'], 'Apartment',
        input_lat=project.get('lat'), input_lon=project.get('lon'), vat=vat, **loc)
    comparables, rate_note, apt_source = apt_used, apt_note, 'comparable'
    if apt_rate is None:
        apt_rate, comparables, blended_note, _blended_ranked = derive_mgmt_rate_capped(
            project['total_nfa'], project['name'], input_lat=project.get('lat'), input_lon=project.get('lon'),
            vat=vat, **loc)
        rate_note = ((blended_note + '  ') if blended_note else '') + BLENDED_FALLBACK_NOTE
        apt_source = 'blended-fallback'
    entered = ((project.get('operating') or {}).get('rates')) or {}
    apt_comparable_rate = apt_rate
    # Change price-fee-and-parking-from-portfolio (design D3): the real-budget range ranks between the entered rate
    # and the comparables. The comparables stay selected for the Comparison sheets and the benchmark verdict.
    apt_range, range_rate = apartment_range(project, vat['pct'], vat_inclusive)
    if range_rate is not None:
        apt_rate, apt_source = range_rate, 'range'
        rate_note = ((rate_note + '  ') if rate_note else '') + RANGE_SOURCE_NOTE
    apt_entered = entered.get('Apartment')
    if apt_entered:
        apt_rate, apt_source = apt_entered['rate'], 'entered'
    if apt_rate is None:
        raise ValueError("Could not derive a management-fee rate — no comparable in the master table has one.")

    products = {}
    for product, info in (project.get('products') or {}).items():
        if not (info or {}).get('nfa'):
            continue
        if product == 'Apartment':
            products[product] = dict(rate=apt_rate, used=[] if apt_entered else apt_used, note=apt_note,
                                     source=apt_source, is_fallback=False,
                                     vat=apt_entered['vat'] if apt_entered else None,
                                     comparable_rate=apt_comparable_rate)
            continue
        rate, used, note, _ranked = derive_product_rate_capped(
            project['total_nfa'], project['name'], product,
            input_lat=project.get('lat'), input_lon=project.get('lon'), vat=vat, **loc)
        if product in entered:
            products[product] = dict(rate=entered[product]['rate'], used=[], note=note, source='entered',
                                     is_fallback=False, vat=entered[product]['vat'], comparable_rate=rate)
        elif rate is None:
            products[product] = dict(rate=apt_rate, used=[], note=note, source='apartment-fallback',
                                     is_fallback=True, vat=None, comparable_rate=None)
        else:
            products[product] = dict(rate=rate, used=used, note=note, source='comparable',
                                     is_fallback=False, vat=None, comparable_rate=rate)
    return dict(apartment_rate=apt_rate, apartment_used=apt_used, apartment_note=apt_note,
                apartment_source=apt_source, comparables=comparables, rate_note=rate_note,
                all_ranked=all_ranked, products=products, apartment_comparable_rate=apt_comparable_rate,
                apartment_entered=apt_entered, vat_pct=vat['pct'], vat_inclusive=vat_inclusive,
                apartment_range=apt_range, apartment_range_rate=range_rate,
                apartment_rates_on_basis=[_on_incl_vat(vat, c, 'Apartment', r) if r else None
                                          for c in comparables for r in [(c.get('rates') or {}).get('Apartment')]],
                vat_flags=vat_flags_for(vat, {**{'Apartment': apt_used if apt_source == 'comparable' else comparables},
                                              **{k: v['used'] for k, v in products.items() if k != 'Apartment'}}))
