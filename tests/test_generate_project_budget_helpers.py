"""Unit tests for the pure helper functions of generate_project_budget.py.

Covered: the input resolvers (_resolve_operating_years, _resolve_capex_drop_year,
_resolve_pool_count, _resolve_coords), the Roster Setup ratio fallback (_ratio_or_default,
_ratio_note), staffing (_staff_on_duty, _portfolio_headcount, _pool_lifeguards_per_shift,
_eff_headcount), the proposal-benchmark wording (_benchmark_fee_clause) and _append_vat.

Not covered: anything that opens or writes a workbook (read_input, build_budget, the fill_*
sheet writers), the remark composers, and generate_project_output (it needs its CSV at import).

Invented data only: fictional projects, no reads of input/, data/, reports/ or output/.
Expected values come from the documented rules (docs/05, 15, 16, 17; openspec specs
proposal-benchmark, capex-reserve-rate, portfolio-derived-staffing-defaults), not from running
the code. A test whose rule is written only in a code comment says so above it.
"""
import math

import pytest

import generate_project_budget as g


class Cell:
    """Stub for an openpyxl cell: only .value is read."""

    def __init__(self, value):
        self.value = value


@pytest.fixture(autouse=True)
def reset_globals(monkeypatch):
    """Module globals these helpers read or mutate are restored around every test."""
    monkeypatch.setattr(g, '_POSITION_RATIOS', None)
    g._RATIO_DEFAULTED.clear()
    yield
    g._RATIO_DEFAULTED.clear()


BLANKS = [None, '', '   ']


# ---------------------------------------------------------------- _resolve_operating_years
# Rule: docs/16-intake-form-guide.md ("only accepts 1 today"); blank takes the default of 1.
@pytest.mark.parametrize('raw', BLANKS)
def test_operating_years_blank_means_one(raw):
    assert g._resolve_operating_years(raw) == 1


@pytest.mark.parametrize('raw', [1, 1.0, '1', ' 1 '])
def test_operating_years_one_accepted(raw):
    assert g._resolve_operating_years(raw) == 1


@pytest.mark.parametrize('raw', [2, 3, 10, '2'])
def test_operating_years_above_one_rejected_naming_value(raw):
    with pytest.raises(ValueError) as exc:
        g._resolve_operating_years(raw)
    assert 'Operating Years to Budget' in str(exc.value)
    assert f' is {int(raw)},' in str(exc.value)


@pytest.mark.parametrize('raw', [0, -1, '0'])
def test_operating_years_below_one_rejected_naming_value(raw):
    with pytest.raises(ValueError) as exc:
        g._resolve_operating_years(raw)
    assert f' is {int(raw)}.' in str(exc.value)


@pytest.mark.parametrize('raw', [1.5, 0.5, 'abc', '1.5'])
def test_operating_years_fraction_or_text_rejected_naming_value(raw):
    with pytest.raises(ValueError) as exc:
        g._resolve_operating_years(raw)
    assert repr(raw) in str(exc.value)
    assert 'whole number' in str(exc.value)


# ---------------------------------------------------------------- _resolve_capex_drop_year
# Rule: docs/05-decisions.md "Capex drop-to-reserve year" and capex-reserve-rate spec:
# blank = Year 2 and flagged as a default; 3 or 4 accepted; Year 1 cannot be entered.
@pytest.mark.parametrize('raw', BLANKS)
def test_capex_drop_year_blank_is_default_year_two(raw):
    assert g._resolve_capex_drop_year(raw) == (2, True)


@pytest.mark.parametrize('raw,year', [(2, 2), (3, 3), (4, 4), ('3', 3), (4.0, 4), (' 2 ', 2)])
def test_capex_drop_year_accepted_range_is_not_default(raw, year):
    assert g._resolve_capex_drop_year(raw) == (year, False)


@pytest.mark.parametrize('raw', [1, 5, 0, -3, 99])
def test_capex_drop_year_out_of_range_rejected_naming_value(raw):
    with pytest.raises(ValueError) as exc:
        g._resolve_capex_drop_year(raw)
    msg = str(exc.value)
    assert 'Capex Drop-to-Reserve Year' in msg
    assert f' is {raw}.' in msg


