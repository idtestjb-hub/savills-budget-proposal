"""Unit tests for verification/operating_project.check_operating and compare_existing_stable, the pure
checks behind verify.py section 9 (change use-operating-project-actuals, tasks 7.2 and 7.3).

Built on invented values in memory: no workbook, no Excel. A clean set passes; each of the four
breakages task 7.3 names fails, and its message carries both figures in VND.
This file sets up its own import path, so it runs with or without a conftest.py beside it.
"""
import copy
import os
import sys

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from verification import operating_project as op      # noqa: E402

NFA = {p: 0.0 for p in op.RM_PRODUCT_ROWS}
NFA.update({'Apartment': 10_000.0, 'Shophouse': 500.0})
EXPECTED = dict(nfa=NFA, rates={'Apartment': (15_000.0, 'excl. VAT')}, stable=True,
                parking={'car': 20_000_000.0, 'moto': 30_000_000.0},
                cob={'Apartment': {'water': 100_000_000.0, 'electricity': 200_000_000.0},
                     'Shophouse': {'water': 0.0, 'electricity': 10_000_000.0}})
STANDARD = {'Shophouse': 120_000_000.0}


def _line(row, monthly):
    return dict(row=row, g=monthly * 12, months=[monthly] * 12, remark='')


def _clean():
    rm = {p: _line(r, 0.0) for p, r in op.RM_PRODUCT_ROWS.items()}
    rm['Apartment'] = _line(14, 15_000.0 * 10_000)
    rm['Shophouse'] = _line(20, 10_000_000.0)
    fund = {'RM.0A': _line(23, 0.0), 'RP1': _line(26, 30_000_000.0), 'RP2': _line(27, 20_000_000.0),
            'RO3.A': _line(40, 100_000_000.0), 'RO3.S': _line(45, 0.0), 'RO4.A': _line(48, 200_000_000.0),
            'RO4.S': _line(53, 10_000_000.0), 'EEW.A': _line(229, 100_000_000.0),
            'EEE.A': _line(239, 210_000_000.0)}
    return dict(rm=rm, fund=fund, summary_k={}, fills={k: [1.0] * 12 for k in ('resident', 'car', 'moto')},
                mgmt_fee={'Apartment': 150_000_000.0, 'Shophouse': 10_000_000.0},
                parking={'car': 20_000_000.0, 'moto': 30_000_000.0})


def _messages(out):
    ok, _rows, diffs, _notes = op.check_operating(EXPECTED, out, STANDARD)
    return ok, ' || '.join(f'{label}: {msg}' for label, msg in diffs)


def test_clean_outputs_pass():
    ok, text = _messages(_clean())
    assert ok, text


def test_analysis_ignoring_the_entered_rate_fails_with_both_values():
    out = _clean()
    out['mgmt_fee']['Apartment'] = 160_000_000.0
    ok, text = _messages(out)
    assert not ok
    assert '1,800,000,000' in text and '1,920,000,000' in text


def test_non_zero_developer_top_up_fails():
    out = _clean()
    out['fund']['RM.0A']['g'] = 5_000_000.0
    ok, text = _messages(out)
    assert not ok and 'RM.0A' in text and '5,000,000' in text


def test_rp2_not_entered_times_twelve_fails():
    out = _clean()
    out['fund']['RP2']['months'][-1] = 0.0
    out['fund']['RP2']['g'] = 220_000_000.0
    ok, text = _messages(out)
    assert not ok and '240,000,000' in text and '220,000,000' in text


def test_unbalanced_pair_names_expense_and_revenue_codes():
    out = _clean()
    out['fund']['EEE.A']['g'] = 2_400_000_000.0
    ok, text = _messages(out)
    assert not ok
    assert 'EEE.A' in text and 'RO4.A + RO4.S' in text and '2,520,000,000' in text and '2,400,000,000' in text


def test_ramped_occupancy_fails_when_stable():
    out = _clean()
    out['fills']['resident'][0] = 0.4
    ok, text = _messages(out)
    assert not ok and 'resident' in text


def test_existing_stable_comparison_flags_a_moved_utility_line():
    plain = dict(fund={'EEW.C': _line(230, 5_000_000.0), 'EEE.C': _line(240, 9_000_000.0)},
                 summary_k={38: 'nước', 39: 'điện'})
    same = copy.deepcopy(plain)
    assert op.compare_existing_stable(plain, same)[0]
    moved = copy.deepcopy(plain)
    moved['fund']['EEE.C']['g'] = 1.0
    ok, _rows, diffs, _notes = op.compare_existing_stable(plain, moved)
    assert not ok and diffs[0][0] == 'EEE.C g'
