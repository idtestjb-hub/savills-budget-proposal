"""verification.checks.sinking_fund_expected (change add-sinking-fund, task 8.1): the rules recomputed apart from
price_sf. TEST DATA: invented reference rows."""
import statistics

import real_budget_ranges as rbr
from verification import checks


def _rows(code, n, base=10.0, basis='fee_nfa'):
    return [dict(project_id=f'P{i:03d}', name_key=f'k{i}', nfa_m2=10_000.0 + i, budget_year=2026, code=code,
                 basis=basis, value_unit_month_2027=base + i, flag='') for i in range(n)]


ROWS = (_rows('ERA1', 12) + _rows('ERE2', 12) + _rows('ERX9', 9) + _rows('ESA2', 9)
        + _rows('ERLM1', 11, 900_000.0, 'lift'))
F = [1.08] * 6 + [1.10] * 6


def test_new_project_median_warranty_and_pm():
    project = dict(total_nfa=40_000, total_lifts=None, warranty_months=24, name='ZZ TEST')
    out = checks.sinking_fund_expected(project, {}, False, ROWS, {'ERM'},
                                       ['ERA1', 'ERE2', 'ERX9', 'ESA2', 'ERLM1', 'ERM'], F, 2027, None)
    m = statistics.median([10.0 + i for i in range(12)]) * 40_000
    assert out['ERA1'] == (rbr.SF_STATUS_PRICED, [round(m * f) for f in F])        # on the warranty list: priced
    assert out['ERE2'] == (rbr.SF_STATUS_WARRANTY, [0] * 12)                         # 24 months: whole year 0
    assert out['ERX9'] == (rbr.SF_STATUS_WARRANTY, [0] * 12)                         # 0 in warranty, even under 10
    assert out['ESA2'] == (rbr.SF_STATUS_PM, None)                                   # on the list, 9 projects
    assert out['ERLM1'] == (rbr.SF_STATUS_PM, None)                                  # no lift count
    assert out['ERM'] == (rbr.SF_STATUS_OTHER_FUND, [0] * 12)


def test_partial_warranty_zeroes_the_first_months_only():
    project = dict(total_nfa=40_000, total_lifts=6, warranty_months=5)
    out = checks.sinking_fund_expected(project, {}, False, ROWS, set(), ['ERE2', 'ERLM1'], [1.0] * 12, 2027, None)
    m = statistics.median([10.0 + i for i in range(12)]) * 40_000
    assert out['ERE2'][1] == [0] * 5 + [round(m)] * 7
    lift = statistics.median([900_000.0 + i for i in range(11)]) * 6
    assert out['ERLM1'] == (rbr.SF_STATUS_PRICED, [round(lift)] * 12)


def test_review_carries_prior_times_cpi_and_ignores_warranty():
    project = dict(total_nfa=40_000, warranty_months=24, existing=object())
    cpi = rbr.load_cpi()
    prior = {'ERE2': (120_000_000.0, 2025, 'TEST')}
    out = checks.sinking_fund_expected(project, prior, True, ROWS, set(), ['ERE2', 'ERA1'], [1.0] * 12, 2027, cpi)
    monthly = 120_000_000.0 * rbr.cpi_factor(2025, cpi, target=2027) / 12
    assert out['ERE2'] == (rbr.SF_STATUS_CARRY, [round(monthly)] * 12)
    assert out['ERA1'][0] == rbr.SF_STATUS_PRICED and all(out['ERA1'][1])            # no warranty in a Review


def test_no_reference_file_leaves_every_line_for_the_pm():
    out = checks.sinking_fund_expected(dict(total_nfa=1, warranty_months=24), {}, False, None, set(), ['ERE2'],
                                       [1.0] * 12, 2027, None)
    assert out['ERE2'] == (rbr.SF_STATUS_PM, None)