@pytest.mark.parametrize('raw', [2.5, 'abc', '3.5'])
def test_capex_drop_year_fraction_or_text_rejected_naming_value(raw):
    with pytest.raises(ValueError) as exc:
        g._resolve_capex_drop_year(raw)
    assert repr(raw) in str(exc.value)


# ---------------------------------------------------------------- _resolve_pool_count
# Rule: docs/16 section 6 and the function docstring: a pool with no stated count is one pool.
def test_pool_count_no_pool_is_zero():
    assert g._resolve_pool_count(None, False) == (0, False)
    assert g._resolve_pool_count('', False) == (0, False)
    assert g._resolve_pool_count(0, False) == (0, False)


@pytest.mark.parametrize('raw', [None, '', '  ', 0, '0'])
def test_pool_count_pool_without_count_assumes_one(raw):
    assert g._resolve_pool_count(raw, True) == (1, False)


@pytest.mark.parametrize('raw,n', [(1, 1), (3, 3), ('2', 2), (2.0, 2)])
def test_pool_count_stated_count_used(raw, n):
    assert g._resolve_pool_count(raw, True) == (n, True)


# Rule: docs/16 section 8 ("Number of Pools contradicts Has Swimming Pool?").
def test_pool_count_contradiction_rejected_naming_both_fields():
    with pytest.raises(ValueError) as exc:
        g._resolve_pool_count(2, False)
    msg = str(exc.value)
    assert 'Has Swimming Pool?' in msg and 'Number of Pools' in msg and ' is 2.' in msg


@pytest.mark.parametrize('raw', [-1, -5])
@pytest.mark.parametrize('has_pool', [True, False])
def test_pool_count_negative_rejected_naming_value(raw, has_pool):
    with pytest.raises(ValueError) as exc:
        g._resolve_pool_count(raw, has_pool)
    assert f'is {raw}.' in str(exc.value)


@pytest.mark.parametrize('raw', [1.5, 'two'])
def test_pool_count_fraction_or_text_rejected_naming_value(raw):
    with pytest.raises(ValueError) as exc:
        g._resolve_pool_count(raw, True)
    assert repr(raw) in str(exc.value)


# ---------------------------------------------------------------- _resolve_coords
# Rule source: function docstring (a half-filled pair means no coordinates).
def test_coords_full_pair_returned_as_floats():
    assert g._resolve_coords(10.5, 106.25) == (10.5, 106.25)
    assert g._resolve_coords('10.5', '106.25') == (10.5, 106.25)


@pytest.mark.parametrize('lat,lon', [
    (10.5, None), (None, 106.25), (10.5, ''), ('', 106.25),
    (10.5, 'n/a'), ('n/a', 106.25),
])
def test_coords_half_filled_pair_is_no_coordinates(lat, lon):
    assert g._resolve_coords(lat, lon) == (None, None)


@pytest.mark.parametrize('lat,lon', [(None, None), ('', ''), ('x', 'y')])
def test_coords_both_missing_or_unreadable(lat, lon):
    assert g._resolve_coords(lat, lon) == (None, None)


# Rule source: code (0 is not blank). Not settled: whether a literal 0 should count as unfilled.
def test_coords_zero_is_treated_as_a_value_not_blank():
    assert g._resolve_coords(0, 106.25) == (0.0, 106.25)


# ---------------------------------------------------------------- _ratio_or_default / _ratio_note
# Rule: docs/17-huong-dan-file-dau-vao.md: blank or 0 takes the standard (1, 5000, 3000, 2, 2000)
# and the row says "standard assumption".
DEFAULTS = {
    'staff_per_gate': 1,
    'sqm_per_patrol': 5000,
    'sqm_per_cleaner': 3000,
    'towers_per_supervisor': 2,
    'sqm_per_gardener': 2000,
}


