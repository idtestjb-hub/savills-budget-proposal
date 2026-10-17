"""Unit tests for master_comparables.py (comparable ranking and management-fee rate derivation).

Covered: _location_tier, nearest_comparables, derive_mgmt_rate, derive_product_rate,
derive_product_rate_capped, comparable_match_basis.
Not covered: the CSV loaders and _merge_comparables beyond "imports with the CSVs absent"
(they need the reference CSVs), _haversine_km on its own.

The module is loaded under a private name with the two reference CSVs reported as absent, so the
tests never read anything under data/. Each test then swaps in an invented MASTER_COMPARABLES.
Invented data only: fictional towers and districts.

Rule sources, in order: docs/05-decisions.md (2026-09-17 location + provenance ranking, 2026-09-18
size band), then the function docstrings. Rules still open are marked "not settled".
"""
import importlib.util
import os
import unicodedata
from unittest import mock

import pytest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'master_comparables.py')


@pytest.fixture(scope='module')
def mc_module():
    real_exists = os.path.exists

    def fake_exists(path):
        if str(path).lower().endswith('.csv'):
            return False
        return real_exists(path)

    with mock.patch('os.path.exists', side_effect=fake_exists):
        spec = importlib.util.spec_from_file_location('master_comparables_under_test', SRC)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mc(mc_module, monkeypatch):
    """The module with a clean, known configuration; the pool is set per test."""
    monkeypatch.setattr(mc_module, 'MASTER_COMPARABLES', [])
    monkeypatch.setattr(mc_module, 'SIZE_SIMILARITY_BAND', 0.50)
    monkeypatch.setattr(mc_module, 'DISTANCE_COMPARISON_ENABLED', False)
    return mc_module


def comp(name, nfa, district=None, city=None, rate=None, vat=None, verified=False,
         rates=None, lat=None, lon=None):
    c = dict(name=name, nfa=nfa, district=district, city=city, mgmt_rate=rate, mgmt_rate_vat=vat,
             rates=rates if rates is not None else {'Apartment': rate})
    if verified:
        c['hand_verified'] = True
    if lat is not None:
        c['lat'], c['lon'] = lat, lon
    return c


def names(items):
    return [c['name'] for c in items]


def use(mc, monkeypatch, pool):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', pool)


# ---------------------------------------------------------------- import without CSVs

def test_imports_without_csvs_and_keeps_only_rankable_hand_verified(mc_module):
    # rule source: docstring of _merge_comparables (excluded_from_ranking entries never reach the pool)
    pool = mc_module.MASTER_COMPARABLES
    expected = [c for c in mc_module.HAND_VERIFIED_COMPARABLES if not c.get('excluded_from_ranking')]
    assert len(pool) == len(expected) > 0
    assert all(c.get('hand_verified') for c in pool)
    assert not any(c.get('excluded_from_ranking') for c in pool)


# ---------------------------------------------------------------- _location_tier

@pytest.mark.parametrize('cd, cc, idist, icity, tier', [
    ('Quan Alpha', 'Thanh pho X', 'Quan Alpha', 'Thanh pho X', 0),   # same district
    ('Quan Alpha', 'Thanh pho X', 'Quan Beta', 'Thanh pho X', 1),    # same city, other district
    ('Quan Alpha', 'Thanh pho X', 'Quan Beta', 'Thanh pho Y', 2),    # nothing in common
    ('Quan Alpha', 'Thanh pho X', '  QUAN alpha ', None, 0),         # case and padding ignored
    ('Quan Alpha', 'Thanh pho X', None, 'thanh pho x', 1),           # input has a city only
])
def test_location_tier_levels(mc, cd, cc, idist, icity, tier):
    assert mc._location_tier(cd, cc, idist, icity) == tier


def test_location_tier_input_without_location_is_tier2(mc):
    assert mc._location_tier('Quan Alpha', 'Thanh pho X', None, None) == 2
    assert mc._location_tier('Quan Alpha', 'Thanh pho X', '', '') == 2


def test_location_tier_blank_on_either_side_never_matches(mc):
    # a blank is never treated as a match
    assert mc._location_tier(None, None, 'Quan Alpha', 'Thanh pho X') == 2
    assert mc._location_tier('', '', 'Quan Alpha', 'Thanh pho X') == 2
    assert mc._location_tier(None, 'Thanh pho X', 'Quan Alpha', None) == 2   # input has no city
    assert mc._location_tier('', None, '', None) == 2                       # blank equals blank is no match


