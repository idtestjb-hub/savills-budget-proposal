"""TEST DATA only: invented lines and names. Change add-sinking-fund, task 1.5: the sinking-fund read rules of
build_real_budget_ranges.py (H vs the read column, placeholder sheet, other-year sheet, A/B sum, VAT, lift basis,
name refusal) and an end-to-end build on an invented mini-store."""
import csv
import sqlite3

import pytest

import build_real_budget_ranges as b
import real_budget_ranges as rbr


def line(code, sheet='3', price_total=None, amount_year=None, value_col='AF', sy=2026, vat_rule='already_excl',
         vat_factor=None, months=12):
    return dict(code=code, sheet=sheet, price_total=price_total, amount_year=amount_year, value_col=value_col, sy=sy,
                vat_rule=vat_rule, vat_factor=vat_factor, months_in_period=months)


def test_h_wins_over_read_column():
    codes, notes = b.sf_codes_of_file([line('ERE2', price_total=1_200_000, amount_year=999)], 2026, 12)
    assert codes == {'ERE2': pytest.approx(100_000)} and notes == []


def test_prior_year_read_column_without_h_gives_nothing():
    lines = [line('ERE2', price_total=None, amount_year=1_200_000, value_col='AB'),
             line('ERG2', price_total=None, amount_year=2_400_000, value_col='AF')]
    codes, _ = b.sf_codes_of_file(lines, 2026, 12)
    assert codes == {'ERG2': pytest.approx(200_000)}


def test_placeholder_sheet_left_out():
    lines = [line(c, price_total=5_000_000) for c in ('ERE2', 'ERG2', 'ERT2', 'ERB2', 'ERA2')]
    codes, notes = b.sf_codes_of_file(lines, 2026, 12)
    assert codes == {} and b.SF_PLACEHOLDER in notes
    # four equal lines are not enough to call it a placeholder
    codes, notes = b.sf_codes_of_file(lines[:4], 2026, 12)
    assert len(codes) == 4 and b.SF_PLACEHOLDER not in notes


def test_other_year_sheet_dropped_and_blocks_summed():
    lines = [line('ERE2', sheet='3A', price_total=1_200_000), line('ERE2', sheet='3B', price_total=2_400_000),
             line('ERE2', sheet='3_old', price_total=99_000_000, sy=2025)]
    codes, notes = b.sf_codes_of_file(lines, 2026, 12)
    assert codes == {'ERE2': pytest.approx(300_000)} and notes == [b.SF_OTHER_YEAR]


def test_vat_out_at_line_factor():
    codes, _ = b.sf_codes_of_file([line('ERE2', price_total=1_296_000, vat_rule='converted', vat_factor=1.08)], 2026, 12)
    assert codes['ERE2'] == pytest.approx(100_000)


def _chosen(fid, name, nfa=10_000, year=2026, flags=()):
    return dict(file_id=fid, project_name=name, nfa=nfa, budget_year_v2=year, months_in_period=12, flags=list(flags))


def test_lift_basis_and_missing_lifts():
    cpi = {2027: rbr.CpiYear(2027, 0.05, 'stand-in', 'x')}
    chosen = [_chosen('f1', 'Invented Alpha'), _chosen('f2', 'Invented Beta')]
    sf = {'f1': [line('ERLM1', price_total=12_000_000), line('ERE2', price_total=1_200_000)],
          'f2': [line('ERLM1', price_total=24_000_000)]}
    rows, counts = b.build_sf_rows(chosen, {'f1': 'P001', 'f2': 'P002'}, sf, cpi, {'f1': 4})
    by = {(r['project_id'], r['code']): r for r in rows}
    assert by[('P001', 'ERLM1')]['basis'] == rbr.BASIS_LIFT
    assert by[('P001', 'ERLM1')]['value_unit_month'] == pytest.approx(250_000)          # 1,000,000 / 4 lifts
    assert by[('P001', 'ERLM1')]['value_unit_month_2027'] == pytest.approx(262_500)
    assert by[('P001', 'ERE2')]['basis'] == rbr.BASIS_FEE_NFA
    assert by[('P001', 'ERE2')]['value_unit_month'] == pytest.approx(10)                 # 100,000 / 10,000 m2
    assert ('P002', 'ERLM1') not in by and counts['no_lifts'] == 1
    assert by[('P001', 'ERE2')]['name_key'] and by[('P001', 'ERE2')]['nfa_m2'] == 10_000


def test_master_lifts_one_row_only(tmp_path):
    master = tmp_path / 'master.csv'
    with open(master, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Name', 'ElevatorCount'])
        w.writerows([['Invented Alpha', '6'], ['Invented Beta', '3'], ['Invented Beta', '4'], ['Invented Gamma', '0']])
    chosen = [_chosen('f1', 'INVENTED ALPHA'), _chosen('f2', 'Invented Beta'), _chosen('f3', 'Invented Gamma')]
    assert b.master_lifts(str(master), chosen) == {'f1': 6.0}


def test_name_refusal_on_sf_rows():
    rows = [{'project_id': 'P001', 'name_key': '', 'nfa_m2': 10_000, 'budget_year': 2026, 'code': 'ERE2',
             'basis': 'fee_nfa', 'value_unit_month': 1, 'cpi_factor': 1, 'value_unit_month_2027': 1,
             'flag': 'see Invented Alpha'}]
    with pytest.raises(b.NameWouldLeak):
        b.name_scan(rows, [], {'Invented Alpha'}, columns=rbr.SF_VALUE_COLUMNS)


def test_store_without_sheet_catalog_gives_nothing(tmp_path):
    db = tmp_path / 's.sqlite'
    sqlite3.connect(db).close()
    assert b.read_sf_lines(str(db), ['f1']) == {}