@pytest.mark.parametrize('key,default', sorted(DEFAULTS.items()))
@pytest.mark.parametrize('raw', [None, '', 0, 0.0, '0'])
def test_ratio_blank_or_zero_uses_standard_and_notes_it(key, default, raw):
    assert g._ratio_or_default(raw, key) == default
    assert 'standard assumption' in g._ratio_note(key)


@pytest.mark.parametrize('key', sorted(DEFAULTS))
def test_ratio_positive_value_kept_without_note(key):
    assert g._ratio_or_default(7.5, key) == 7.5
    assert g._ratio_or_default('4', key) == 4.0
    assert g._ratio_note(key) == ''


def test_ratio_note_is_per_key():
    g._ratio_or_default(0, 'sqm_per_cleaner')
    g._ratio_or_default(2500, 'sqm_per_gardener')
    assert 'standard assumption' in g._ratio_note('sqm_per_cleaner')
    assert g._ratio_note('sqm_per_gardener') == ''


def test_ratio_later_valid_value_clears_the_fallback_flag():
    g._ratio_or_default(None, 'staff_per_gate')
    g._ratio_or_default(2, 'staff_per_gate')
    assert g._ratio_note('staff_per_gate') == ''


# Not settled: a negative or non-numeric ratio. Pinned: it takes the standard like a blank.
@pytest.mark.parametrize('raw', [-3, 'abc'])
def test_ratio_negative_or_text_falls_back_like_blank(raw):
    assert g._ratio_or_default(raw, 'sqm_per_patrol') == 5000
    assert 'standard assumption' in g._ratio_note('sqm_per_patrol')


# ---------------------------------------------------------------- _eff_headcount
# Rule source: function docstring (7-day coverage needs 7/6 of staff per day, 1 day off in 7).
@pytest.mark.parametrize('per_day,expected', [
    (0, 0), (1, 2), (2, 3), (3, 4), (6, 7), (7, 9), (12, 14),
])
def test_eff_headcount_seven_day_coverage_is_seven_sixths_rounded_up(per_day, expected):
    assert g._eff_headcount({'StaffPerDay': per_day, 'CoverageDays': 7}) == expected
    assert expected == math.ceil(per_day * 7 / 6)


@pytest.mark.parametrize('coverage', [1, 5, 6])
def test_eff_headcount_below_seven_days_is_exact_staff_per_day(coverage):
    assert g._eff_headcount({'StaffPerDay': 5, 'CoverageDays': coverage}) == 5


# ---------------------------------------------------------------- _pool_lifeguards_per_shift
# Rule: docs/15-pool-staffing-regulation.md and docs/16 section 6:
# ceil(water surface / 200) per shift; pool count is not a driver; no area = 1 attendant.
def test_lifeguards_no_pool_is_zero():
    n, basis = g._pool_lifeguards_per_shift({'has_pool': False, 'pool_area': 500}, {})
    assert n == 0
    assert 'No swimming pool' in basis


@pytest.mark.parametrize('area,expected', [
    (180, 1),    # three small pools totalling 180 m2 clear the test with one (docs/15)
    (199, 1),
    (200, 1),    # exactly one lifeguard's worth
    (201, 2),    # just over the threshold needs a second
    (400, 2),    # one 400 m2 pool needs two (docs/15)
    (401, 3),
])
def test_lifeguards_per_shift_is_area_over_200_rounded_up(area, expected):
    n, basis = g._pool_lifeguards_per_shift({'has_pool': True, 'pool_area': area}, {})
    assert n == pytest.approx(area / 200)
    assert math.ceil(n) == expected
    assert f'{area:,.0f} m2' in basis


def test_lifeguards_not_scaled_by_pool_count():
    one = g._pool_lifeguards_per_shift({'has_pool': True, 'pool_area': 180, 'pool_count': 1}, {})
    three = g._pool_lifeguards_per_shift({'has_pool': True, 'pool_area': 180, 'pool_count': 3}, {})
    assert one[0] == three[0]