def test_location_tier_candidate_without_district_can_still_match_city(mc):
    assert mc._location_tier(None, 'Thanh pho X', 'Quan Alpha', 'Thanh pho X') == 1


def test_location_tier_unicode_forms_compare_equal(mc):
    composed = unicodedata.normalize('NFC', 'Quận Ba')
    decomposed = unicodedata.normalize('NFD', 'Quận Ba')
    assert composed != decomposed
    assert mc._location_tier(decomposed, None, composed, None) == 0


def test_location_tier_same_district_name_in_other_city_is_tier0(mc):
    # not settled: district is compared without the city, so a same-named district in another city
    # counts as "same district". Pinned as current behaviour.
    assert mc._location_tier('Quan Alpha', 'Thanh pho Y', 'Quan Alpha', 'Thanh pho X') == 0


# ---------------------------------------------------------------- nearest_comparables

def test_nearest_ranks_by_nfa_delta_without_location(mc, monkeypatch):
    use(mc, monkeypatch, [comp('Far', 20000), comp('Near', 10200), comp('Mid', 11500), comp('Low', 9000)])
    assert names(mc.nearest_comparables(10000, n=4)) == ['Near', 'Low', 'Mid', 'Far']


def test_nearest_n_limits_and_oversized_n_returns_whole_pool(mc, monkeypatch):
    use(mc, monkeypatch, [comp('A', 10000), comp('B', 10100), comp('C', 10200)])
    assert names(mc.nearest_comparables(10000, n=2)) == ['A', 'B']
    assert len(mc.nearest_comparables(10000, n=99)) == 3
    assert mc.nearest_comparables(10000, n=0) == []


def test_nearest_empty_pool_returns_empty(mc):
    assert mc.nearest_comparables(10000) == []


def test_nearest_does_not_reorder_or_change_the_pool(mc, monkeypatch):
    pool = [comp('Far', 20000), comp('Near', 10100)]
    use(mc, monkeypatch, pool)
    mc.nearest_comparables(10000, n=2)
    assert names(pool) == ['Far', 'Near']


def test_nearest_exclude_name_is_case_insensitive(mc, monkeypatch):
    use(mc, monkeypatch, [comp('Tower Alpha', 10000), comp('Tower Beta', 10500)])
    assert names(mc.nearest_comparables(10000, exclude_name='TOWER alpha', n=5)) == ['Tower Beta']
    assert names(mc.nearest_comparables(10000, exclude_name='  tower alpha  ', n=5)) == ['Tower Beta']


def test_nearest_exclude_name_matches_when_candidate_name_is_inside_it(mc, monkeypatch):
    # rule source: docstring ("case-insensitive substring match, so a new prospect never matches itself")
    use(mc, monkeypatch, [comp('Tower Alpha', 10000), comp('Tower Beta', 10500)])
    assert names(mc.nearest_comparables(10000, exclude_name='Tower Alpha (new prospect)', n=5)) == ['Tower Beta']


def test_nearest_exclude_name_not_matching_a_longer_candidate_name(mc, monkeypatch):
    # not settled: the substring test runs candidate-in-exclude only, so 'Tower Alpha' does not
    # exclude a candidate called 'Tower Alpha Annex'. Pinned as current behaviour.
    use(mc, monkeypatch, [comp('Tower Alpha Annex', 10000), comp('Tower Beta', 10500)])
    assert names(mc.nearest_comparables(10000, exclude_name='Tower Alpha', n=5)) == ['Tower Alpha Annex', 'Tower Beta']


def test_nearest_same_district_beats_nearer_size_elsewhere(mc, monkeypatch):
    # 2026-09-17 decision: district beats city beats no match, ahead of size
    use(mc, monkeypatch, [
        comp('Elsewhere', 10000, 'Quan Gamma', 'Thanh pho Y'),
        comp('SameCity', 10100, 'Quan Beta', 'Thanh pho X'),
        comp('SameDistrict', 14000, 'Quan Alpha', 'Thanh pho X'),
    ])
    got = mc.nearest_comparables(10000, n=3, input_district='Quan Alpha', input_city='Thanh pho X')
    assert names(got) == ['SameDistrict', 'SameCity', 'Elsewhere']


def test_nearest_missing_location_data_does_not_get_a_tier_bonus(mc, monkeypatch):
    use(mc, monkeypatch, [comp('NoLocation', 10000), comp('SameCity', 12000, 'Quan Beta', 'Thanh pho X')])
    got = mc.nearest_comparables(10000, n=2, input_district='Quan Alpha', input_city='Thanh pho X')
    assert names(got) == ['SameCity', 'NoLocation']


