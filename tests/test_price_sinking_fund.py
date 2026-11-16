"""TEST DATA only: invented reference values. Change add-sinking-fund, task 2.5: real_budget_ranges.price_sf (median x
NFA, the lift count missing, a code under 10 projects, a warranty over the full year and one ending mid-year, no
warranty, carry-forward with its fallback, an excluded code)."""
import pytest

import real_budget_ranges as rbr


def ref(code, values, basis=rbr.BASIS_FEE_NFA, name_key=''):
    return [{'project_id': f'P{i:03d}', 'name_key': name_key if i == 0 else '', 'nfa_m2': 10_000 + i, 'budget_year': 2026,
             'code': code, 'basis': basis, 'value_unit_month_2027': v, 'flag': ''} for i, v in enumerate(values)]


ROWS = (ref('ERE2', [10.0] * 5 + [20.0] * 6)                            # 11 projects, median 20
        + ref('ERE1', [5.0] * 12)                                       # warranty-list code
        + ref('ERLM1', [100_000.0] * 10, basis=rbr.BASIS_LIFT)
        + ref('ERF3.2', [7.0] * 4))                                     # under 10 projects
CODES = ('ERE1', 'ERE2', 'ERLM1', 'ERF3.2', 'ERM')
CPI = {2026: rbr.CpiYear(2026, 0.04, 'x', 'x'), 2027: rbr.CpiYear(2027, 0.05, 'x', 'x')}


def price(**kw):
    args = dict(nfa=50_000, lifts=None, warranty_months=0, budget_year=2027)
    args.update(kw)
    return rbr.price_sf(CODES, ROWS, **args)


def test_median_times_nfa_with_remark():
    r = price()['ERE2']
    assert r.status == rbr.SF_STATUS_PRICED and r.n == 11 and r.median == 20.0
    assert r.figure == 20 * 50_000 * 12 and r.even
    assert '11 dự án' in r.remark and 'P25–P75' in r.remark and '50,000 m² NFA' in r.remark


def test_vat_factors_by_month():
    factors = [1.08] * 6 + [1.10] * 6
    r = price(vat_factors=factors)['ERE2']
    assert r.months[0] == round(1_000_000 * 1.08) and r.months[11] == round(1_000_000 * 1.10) and not r.even


def test_lift_count_missing_and_present():
    assert price()['ERLM1'].status == rbr.SF_STATUS_PM and price()['ERLM1'].reason == rbr.SF_REASON_NO_LIFTS
    r = price(lifts=6)['ERLM1']
    assert r.status == rbr.SF_STATUS_PRICED and r.figure == 100_000 * 6 * 12 and 'thang máy' in r.remark


def test_code_under_ten_projects():
    r = price()['ERF3.2']
    assert r.status == rbr.SF_STATUS_PM and r.reason == rbr.SF_REASON_TOO_FEW and r.figure == 0


def test_warranty_full_year():
    res = price(warranty_months=24)
    assert res['ERE2'].status == rbr.SF_STATUS_WARRANTY and res['ERE2'].figure == 0
    assert 'trong thời gian bảo hành (24 tháng)' in res['ERE2'].remark
    assert res['ERE1'].status == rbr.SF_STATUS_PRICED and res['ERE1'].figure == 5 * 50_000 * 12
    # a rare code inside a full-year warranty is 0, not a PM line
    assert res['ERF3.2'].status == rbr.SF_STATUS_WARRANTY


def test_warranty_ends_mid_year():
    r = price(warranty_months=6)['ERE2']
    assert r.status == rbr.SF_STATUS_PRICED and r.months[:6] == [0] * 6 and r.months[6:] == [1_000_000] * 6
    assert '6 tháng đầu' in r.remark and not r.even


def test_no_warranty_full_amount():
    assert price(warranty_months=0)['ERE2'].figure == 12_000_000


def test_carry_forward_and_fallback():
    prior = {'ERE2': (24_000_000, 2026, 'sheet 3 của file đã duyệt')}
    res = price(prior=prior, cpi=CPI, warranty_months=24)
    r = res['ERE2']
    assert r.status == rbr.SF_STATUS_CARRY and r.figure == pytest.approx(24_000_000 * 1.05, abs=12)
    assert 'năm 2026 × CPI' in r.remark
    # no prior: the median, and the warranty does not apply in a review
    assert res['ERE1'].status == rbr.SF_STATUS_PRICED and res['ERE1'].figure == 5 * 50_000 * 12
    # neither: PM line
    assert res['ERF3.2'].status == rbr.SF_STATUS_PM


def test_excluded_code():
    r = price(excluded={'ERM': rbr.SF_OTHER_FUND_PRICED, 'ERE2': rbr.SF_OTHER_FUND_PM})
    assert r['ERM'].status == rbr.SF_STATUS_OTHER_FUND and r['ERM'].figure == 0
    assert r['ERE2'].status == rbr.SF_STATUS_OTHER_FUND and rbr.SF_OTHER_FUND_PM in r['ERE2'].remark


def test_review_self_exclusion_by_name_key():
    rows = ref('ERE2', [20.0] * 10, name_key=rbr.name_key('Invented Self'))
    r = rbr.price_sf(('ERE2',), rows, nfa=1, lifts=None, warranty_months=0, self_name='Invented Self', prior={})
    assert r['ERE2'].n == 9 and r['ERE2'].status == rbr.SF_STATUS_PM


def test_no_values_file():
    r = rbr.price_sf(('ERE2',), None, nfa=50_000, lifts=None)
    assert r['ERE2'].status == rbr.SF_STATUS_PM and r['ERE2'].reason == rbr.SF_REASON_NO_DATA