def test_lifeguards_basis_carries_the_scope_caveat():
    _, basis = g._pool_lifeguards_per_shift({'has_pool': True, 'pool_area': 400}, {})
    assert 'Thong tu 03/2018/TT-BVHTTDL' in basis
    assert 'NOT an established legal obligation' in basis


@pytest.mark.parametrize('area', [None, 0, '', 'abc'])
def test_lifeguards_missing_area_falls_back_to_one_attendant_and_says_so(area):
    n, basis = g._pool_lifeguards_per_shift({'has_pool': True, 'pool_area': area}, {})
    assert n == 1
    assert 'Pool Area (m2) not supplied' in basis


# Not settled: a negative area. Pinned: treated like a missing area.
def test_lifeguards_negative_area_treated_as_missing():
    n, _ = g._pool_lifeguards_per_shift({'has_pool': True, 'pool_area': -50}, {})
    assert n == 1


def test_lifeguards_numeric_text_area_is_read():
    n, _ = g._pool_lifeguards_per_shift({'has_pool': True, 'pool_area': '600'}, {})
    assert n == pytest.approx(3.0)


# ---------------------------------------------------------------- _portfolio_headcount
# Rule: openspec portfolio-derived-staffing-defaults: ratio x NFA, split across shift rows,
# role measured on fewer than the floor (10) properties is not estimated, no NFA is not estimated,
# basis states median, sample size and "not a Savills standard".
def stats(n=12, median=0.2, p25=0.1, p75=0.3):
    return {'n': n, 'median': median, 'p25': p25, 'p75': p75}


TECH_ROWS = ['Technician (Morning)', 'Technician (Afternoon)', 'Technician (Night)']