def test_nearest_in_band_beats_hand_verified_out_of_band(mc, monkeypatch):
    # 2026-09-18 decision: a similarly-sized unverified comparable beats a badly-sized verified one
    use(mc, monkeypatch, [comp('VerifiedFar', 22000, verified=True), comp('UnverifiedClose', 11000)])
    assert names(mc.nearest_comparables(10000, n=2)) == ['UnverifiedClose', 'VerifiedFar']


def test_nearest_verified_beats_closer_size_when_both_in_band(mc, monkeypatch):
    # 2026-09-17 decision: within a tier, a hand-verified project outranks an auto-scraped one
    use(mc, monkeypatch, [comp('UnverifiedNear', 10050), comp('VerifiedFarther', 13000, verified=True)])
    assert names(mc.nearest_comparables(10000, n=2)) == ['VerifiedFarther', 'UnverifiedNear']


def test_nearest_size_band_upper_edge_is_inclusive(mc, monkeypatch):
    # not settled: the +/-50% band is a judgment call. Exactly 50% above is inside, one more m2 is out.
    # If 15000 were outside, the verified 15001 would win; inside means the unverified 15000 wins.
    use(mc, monkeypatch, [comp('Edge50', 15000), comp('Over50Verified', 15001, verified=True)])
    assert names(mc.nearest_comparables(10000, n=2)) == ['Edge50', 'Over50Verified']


def test_nearest_size_band_lower_edge_is_inclusive(mc, monkeypatch):
    # not settled: same band, below the input
    use(mc, monkeypatch, [comp('Edge50', 5000), comp('Under50Verified', 4999, verified=True)])
    assert names(mc.nearest_comparables(10000, n=2)) == ['Edge50', 'Under50Verified']


def test_nearest_band_value_is_read_from_the_module_constant(mc, monkeypatch):
    # not settled: band width. Narrowing it moves the 12,000 candidate out of the band.
    use(mc, monkeypatch, [comp('Unverified12k', 12000), comp('Verified16k', 16000, verified=True)])
    assert names(mc.nearest_comparables(10000, n=2)) == ['Unverified12k', 'Verified16k']
    monkeypatch.setattr(mc, 'SIZE_SIMILARITY_BAND', 0.10)
    assert names(mc.nearest_comparables(10000, n=2)) == ['Verified16k', 'Unverified12k']


def test_nearest_nobody_in_band_still_returns_n_by_provenance_then_nfa(mc, monkeypatch):
    # rule source: docstring ("a preference, not a filter, and never returns an empty set")
    use(mc, monkeypatch, [comp('FarA', 30000), comp('FarB', 40000), comp('FarVerified', 90000, verified=True)])
    got = mc.nearest_comparables(10000, n=2)
    assert len(got) == 2
    assert names(got) == ['FarVerified', 'FarA']   # verified first, then smallest NFA delta


def test_nearest_equal_nfa_ties_keep_pool_order(mc, monkeypatch):
    use(mc, monkeypatch, [comp('First', 10000), comp('Second', 10000)])
    assert names(mc.nearest_comparables(10000, n=2)) == ['First', 'Second']


def test_nearest_distance_ignored_while_switch_is_off(mc, monkeypatch):
    # not settled: DISTANCE_COMPARISON_ENABLED is False by instruction (2026-09-17).
    use(mc, monkeypatch, [
        comp('NearbyButBigger', 12000, lat=10.7700, lon=106.7000),
        comp('SameSizeNoCoords', 10000),
    ])
    got = mc.nearest_comparables(10000, n=2, input_lat=10.7700, input_lon=106.7000)
    assert names(got) == ['SameSizeNoCoords', 'NearbyButBigger']


def test_nearest_within_1km_ranks_first_when_switch_is_on(mc, monkeypatch):
    # rule source: docstring (within DISTANCE_TIER_KM a candidate ranks by distance ahead of NFA delta)
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    use(mc, monkeypatch, [
        comp('SameSizeNoCoords', 10000),
        comp('Near500m', 12000, lat=10.7745, lon=106.7000),      # about 0.5 km north
    ])
    got = mc.nearest_comparables(10000, n=2, input_lat=10.7700, input_lon=106.7000)
    assert names(got) == ['Near500m', 'SameSizeNoCoords']


