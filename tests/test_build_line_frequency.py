"""The default-frequency table built from the real budgets' frequency column (change
default-frequency-from-real-budgets, spec line-frequency, task 1.5). Invented raw read (TEST DATA): file ids and
codes only, no project, no workbook opened except the 2027 template for the form's code list."""
import os

import pytest

import build_line_frequency as blf
import line_frequency as lf

TEMPLATE = blf.TEMPLATE


def _line(fid, code, freq, fund='MF', amount=1000.0, kind='budget'):
    return dict(file_id=fid, budget_year='2027', fund=fund, sheet='Ngân sách', sheet_kind=kind, row='10', code=code,
                amount_year=str(amount), is_blank='0', freq_col='C', freq_header='Frequency', freq_raw=freq,
                colC_raw=freq)


def _files(code, freqs, fund='MF'):
    """One line per file id, f1.., each with the given frequency."""
    return [_line(f'{code}-f{i}', code, f, fund) for i, f in enumerate(freqs, 1)]


def test_one_vote_per_file_the_most_common_frequency():
    lines = [_line('a', 'ESC4', 'Yearly'), _line('a', 'ESC4', 'Yearly'), _line('a', 'ESC4', 'Monthly'),
             _line('b', 'ESC4', 'Monthly')]
    assert blf.votes(lines)['ESC4'] == {'Yearly': 1, 'Monthly': 1}


def test_a_tie_votes_for_nothing_and_schedule_zero_lines_and_report_sheets_are_left_out():
    lines = [_line('a', 'ESC4', 'Yearly'), _line('a', 'ESC4', 'Monthly'),          # tie
             _line('b', 'ESC4', 'Schedule'),                                         # not counted
             _line('c', 'ESC4', 'Yearly', amount=0),                                 # zero line
             _line('d', 'ESC4', 'Yearly', kind='report'),                            # report sheet
             _line('e', 'ESC4', 'half a year')]                                      # normalised
    assert blf.votes(lines)['ESC4'] == {blf.TIE: 1, 'Half a Year': 1}


def test_the_common_area_fund_does_not_vote_for_the_management_fund():
    lines = _files('ESC5', ['Yearly'] * 6, fund='CA')
    assert 'ESC5' not in blf.votes(lines, 'MF')
    assert blf.votes(lines, 'CA')['ESC5'] == {'Yearly': 6}


@pytest.mark.parametrize('freqs, expected', [
    (['Yearly'] * 3 + ['Monthly'] * 2, 'Yearly'),           # 5 files, 3 of 5
    (['Yearly'] * 4, None),                                 # fewer than 5 files
    (['Yearly'] * 3 + ['Monthly'] * 3, None),               # half is not more than half
    (['Yearly'] * 2 + ['Half a Year'] * 2 + ['Monthly'], None),
    (['Monthly'] * 6, None),
])
def test_threshold(freqs, expected):
    assert blf.winner(blf.votes(_files('ESC4', freqs))['ESC4']) == expected


def test_count_text_has_counts_only():
    counter = blf.votes(_files('ESC5', ['Yearly'] * 22 + ['Monthly'] * 16))['ESC5']
    counter[blf.TIE] += 2
    assert blf.count_text(counter) == 'Yearly 22 of 40 MF files (16 Monthly, 2 tie)'


def test_build_lists_the_winners_keeps_the_costing_codes_and_drops_off_form_codes():
    lines = (_files('ESC5', ['Yearly'] * 4 + ['Monthly'] * 2)
             + _files('ESA1', ['Yearly'] * 5 + ['Monthly'] * 3)         # not on the 2027 form
             + _files('RO2a', ['Monthly'] * 22)                        # template Half a Year, real Monthly
             + _files('ESM2', ['Monthly'] * 15 + ['Yearly'] * 7))      # costing keeps Half a Year
    rows, report = blf.build(lines, TEMPLATE)
    table = {r['code']: r for r in rows}
    assert set(table) == {'ESC5', 'ESC12', 'ESM2', 'ESM5', 'ESM25'}
    assert (table['ESC5']['frequency'], table['ESC5']['times'], table['ESC5']['first_month']) == ('Yearly', 1, 1)
    assert table['ESC5']['source'] == 'real budgets: Yearly 4 of 6 MF files (2 Monthly)'
    assert table['ESM2']['frequency'] == 'Half a Year' and 'real budgets: Monthly 15 of 22 MF files' in table['ESM2']['source']
    assert blf.KEEP_NOTE in table['ESM2']['note']
    assert table['ESC12']['source'].endswith('real budgets: no MF file carries the code')
    assert any('not on the 2027 form: ESA1' in r for r in report)
    assert any(r.endswith(': RO2a') and 'not used' in r for r in report)


def test_the_written_table_is_read_back(tmp_path):
    rows, _ = blf.build(_files('ESC5', ['Yearly'] * 5), TEMPLATE)
    path = str(tmp_path / 'Ref_LineFrequency.csv')
    blf.write_table(rows, path)
    table = lf.load_table(path)
    assert table['ESC5'].months == [1] and table['ESM25'].months == [1, 4, 7, 10]


def test_leak_check_finds_a_project_name(tmp_path):
    names = tmp_path / 'names.txt'
    names.write_text('(1) ZZ Invented Tower - 2027 budget\n', encoding='utf-8')
    rows = [dict(code='ESC5', source='real budgets: Yearly 4 of 6 MF files', note='ZZ Invented Tower')]
    assert blf.leak_check(rows, str(names)) == ['zz invented tower']
    rows[0]['note'] = ''
    assert blf.leak_check(rows, str(names)) == []
    assert blf.leak_check(rows, str(tmp_path / 'missing.txt')) is None


def test_the_committed_table_has_no_store_file_id():
    with open(lf.TABLE_PATH, encoding='utf-8-sig') as fh:
        text = fh.read()
    assert 'file_id' not in text and not any(len(w) == 12 and all(c in '0123456789abcdef' for c in w)
                                             for w in text.replace(',', ' ').split())
    assert os.path.basename(lf.TABLE_PATH) == 'Ref_LineFrequency.csv'