def test_portfolio_headcount_is_median_per_1000_m2_times_nfa(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Property Manager': stats(median=0.04)})
    # 0.04 per 1,000 m2 x 50,000 m2 = 2 for the building; single-row role takes all of it
    value, basis = g._portfolio_headcount('Property Manager', 'Property Manager',
                                          {'total_nfa': 50000})
    assert value == 2
    assert 'split across' not in basis


def test_portfolio_headcount_split_across_shift_rows_sums_to_total(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Technician': stats(median=0.2)})
    # 0.2 x 50 = 10 for the building, spread over 3 rows, not 10 on each
    values = [g._portfolio_headcount('Technician', r, {'total_nfa': 50000})[0] for r in TECH_ROWS]
    assert sum(values) == 10
    assert max(values) - min(values) <= 1
    assert values == [4, 3, 3]          # the remainder goes to the earliest rows


def test_portfolio_headcount_even_split(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Technician': stats(median=0.18)})
    # 0.18 x 50 = 9 -> 3 per row
    values = [g._portfolio_headcount('Technician', r, {'total_nfa': 50000})[0] for r in TECH_ROWS]
    assert values == [3, 3, 3]


# Rule source: code (max(1, ...)). Not settled: a building total never rounds to zero.
def test_portfolio_headcount_building_total_never_below_one(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Technician': stats(median=0.01)})
    values = [g._portfolio_headcount('Technician', r, {'total_nfa': 1000})[0] for r in TECH_ROWS]
    assert values == [1, 0, 0]


def test_portfolio_headcount_floor_of_ten_properties(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Cashier': stats(n=9)})
    value, basis = g._portfolio_headcount('Cashier', 'Cashier', {'total_nfa': 50000})
    assert value is None
    assert '9 comparable properties' in basis and 'too few' in basis
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Cashier': stats(n=10)})
    value, _ = g._portfolio_headcount('Cashier', 'Cashier', {'total_nfa': 50000})
    assert value is not None


def test_portfolio_headcount_single_property_wording(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Cashier': stats(n=1)})
    value, basis = g._portfolio_headcount('Cashier', 'Cashier', {'total_nfa': 50000})
    assert value is None
    assert 'only 1 comparable property' in basis


@pytest.mark.parametrize('nfa', [0, None, -100])
def test_portfolio_headcount_no_nfa_is_not_estimated(monkeypatch, nfa):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Cashier': stats()})
    value, basis = g._portfolio_headcount('Cashier', 'Cashier', {'total_nfa': nfa})
    assert value is None
    assert 'No NFA' in basis


def test_portfolio_headcount_missing_nfa_key(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Cashier': stats()})
    value, _ = g._portfolio_headcount('Cashier', 'Cashier', {})
    assert value is None


def test_portfolio_headcount_role_without_ratio(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {})
    value, basis = g._portfolio_headcount('Cashier', 'Cashier', {'total_nfa': 50000})
    assert value is None
    assert 'No derived ratio for Cashier' in basis


def test_portfolio_headcount_basis_discloses_median_sample_and_non_standard(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS',
                        {'Technician': stats(n=14, median=0.2, p25=0.15, p75=0.35)})
    _, basis = g._portfolio_headcount('Technician', TECH_ROWS[0], {'total_nfa': 50000})
    assert '0.2000 per 1,000 m2 NFA' in basis
    assert 'Measured on 14 comparable residential properties' in basis
    assert '0.150-0.350' in basis
    assert 'not a Savills standard or a statutory minimum' in basis
    assert 'split across 3 shift rows' in basis


# ---------------------------------------------------------------- _staff_on_duty
# Rule: portfolio spec "A PM's typed override always wins" and the function docstring.
GATE = 'Security - Main Gate (Morning)'
PROJECT = {'gate_count': 3, 'open_space': 12000, 'towers': 3, 'garden_area': 5000,
           'total_nfa': 50000}
RATIOS = {'staff_per_gate': 1.5, 'sqm_per_patrol': 5000, 'sqm_per_cleaner': 3000,
          'towers_per_supervisor': 2, 'sqm_per_gardener': 2000}
GATE_FN = g.RATIO_DRIVEN_STAFFING[GATE]      # 3 gates x 1.5 = 4.5 -> 5


def test_staff_typed_override_beats_ratio_suggestion():
    n, basis = g._staff_on_duty(GATE, 8, Cell(8), GATE_FN, PROJECT, RATIOS, 12)
    assert n == 8
    assert 'PM override' in basis


def test_staff_override_with_no_formula_cell_object():
    n, basis = g._staff_on_duty(GATE, 8, None, GATE_FN, PROJECT, RATIOS, 12)
    assert n == 8 and 'PM override' in basis


def test_staff_seeded_formula_is_recomputed_not_trusted_from_cache():
    # cached 99 is stale; the formula is still there, so the ratio decides (4.5 rounded up = 5)
    n, basis = g._staff_on_duty(GATE, 99, Cell('=ROUNDUP(B2*B3,0)'), GATE_FN, PROJECT, RATIOS, 12)
    assert n == 5
    assert 'rounded up' in basis
    assert 'blank or zero' not in basis


@pytest.mark.parametrize('cached', [None, '', '  ', 0, 0.0])
def test_staff_blank_or_zero_falls_back_to_ratio_and_says_so(cached):
    # documented: a zero left in place is not a way to force a ratio-covered role to zero
    n, basis = g._staff_on_duty(GATE, cached, Cell(cached), GATE_FN, PROJECT, RATIOS, 12)
    assert n == 5
    assert 'blank or zero' in basis


# Rule source: code comment only (ratio rows are ROUNDUP formulas in the form).
@pytest.mark.parametrize('pos,expected', [
    ('Security - Patrol / Open Space', 3),    # 12000 / 5000 = 2.4 -> 3
    ('Cleaning - Common Area', 4),            # 12000 / 3000 = 4.0 -> 4, exact stays exact
    ('Cleaning - Supervisor', 2),             # 3 / 2 = 1.5 -> 2
    ('Gardener / Landscape', 3),              # 5000 / 2000 = 2.5 -> 3
])
def test_staff_ratio_rows_round_up(pos, expected):
    n, _ = g._staff_on_duty(pos, None, Cell(None), g.RATIO_DRIVEN_STAFFING[pos],
                            PROJECT, RATIOS, 7)
    assert n == expected


@pytest.mark.parametrize('cached', ['abc', '#REF!'])
def test_staff_non_numeric_value_rejected_naming_row_and_value(cached):
    with pytest.raises(ValueError) as exc:
        g._staff_on_duty(GATE, cached, Cell(None), GATE_FN, PROJECT, RATIOS, 12)
    msg = str(exc.value)
    assert 'row 12' in msg and GATE in msg and repr(cached) in msg


def test_staff_row_without_ratio_uses_typed_value_including_zero():
    assert g._staff_on_duty('CCTV', 3, Cell(3), None, PROJECT, RATIOS, 4) == (
        3, 'PM-entered value (Staffing Demand sheet, not ratio-driven)')
    assert g._staff_on_duty('CCTV', 0, Cell(0), None, PROJECT, RATIOS, 4)[0] == 0


def test_staff_row_without_ratio_blank_is_an_error_naming_row():
    with pytest.raises(ValueError) as exc:
        g._staff_on_duty('CCTV', None, Cell(None), None, PROJECT, RATIOS, 4)
    assert 'row 4' in str(exc.value) and "'CCTV'" in str(exc.value)


def _no_ratio(_project, _ratios):
    raise g._NoPortfolioRatio('Cashier is measured on only 3 comparable properties')


def test_staff_no_usable_portfolio_ratio_keeps_form_value_and_says_why():
    n, basis = g._staff_on_duty('Cashier', 2, Cell('=1+1'), _no_ratio, PROJECT, RATIOS, 9)
    assert n == 2
    assert 'only 3 comparable properties' in basis
    assert 'no portfolio estimate' in basis


def test_staff_no_usable_portfolio_ratio_and_blank_keeps_zero():
    n, _ = g._staff_on_duty('Cashier', None, Cell(None), _no_ratio, PROJECT, RATIOS, 9)
    assert n == 0


def test_staff_portfolio_row_end_to_end(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Technician': stats(median=0.2)})
    fn = g.RATIO_DRIVEN_STAFFING['Technician (Morning)']
    n, basis = g._staff_on_duty('Technician (Morning)', None, Cell(None), fn, PROJECT, RATIOS, 6)
    assert n == 4                                  # 10 for the building over 3 rows -> 4,3,3
    assert 'portfolio median' in basis


def test_staff_portfolio_row_thin_sample_keeps_seed(monkeypatch):
    monkeypatch.setattr(g, '_POSITION_RATIOS', {'Technician': stats(n=5)})
    fn = g.RATIO_DRIVEN_STAFFING['Technician (Morning)']
    n, basis = g._staff_on_duty('Technician (Morning)', 2, Cell('=ROUNDUP(1,0)'), fn,
                                PROJECT, RATIOS, 6)
    assert n == 2 and 'no portfolio estimate' in basis


def test_staff_pool_row_rounds_the_per_shift_figure_up():
    fn = g.RATIO_DRIVEN_STAFFING['Pool Attendant (Morning)']
    project = {'has_pool': True, 'pool_area': 401}
    n, _ = g._staff_on_duty('Pool Attendant (Morning)', None, Cell(None), fn, project, RATIOS, 8)
    assert n == 3                                  # ceil(401 / 200)


# ---------------------------------------------------------------- _benchmark_fee_clause
# Rule: openspec proposal-benchmark ("inside, below or above the range ... by how much in
# percentage terms"; "fewer than two comparables ... narrow base"; no invented rate).
def test_fee_clause_within_range():
    text = g._benchmark_fee_clause(50000, [40000, 60000])
    assert 'within' in text and '40,000-60,000' in text
    assert 'review' not in text


@pytest.mark.parametrize('rate', [40000, 60000])
def test_fee_clause_range_ends_count_as_within(rate):
    # not settled: whether a fee exactly equal to the lowest/highest comparable is "within"
    assert 'within' in g._benchmark_fee_clause(rate, [40000, 60000])


def test_fee_clause_below_range_states_percentage():
    text = g._benchmark_fee_clause(30000, [40000, 60000])
    assert '25% below the lower comparable (40,000)' in text
    assert 'within' not in text


def test_fee_clause_above_range_states_percentage():
    text = g._benchmark_fee_clause(72000, [40000, 60000])
    assert '20% above the higher comparable (60,000)' in text


def test_fee_clause_order_of_comparables_does_not_matter():
    assert (g._benchmark_fee_clause(50000, [60000, 40000])
            == g._benchmark_fee_clause(50000, [40000, 60000]))


@pytest.mark.parametrize('rates', [[], None, [0, None]])
def test_fee_clause_without_verified_rate_cannot_be_benchmarked(rates):
    text = g._benchmark_fee_clause(50000, rates)
    assert 'cannot be benchmarked' in text
    assert '50,000' in text


def test_fee_clause_single_comparable_is_flagged_narrow():
    text = g._benchmark_fee_clause(55000, [50000])
    assert 'narrow base' in text
    assert '10% above' in text and '(50,000)' in text


def test_fee_clause_single_comparable_below():
    assert '20% below' in g._benchmark_fee_clause(40000, [50000])


# Not settled: a comparable with a zero rate is ignored (the spec says blank, not zero).
def test_fee_clause_zero_rate_comparable_is_dropped_leaving_narrow_base():
    text = g._benchmark_fee_clause(55000, [50000, 0])
    assert 'narrow base' in text


# Not settled: the "matches" tolerance for a single comparable (under 0.5 percent).
def test_fee_clause_single_comparable_matches_within_half_percent():
    assert 'matches the one available comparable' in g._benchmark_fee_clause(50100, [50000])


# ---------------------------------------------------------------- _append_vat
# Rule source: code comment above _ACTIVE_VAT_SENTENCE (AI Guideline: an incl-VAT remark carries
# the VAT sentence; empty sentence = exclusive-of-VAT run, nothing appended) and the docstring.
SENTENCE = 'Gia da bao gom VAT, nam ngan sach 2027.'


def test_vat_appended_once_after_a_space(monkeypatch):
    monkeypatch.setattr(g, '_ACTIVE_VAT_SENTENCE', SENTENCE)
    assert g._append_vat('Chi phi bao ve.') == f'Chi phi bao ve. {SENTENCE}'


def test_vat_is_not_appended_twice(monkeypatch):
    monkeypatch.setattr(g, '_ACTIVE_VAT_SENTENCE', SENTENCE)
    once = g._append_vat('Chi phi bao ve.')
    assert g._append_vat(once) == once
    assert once.count(SENTENCE) == 1


def test_vat_exclusive_run_appends_nothing(monkeypatch):
    monkeypatch.setattr(g, '_ACTIVE_VAT_SENTENCE', '')
    assert g._append_vat('Chi phi bao ve.') == 'Chi phi bao ve.'


@pytest.mark.parametrize('remark', ['', None])
def test_vat_empty_remark_stays_empty(monkeypatch, remark):
    monkeypatch.setattr(g, '_ACTIVE_VAT_SENTENCE', SENTENCE)
    assert g._append_vat(remark) == remark


def test_vat_multiline_remark_gets_its_own_line(monkeypatch):
    monkeypatch.setattr(g, '_ACTIVE_VAT_SENTENCE', SENTENCE)
    assert g._append_vat('- bao ve\n- ve sinh') == f'- bao ve\n- ve sinh\n{SENTENCE}'


def test_vat_remark_ending_in_newline_gets_no_extra_separator(monkeypatch):
    monkeypatch.setattr(g, '_ACTIVE_VAT_SENTENCE', SENTENCE)
    assert g._append_vat('- bao ve\n') == f'- bao ve\n{SENTENCE}'


def test_vat_remark_ending_in_space_gets_no_double_space(monkeypatch):
    monkeypatch.setattr(g, '_ACTIVE_VAT_SENTENCE', SENTENCE)
    assert g._append_vat('Chi phi bao ve. ') == f'Chi phi bao ve. {SENTENCE}'