def test_nearest_beyond_1km_falls_back_to_nfa_delta_when_switch_is_on(mc, monkeypatch):
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    use(mc, monkeypatch, [
        comp('SameSizeNoCoords', 10000),
        comp('Far2km', 12000, lat=10.7880, lon=106.7000),         # about 2 km north
    ])
    got = mc.nearest_comparables(10000, n=2, input_lat=10.7700, input_lon=106.7000)
    assert names(got) == ['SameSizeNoCoords', 'Far2km']


def test_nearest_distance_never_beats_a_better_location_tier(mc, monkeypatch):
    # rule source: docstring ("a strict tie-break INSIDE a tier, not a new tier")
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    use(mc, monkeypatch, [
        comp('NearbyOtherCity', 10000, 'Quan Gamma', 'Thanh pho Y', lat=10.7710, lon=106.7000),
        comp('SameDistrictNoCoords', 13000, 'Quan Alpha', 'Thanh pho X'),
    ])
    got = mc.nearest_comparables(10000, n=2, input_district='Quan Alpha', input_city='Thanh pho X',
                                 input_lat=10.7700, input_lon=106.7000)
    assert names(got) == ['SameDistrictNoCoords', 'NearbyOtherCity']


# ---------------------------------------------------------------- derive_mgmt_rate

def test_mgmt_rate_is_rounded_average_of_rated_comparables(mc):
    rate, note = mc.derive_mgmt_rate([comp('A', 1, rate=15000, vat='incl. VAT'),
                                      comp('B', 1, rate=18000, vat='incl. VAT')])
    assert rate == 16500
    assert note is None


def test_mgmt_rate_skips_comparables_with_no_rate(mc):
    rate, note = mc.derive_mgmt_rate([comp('A', 1, rate=None), comp('B', 1, rate=15000, vat='incl. VAT')])
    assert rate == 15000
    assert note is None


def test_mgmt_rate_mixed_vat_conventions_are_disclosed(mc):
    rate, note = mc.derive_mgmt_rate([comp('A', 1, rate=15000, vat='incl. VAT'),
                                      comp('B', 1, rate=18000, vat='excl. VAT')])
    assert rate == 16500
    assert 'mixed VAT' in note and 'excl. VAT, incl. VAT' in note


def test_mgmt_rate_nothing_rated_and_no_fallback_pool(mc):
    rate, note = mc.derive_mgmt_rate([comp('A', 1, rate=None), comp('B', 1, rate=None)])
    assert rate is None
    assert 'No comparable' in note


def test_mgmt_rate_falls_back_to_next_nearest_rated_and_says_so(mc):
    near = [comp('A', 1, rate=None), comp('B', 1, rate=None)]
    ranked = near + [comp('C', 1, rate=None), comp('D', 1, rate=17000, vat='incl. VAT'),
                     comp('E', 1, rate=99000, vat='incl. VAT')]
    rate, note = mc.derive_mgmt_rate(near, all_ranked=ranked)
    assert rate == 17000                      # D is the first rated one beyond the selection
    assert 'D' in note and 'next-nearest' in note


def test_mgmt_rate_fallback_pool_without_any_rate_returns_none(mc):
    near = [comp('A', 1, rate=None)]
    rate, note = mc.derive_mgmt_rate(near, all_ranked=near + [comp('B', 1, rate=None)])
    assert rate is None


def test_mgmt_rate_fallback_not_used_when_selection_has_a_rate(mc):
    near = [comp('A', 1, rate=15000, vat='incl. VAT')]
    rate, note = mc.derive_mgmt_rate(near, all_ranked=near + [comp('B', 1, rate=30000)])
    assert rate == 15000 and note is None


def test_mgmt_rate_zero_is_treated_as_no_rate(mc):
    # not settled: the docstring says "rates that aren't None" but the code uses truthiness, so a
    # rate of 0 is dropped like None. Pinned as current behaviour.
    rate, _ = mc.derive_mgmt_rate([comp('A', 1, rate=0), comp('B', 1, rate=15000, vat='incl. VAT')])
    assert rate == 15000


# ---------------------------------------------------------------- derive_product_rate

def ranked_with(product, values):
    return [comp(f'C{i}', 1000 + i, rates=({product: v} if v is not None else {})) for i, v in enumerate(values)]


def test_product_rate_averages_the_n_nearest_that_have_a_rate(mc):
    ranked = ranked_with('Officetel', [None, 20000, 30000, 40000])
    rate, used, note = mc.derive_product_rate(ranked, 'Officetel', n=2)
    assert rate == 25000
    assert names(used) == ['C1', 'C2']       # C0 has no rate and is skipped; C3 is beyond n
    assert note is None


def test_product_rate_respects_ranking_order_not_rate_size(mc):
    ranked = ranked_with('Shophouse', [50000, 10000, 30000])
    rate, used, _ = mc.derive_product_rate(ranked, 'Shophouse', n=1)
    assert rate == 50000 and names(used) == ['C0']


def test_product_rate_thin_pool_is_disclosed(mc):
    ranked = ranked_with('Retail', [None, 24000, None])
    rate, used, note = mc.derive_product_rate(ranked, 'Retail', n=2)
    assert rate == 24000 and names(used) == ['C1']
    assert 'Only 1' in note and '3-project' in note and 'Retail' in note


def test_product_rate_no_comparable_has_a_rate(mc):
    rate, used, note = mc.derive_product_rate(ranked_with('Villas', [None, None]), 'Villas')
    assert rate is None and used == []
    assert 'Villas' in note


def test_product_rate_other_product_rates_do_not_count(mc):
    ranked = ranked_with('Apartment', [15000, 16000])
    rate, used, _ = mc.derive_product_rate(ranked, 'Officetel')
    assert rate is None and used == []


def test_product_rate_blank_zero_and_missing_rates_are_skipped(mc):
    ranked = [comp('A', 1, rates={'Retail': 0}), comp('B', 1, rates={'Retail': None}),
              comp('C', 1, rates={}), {'name': 'D', 'nfa': 1}, comp('E', 1, rates={'Retail': 12000})]
    rate, used, _ = mc.derive_product_rate(ranked, 'Retail', n=2)
    assert rate == 12000 and names(used) == ['E']


def test_product_rate_empty_ranking(mc):
    rate, used, note = mc.derive_product_rate([], 'Apartment')
    assert rate is None and used == [] and note


# ---------------------------------------------------------------- derive_product_rate_capped

def capped_pool(near_rate, near_has_coords=True):
    """Prospect NFA 10,000. 'Exact' matches it by size (rate 10,000, no coordinates).
    'Near' is 20% bigger and, when coordinates are used, sits about 0.5 km from the prospect."""
    near_kwargs = dict(lat=10.7745, lon=106.7000) if near_has_coords else {}
    return [comp('Exact', 10000, rates={'Apartment': 10000}),
            comp('Near', 12000, rates={'Apartment': near_rate}, **near_kwargs)]


COORDS = dict(input_lat=10.7700, input_lon=106.7000)


def test_capped_without_coordinates_equals_plain_ranking(mc, monkeypatch):
    use(mc, monkeypatch, capped_pool(14000))
    rate, used, note, all_ranked = mc.derive_product_rate_capped(10000, 'Prospect', 'Apartment', n=1)
    assert (rate, names(used), note) == (10000, ['Exact'], None)
    assert names(all_ranked) == ['Exact', 'Near']


def test_capped_switch_off_never_swaps_so_nothing_is_clamped(mc, monkeypatch):
    # not settled: with DISTANCE_COMPARISON_ENABLED False the coordinate-aware and basic runs agree
    use(mc, monkeypatch, capped_pool(14000))
    rate, used, note, _ = mc.derive_product_rate_capped(10000, 'Prospect', 'Apartment', n=1, **COORDS)
    assert (rate, names(used)) == (10000, ['Exact'])
    assert note is None


def test_capped_swing_within_20_percent_is_kept(mc, monkeypatch):
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    use(mc, monkeypatch, capped_pool(11500))
    rate, used, note, _ = mc.derive_product_rate_capped(10000, 'Prospect', 'Apartment', n=1, **COORDS)
    assert (rate, names(used), note) == (11500, ['Near'], None)


def test_capped_swing_exactly_20_percent_is_not_clamped(mc, monkeypatch):
    # rule source: docstring ("clamp ... to within MAX_DISTANCE_RATE_SWING (20%)"), edge value
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    use(mc, monkeypatch, capped_pool(12000))
    rate, _, note, _ = mc.derive_product_rate_capped(10000, 'Prospect', 'Apartment', n=1, **COORDS)
    assert rate == 12000 and note is None


def test_capped_swing_above_20_percent_is_clamped_with_a_note(mc, monkeypatch):
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    use(mc, monkeypatch, capped_pool(14000))
    rate, used, note, _ = mc.derive_product_rate_capped(10000, 'Prospect', 'Apartment', n=1, **COORDS)
    assert rate == 12000
    assert names(used) == ['Near']
    assert 'clamped to 12,000' in note and '20%' in note


def test_capped_swing_below_minus_20_percent_is_clamped_up(mc, monkeypatch):
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    use(mc, monkeypatch, capped_pool(7000))
    rate, _, note, _ = mc.derive_product_rate_capped(10000, 'Prospect', 'Apartment', n=1, **COORDS)
    assert rate == 8000
    assert 'clamped to 8,000' in note


def test_capped_same_selection_both_ways_is_never_clamped(mc, monkeypatch):
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    use(mc, monkeypatch, capped_pool(30000, near_has_coords=False))
    rate, used, note, _ = mc.derive_product_rate_capped(10000, 'Prospect', 'Apartment', n=1, **COORDS)
    assert (rate, names(used), note) == (10000, ['Exact'], None)


def test_capped_product_with_no_rate_returns_none_and_the_ranking(mc, monkeypatch):
    use(mc, monkeypatch, capped_pool(14000))
    rate, used, note, all_ranked = mc.derive_product_rate_capped(10000, 'Prospect', 'Officetel', **COORDS)
    assert rate is None and used == [] and 'Officetel' in note
    assert len(all_ranked) == 2


def test_capped_excludes_the_prospect_itself(mc, monkeypatch):
    use(mc, monkeypatch, [comp('Prospect', 10000, rates={'Apartment': 99999}),
                          comp('Other', 11000, rates={'Apartment': 12000})])
    rate, used, _, all_ranked = mc.derive_product_rate_capped(10000, 'prospect', 'Apartment', n=2)
    assert names(used) == ['Other'] and rate == 12000
    assert names(all_ranked) == ['Other']


# ---------------------------------------------------------------- comparable_match_basis

def test_basis_plain_nfa_label_when_no_location(mc):
    assert mc.comparable_match_basis([comp('A', 10000)]) == 'closest Total NFA (whole-building)'
    assert mc.comparable_match_basis([]) == 'closest Total NFA (whole-building)'


def test_basis_reports_best_tier_present(mc):
    cs = [comp('A', 10000, 'Quan Alpha', 'Thanh pho X'), comp('B', 10000, 'Quan Beta', 'Thanh pho X')]
    assert mc.comparable_match_basis(cs, 'Quan Alpha', 'Thanh pho X') == \
        'same District, then closest Total NFA (whole-building)'
    assert mc.comparable_match_basis(cs[1:], 'Quan Alpha', 'Thanh pho X') == \
        'same City/Province, then closest Total NFA (whole-building)'
    assert mc.comparable_match_basis([comp('C', 1, 'Quan Z', 'Thanh pho Q')], 'Quan Alpha', 'Thanh pho X') == \
        'closest Total NFA (whole-building)'


def test_basis_mentions_verified_projects_only_when_one_is_shown(mc):
    assert mc.comparable_match_basis([comp('A', 10000, verified=True)]) == \
        'individually-verified project, then closest Total NFA (whole-building)'
    assert 'verified' not in mc.comparable_match_basis([comp('A', 10000)])


def test_basis_vietnamese_text(mc):
    cs = [comp('A', 10000, 'Quan Alpha', 'Thanh pho X', verified=True)]
    assert mc.comparable_match_basis(cs, 'Quan Alpha', 'Thanh pho X', lang='vi') == \
        'cùng quận/huyện, dự án đã xác minh chi tiết, sau đó gần nhất theo Tổng diện tích NFA (toàn bộ tòa nhà)'
    assert mc.comparable_match_basis([comp('B', 1, 'Quan Beta', 'Thanh pho X')], 'Quan Alpha', 'Thanh pho X',
                                     lang='vi').startswith('cùng tỉnh/thành, ')


def test_basis_flags_a_comparable_outside_the_size_band(mc):
    text = mc.comparable_match_basis([comp('Big Tower', 15001)], input_nfa=10000)
    assert 'Big Tower' in text and '50%' in text and 'no closer-sized comparable' in text
    vi = mc.comparable_match_basis([comp('Big Tower', 15001)], input_nfa=10000, lang='vi')
    assert 'Big Tower' in vi and '50%' in vi


def test_basis_size_band_edge_is_not_flagged(mc):
    # not settled: band width. Exactly 50% off is inside the band, so no note.
    assert 'differs' not in mc.comparable_match_basis([comp('Edge', 15000)], input_nfa=10000)
    assert 'differs' not in mc.comparable_match_basis([comp('Edge', 5000)], input_nfa=10000)
    assert 'Edge' in mc.comparable_match_basis([comp('Edge', 4999)], input_nfa=10000)


def test_basis_no_size_note_without_input_nfa(mc):
    for nfa in (None, 0):
        assert mc.comparable_match_basis([comp('Huge', 10 ** 7)], input_nfa=nfa) == \
            'closest Total NFA (whole-building)'


def test_basis_names_only_the_outsized_comparables(mc):
    text = mc.comparable_match_basis([comp('Okay', 10500), comp('Big', 30000)], input_nfa=10000)
    assert 'Big' in text and 'Okay' not in text


def test_basis_never_claims_distance_while_switch_is_off(mc):
    # not settled: distance comparison is off by instruction
    cs = [comp('A', 10000, lat=10.7745, lon=106.7000)]
    assert 'distance' not in mc.comparable_match_basis(cs, input_lat=10.7700, input_lon=106.7000)


def test_basis_claims_distance_only_for_a_comparable_within_1km(mc, monkeypatch):
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    near = [comp('A', 10000, lat=10.7745, lon=106.7000)]
    far = [comp('B', 10000, lat=10.7880, lon=106.7000)]
    assert mc.comparable_match_basis(near, input_lat=10.7700, input_lon=106.7000) == \
        'closest by real distance (km)'
    assert mc.comparable_match_basis(near, input_lat=10.7700, input_lon=106.7000, lang='vi') == \
        'gần nhất theo khoảng cách thực tế (km)'
    assert 'distance' not in mc.comparable_match_basis(far, input_lat=10.7700, input_lon=106.7000)
    assert 'distance' not in mc.comparable_match_basis(near)                      # no input coordinates
    assert 'distance' not in mc.comparable_match_basis([comp('C', 10000)], input_lat=10.77, input_lon=106.7)


# ------------------------------- group 4 (apply-head-of-pm-decisions-2026-10): distance on, cap on every rate
def test_distance_comparison_is_switched_on_in_the_module(mc_module):
    assert mc_module.DISTANCE_COMPARISON_ENABLED is True


@pytest.fixture
def mc_dist(mc, monkeypatch):
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', True)
    return mc


def _near_far_pool(mc, shop_near, shop_far, apt_near=20_000, apt_far=10_000):
    """'Near' sits 0.1 km from the project but is 40% off in size; 'Far' has no coordinates and is the same size.
    Without coordinates the same-size 'Far' wins; with them the within-1 km 'Near' ranks first."""
    near = comp('Near', 14_000, rate=apt_near, lat=10.7701, lon=106.7001,
                rates={'Apartment': apt_near, 'Shophouse': shop_near})
    far = comp('Far', 10_000, rate=apt_far, rates={'Apartment': apt_far, 'Shophouse': shop_far})
    mc.MASTER_COMPARABLES[:] = [near, far]


def test_a_non_apartment_rate_moved_by_distance_is_capped_at_20_percent(mc_dist):
    _near_far_pool(mc_dist, shop_near=30_000, shop_far=10_000)
    rate, used, note, _ = mc_dist.derive_product_rate_capped(
        10_000, 'ZZ New', 'Shophouse', input_lat=10.7700, input_lon=106.7000, n=1)
    assert [c['name'] for c in used] == ['Near']
    assert rate == 12_000                       # +20% of the 10,000 the basic ranking gives, not 30,000
    assert 'clamped' in note


def test_a_rate_inside_the_cap_is_not_changed(mc_dist):
    _near_far_pool(mc_dist, shop_near=11_000, shop_far=10_000)
    rate, _used, note, _ = mc_dist.derive_product_rate_capped(
        10_000, 'ZZ New', 'Shophouse', input_lat=10.7700, input_lon=106.7000, n=1)
    assert rate == 11_000 and not (note or '').count('clamped')


def test_the_blended_fallback_is_capped_too(mc_dist):
    _near_far_pool(mc_dist, shop_near=None, shop_far=None, apt_near=30_000, apt_far=10_000)
    rate, used, note, _ = mc_dist.derive_mgmt_rate_capped(
        10_000, 'ZZ New', input_lat=10.7700, input_lon=106.7000, n=1)
    assert [c['name'] for c in used] == ['Near'] and rate == 12_000 and 'clamped' in note


@pytest.mark.parametrize('enabled', [True, False])
def test_without_coordinates_the_ranking_and_every_rate_are_the_same_either_way(mc, monkeypatch, enabled):
    monkeypatch.setattr(mc, 'DISTANCE_COMPARISON_ENABLED', enabled)
    _near_far_pool(mc, shop_near=30_000, shop_far=10_000)
    assert names(mc.nearest_comparables(10_000, n=2)) == ['Far', 'Near']
    rate, used, _n, _r = mc.derive_product_rate_capped(10_000, 'ZZ New', 'Shophouse', n=1)
    assert rate == 10_000 and [c['name'] for c in used] == ['Far']
    blended, bused, _note, _r2 = mc.derive_mgmt_rate_capped(10_000, 'ZZ New', n=1)
    assert blended == 10_000 and [c['name'] for c in bused] == ['Far']


# ------------------------------- group 4 (apply-head-of-pm-decisions-2026-10): comparable rates on one VAT basis
def _vat(mc, **entries):
    """A VAT table from {'Name:Product': 'excl'|'incl'}, with a 10% first-month rate (a January 2027 budget)."""
    return dict(pct=10.0, table={(k.split(':')[0].casefold(), k.split(':')[1]): v for k, v in entries.items()})


def test_an_excl_vat_rate_is_raised_before_averaging(mc):
    mc.MASTER_COMPARABLES[:] = [comp('Excl', 10_000, rate=20_000), comp('Incl', 10_000, rate=15_000)]
    ranked = mc.nearest_comparables(10_000, n=2)
    vat = _vat(mc, **{'Excl:Apartment': 'excl', 'Incl:Apartment': 'incl'})
    rate, used, _ = mc.derive_product_rate(ranked, 'Apartment', n=2, vat=vat)
    assert rate == 18_500                       # mean of 22,000 and 15,000
    assert mc.derive_mgmt_rate(ranked, vat=vat)[0] == 18_500


def test_an_unknown_basis_is_used_as_including_vat_and_flagged(mc):
    mc.MASTER_COMPARABLES[:] = [comp('Known', 10_000, rate=20_000), comp('Unknown', 10_000, rate=15_000)]
    ranked = mc.nearest_comparables(10_000, n=2)
    vat = _vat(mc, **{'Known:Apartment': 'excl'})
    rate, used, _ = mc.derive_product_rate(ranked, 'Apartment', n=2, vat=vat)
    assert rate == 18_500
    assert mc.vat_flags_for(vat, {'Apartment': used}) == {'Apartment': ['Unknown']}


def test_without_a_vat_table_nothing_is_converted(mc):
    mc.MASTER_COMPARABLES[:] = [comp('Excl', 10_000, rate=20_000), comp('Incl', 10_000, rate=15_000)]
    ranked = mc.nearest_comparables(10_000, n=2)
    assert mc.derive_product_rate(ranked, 'Apartment', n=2)[0] == 17_500
    assert mc.vat_flags_for(None, {'Apartment': ranked}) == {}


def test_the_basis_is_per_product(mc):
    c = comp('Mixed', 10_000, rate=10_000, rates={'Apartment': 10_000, 'Shophouse': 20_000})
    mc.MASTER_COMPARABLES[:] = [c]
    ranked = mc.nearest_comparables(10_000, n=1)
    vat = _vat(mc, **{'Mixed:Shophouse': 'excl', 'Mixed:Apartment': 'incl'})
    assert mc.derive_product_rate(ranked, 'Apartment', n=1, vat=vat)[0] == 10_000
    assert mc.derive_product_rate(ranked, 'Shophouse', n=1, vat=vat)[0] == 22_000


def test_the_vat_table_loads_and_rejects_bad_rows(mc, tmp_path):
    head = 'project_key,product,basis,source_text,checked_on\n'
    good = tmp_path / 'ok.csv'
    good.write_text(head + 'Tower A,Apartment,excl,"text says chua VAT",2026-10-18\n', encoding='utf-8')
    assert mc.load_vat_basis(str(good)) == {('tower a', 'Apartment'): 'excl'}
    assert mc.load_vat_basis(str(tmp_path / 'missing.csv')) == {}
    for row, message in (('Tower A,Apartment,gross,"x",2026-10-18', 'must be incl or excl'),
                         ('Tower A,Apartment,excl,,2026-10-18', 'source_text is blank'),
                         (',Apartment,excl,"x",2026-10-18', 'required')):
        bad = tmp_path / 'bad.csv'
        bad.write_text(head + row + '\n', encoding='utf-8')
        with pytest.raises(mc.VatBasisError, match=message):
            mc.load_vat_basis(str(bad))


def test_the_real_vat_table_loads_and_every_entry_has_a_source(mc_module):
    table = mc_module.load_vat_basis()
    assert table.get(('rivergate residence', 'Apartment')) == 'excl'
    assert table.get(('green skyline', 'Apartment')) == 'incl'
