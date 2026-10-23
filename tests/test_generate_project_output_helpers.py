"""Unit tests for the pure helpers of generate_project_output.py (the analysis workbook writer).

Covered: statutory_payroll_params, a1_extra_formulas, staff_market_categories / in_staff_category,
_plain, _year_fill_path / _stable_prefix, _load_capex_reserve, _capex_reserve_formula /
_capex_reserve_monthly_formula, _fix_fake_formula_strings and _strip_onedrive_zip_artifacts.

Not covered: the build_*_sheet writers (the verification suite runs them end to end).

Invented data only. The module reads Fact_CapexReserve.csv when it is imported, so the `gpo`
fixture points that read at an invented four-project file in a temp folder; nothing under data/,
input/, reports/ or output/ is read or written. Expected values come from the documented rules:
openspec/specs/capex-reserve-rate (drop-year logic, derived rate), the comments above
statutory_payroll_params (2026-27 Region I figures), docs/05-decisions.md and the OneDrive trap in
the Budget Agent rules (a plain-text note that starts with "= " is not a formula; "[trash]/" zip
entries are garbage). A test whose rule is written only in a code comment says so above it.
"""
import builtins
import datetime
import os
import sys
import zipfile

import openpyxl
import pytest

import existing_staffing
import labor_law_params

CAPEX_RESERVE_FILE = 'Fact_CapexReserve.csv'
CAPEX_HEADER = ('ObservationType,Project,Year1Sheet,LaterSheet,LaterMonths,Year1Capex,LaterCapex,'
                'ImpliedRateLiteral,ImpliedRateAnnualised,SourceFile,ExtractedOn\n')
# Three reserve observations and one full-repeat year (which must not enter the rate).
CAPEX_ROWS = [
    'reserve,Savills - Tower Alpha,Y1,Y2,12,1000,100,0.10,0.10,a.xlsx,2026-01-01',
    'reserve,Savills - Tower Beta,Y1,Y2,9,1000,60,0.06,0.08,b.xlsx,2026-01-01',
    'reserve,Savills - Tower Gamma With A Very Long Project Name Indeed,Y1,Y2,12,1000,120,0.12,0.12,c.xlsx,2026-01-01',
    'full_repeat,Savills - Tower Delta,Y1,Y2,12,1000,1000,1.00,1.00,d.xlsx,2026-01-01',
]


def write_capex_csv(path, rows=CAPEX_ROWS):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        f.write(CAPEX_HEADER + '\n'.join(rows) + '\n')


@pytest.fixture(scope='module')
def gpo(tmp_path_factory):
    """generate_project_output, imported against an invented Fact_CapexReserve.csv.

    A module that was already imported (by an earlier test file) is reused; one imported here is
    removed again afterwards so no later test sees the invented rate.
    """
    if 'generate_project_output' in sys.modules:
        yield sys.modules['generate_project_output']
        return
    fake = tmp_path_factory.mktemp('capex') / CAPEX_RESERVE_FILE
    write_capex_csv(fake)
    real_open, real_exists = builtins.open, os.path.exists

    def fake_open(file, *a, **k):
        if isinstance(file, str) and os.path.basename(file) == CAPEX_RESERVE_FILE:
            file = str(fake)
        return real_open(file, *a, **k)

    def fake_exists(p):
        if isinstance(p, str) and os.path.basename(p) == CAPEX_RESERVE_FILE:
            p = str(fake)
        return real_exists(p)

    builtins.open, os.path.exists = fake_open, fake_exists
    try:
        import generate_project_output as module
    finally:
        builtins.open, os.path.exists = real_open, real_exists
    yield module
    sys.modules.pop('generate_project_output', None)


def evaluate(formula, **cells):
    """Value of a simple Excel formula (+ - * / numbers, $B5-style cells, MAX) with the cells given."""
    expr = formula.lstrip('=')
    for name, value in cells.items():
        expr = expr.replace(name, repr(value))
    return eval(expr.replace('MAX(', 'max('), {'max': max})


# ---------------------------------------------------------------- _plain

@pytest.mark.parametrize('value, shown', [(2530000.0, 2530000), (0.0, 0), (5, 5), (0.205, 0.205), (-3.0, -3)])
def test_plain_prints_whole_numbers_without_a_decimal_point(gpo, value, shown):
    result = gpo._plain(value)
    assert result == shown
    assert isinstance(result, int) == float(value).is_integer()


# ---------------------------------------------------------------- statutory_payroll_params

def law_rows(extra=()):
    """The ten required parameters, Region I, 2026 values (the template's own, see the code comment)."""
    def row(name, value, start=datetime.date(2026, 1, 1), end=None, region='', basis='ND 74/2024'):
        return {'parameter': name, 'region': region, 'value': value, 'effective_from': start,
                'effective_to': end, 'legal_basis': basis}
    rows = [
        row('min_wage_region', 5_310_000, region='I'),
        row('insurance_base', 2_530_000),
        row('si_hi_ceiling_multiple', 20),
        row('ui_ceiling_multiple', 20),
        row('employer_si_rate', 0.175),
        row('employer_hi_rate', 0.03),
        row('employer_ui_rate', 0.01),
        row('union_rate', 0.02),
        row('thirteenth_month', 1, basis='template'),
        row('admin_markup', 0.10, basis='template'),
    ]
    return rows + list(extra)


@pytest.fixture
def law_table(monkeypatch):
    """Point statutory_payroll_params at an invented labour-law table instead of the CSV in data/."""
    holder = {'rows': law_rows()}
    real = labor_law_params.params_for_year
    monkeypatch.setattr(labor_law_params, 'params_for_year',
                        lambda year, region=None: real(year, region, rows=holder['rows']))
    return holder


def test_statutory_params_match_the_template_values_for_2026_and_2027(gpo, law_table):
    for year in (2026, 2027):
        assert gpo.statutory_payroll_params(year) == {
            'si_hi_base': 2_530_000, 'ui_base': 5_310_000,
            'si_hi_cap': 50_600_000, 'ui_cap': 106_200_000,       # x20 of each base
            'si_hi_rate': 0.205, 'ui_rate': 0.01, 'union_rate': 0.02, 'markup': 0.1,
        }


def test_statutory_params_use_the_values_in_force_in_december(gpo, law_table):
    """The code comment: 'the values in force in the last month of the schedule year'."""
    law_table['rows'] += [
        {'parameter': 'insurance_base', 'region': '', 'value': 2_900_000,
         'effective_from': datetime.date(2026, 12, 1), 'effective_to': None, 'legal_basis': 'ND new'},
    ]
    p = gpo.statutory_payroll_params(2026)
    assert p['si_hi_base'] == 2_900_000
    assert p['si_hi_cap'] == 58_000_000


def test_statutory_params_ignore_a_change_that_starts_after_the_year(gpo, law_table):
    law_table['rows'] += [
        {'parameter': 'insurance_base', 'region': '', 'value': 3_000_000,
         'effective_from': datetime.date(2027, 1, 1), 'effective_to': None, 'legal_basis': 'ND later'},
    ]
    assert gpo.statutory_payroll_params(2026)['si_hi_base'] == 2_530_000
    assert gpo.statutory_payroll_params(2027)['si_hi_base'] == 3_000_000


def test_statutory_params_take_the_minimum_wage_of_the_region(gpo, law_table):
    law_table['rows'].append({'parameter': 'min_wage_region', 'region': 'II', 'value': 4_730_000,
                              'effective_from': datetime.date(2026, 1, 1), 'effective_to': None,
                              'legal_basis': 'ND 74/2024'})
    assert gpo.statutory_payroll_params(2026)['ui_base'] == 5_310_000            # blank region = Region I
    assert gpo.statutory_payroll_params(2026, 'II')['ui_base'] == 4_730_000
    assert gpo.statutory_payroll_params(2026, 'II')['ui_cap'] == 94_600_000


def test_statutory_params_refuse_a_region_that_does_not_exist(gpo, law_table):
    with pytest.raises(ValueError):
        gpo.statutory_payroll_params(2026, 'V')


# ---------------------------------------------------------------- a1_extra_formulas

HEADCOUNT, ANNUAL_GROSS, FACTOR = 2, 120_000_000, 1          # 10,000,000 a month for each of 2 people


def extras(gpo, position):
    formulas = gpo.a1_extra_formulas(5, position)
    return [evaluate(f, **{'$B5': HEADCOUNT, '$AA5': ANNUAL_GROSS, '$R5': FACTOR}) if isinstance(f, str) else f
            for f in formulas]


def test_extras_of_an_ordinary_in_house_position(gpo):
    """Annual extras for 2 people on 10M a month: team building 300k, training 1.3%, check-up 1.35M, accident
    (floor 30,000 a month because 40% of the base / 12 is 29,199.5), uniform 300k (existing_staffing A1_* constants)."""
    team, training, checkup, accident, uniform = extras(gpo, 'Technician')
    assert team == 2 * 300_000 * 12
    assert training == pytest.approx(2 * 10_000_000 * 0.013 * 12)
    assert checkup == 2 * 1_350_000
    assert accident == 2 * 30_000 * 12
    assert uniform == 2 * 300_000 * 12


def test_property_manager_row_has_its_own_team_building_and_accident_rule(gpo):
    team, _training, _checkup, accident, _uniform = extras(gpo, 'Property Manager')
    assert team == 2 * 1_000_000 * 12
    base = 10_000_000 * 30 * 0.00099 + 10_000_000 * 3 * 0.0044 + 446_985
    assert accident == pytest.approx(2 * (base + 2_456_000) * 0.58 / 12 * 12)


def test_assistant_property_manager_is_not_costed_as_the_property_manager(gpo):
    """STAFF_COST_EXCLUDE keeps the assistant out of the PM group."""
    assert extras(gpo, 'Assistant Property Manager')[0] == 2 * 300_000 * 12


@pytest.mark.parametrize('position', ['Security Guard', 'Cleaning Staff', 'Landscape Gardener'])
def test_outsourced_positions_carry_no_extras(gpo, position):
    assert gpo.a1_extra_formulas(5, position) == [0] * len(gpo.A1_EXTRA_HEADERS)


def test_extras_follow_the_header_order_and_target_the_row(gpo):
    assert len(gpo.A1_EXTRA_HEADERS) == 5
    formulas = gpo.a1_extra_formulas(17, 'Technician')
    assert len(formulas) == 5
    assert all(f.startswith('=$B17') for f in formulas)
    assert all('$B5' not in f and '$AA5' not in f for f in formulas)


def test_extras_columns_sit_right_after_the_working_days_column(gpo):
    assert gpo.EXTRAS_FIRST_LETTER == 'AB'
    assert gpo.EXTRAS_LAST_LETTER == 'AF'
    assert gpo.A1_EXTRA_HEADERS[1] == f'Training {existing_staffing.A1_TRAINING_RATE:.1%} (A1)'


# ---------------------------------------------------------------- staff categories

def test_new_prospect_takes_the_first_matching_category_only(gpo):
    cats, first_match = gpo.staff_market_categories({'existing': None})
    assert first_match is True
    assert gpo.in_staff_category('Assistant Property Manager', 'Assistant Property Manager', cats, first_match)
    assert not gpo.in_staff_category('Assistant Property Manager', 'Property Manager', cats, first_match)
    assert gpo.in_staff_category('Customer Service Supervisor', 'Customer Service Supervisor', cats, first_match)
    assert not gpo.in_staff_category('Customer Service Supervisor', 'Customer Service', cats, first_match)
    assert gpo.in_staff_category('Property Manager', 'Property Manager', cats, first_match)


def test_new_prospect_has_the_four_extra_positions(gpo):
    cats, _ = gpo.staff_market_categories({})
    for name in ('Operations Manager', 'Accountant', 'Cashier', 'Technical Secretary'):
        assert name in cats
        assert gpo.in_staff_category(name, name, cats, True)


def test_existing_project_keeps_the_original_substring_match(gpo):
    """Existing mode: the assistant is still counted under Property Manager, and may count in more than one category."""
    cats, first_match = gpo.staff_market_categories({'existing': {'any': 'thing'}})
    assert first_match is False
    assert cats is gpo.STAFF_MARKET_KEYWORDS
    assert gpo.in_staff_category('Assistant Property Manager', 'Property Manager', cats, first_match)
    assert gpo.in_staff_category('Customer Service Supervisor', 'Customer Service', cats, first_match)
    assert 'Accountant' not in cats


def test_position_match_ignores_case_and_unmatched_positions_fall_in_no_category(gpo):
    cats, first_match = gpo.staff_market_categories({})
    assert gpo.in_staff_category('CHIEF ENGINEER', 'Chief Engineer', cats, first_match)
    assert not any(gpo.in_staff_category('Cleaning Staff', name, cats, first_match) for name in cats)


# ---------------------------------------------------------------- stable operation

def test_year_fill_path_is_the_ramp_unless_the_project_is_stable(gpo):
    assert gpo._year_fill_path({}) == gpo.YEAR_FILL_PATH
    assert gpo._year_fill_path({'stable_operation': False}) == gpo.YEAR_FILL_PATH
    stable = gpo._year_fill_path({'stable_operation': True})
    assert [label for label, _ in stable] == [label for label, _ in gpo.YEAR_FILL_PATH]
    assert {fill for _, fill in stable} == {1.0}


def test_stable_prefix_appears_only_for_stable_projects(gpo):
    assert gpo._stable_prefix({}) == ''
    assert gpo._stable_prefix({'stable_operation': True}) == gpo.STABLE_NOTE_EN
    assert gpo._stable_prefix({'stable_operation': True}, 'custom ') == 'custom '
    assert gpo._stable_prefix({'stable_operation': False}, 'custom ') == ''


# ---------------------------------------------------------------- _load_capex_reserve

def test_reserve_rate_is_the_mean_of_the_annualised_reserve_observations(gpo, tmp_path, monkeypatch):
    path = tmp_path / CAPEX_RESERVE_FILE
    write_capex_csv(path)
    monkeypatch.setattr(gpo, 'CAPEX_RESERVE_CSV', str(path))
    rate, n, lo, hi, names = gpo._load_capex_reserve()
    assert n == 3                                            # the full-repeat row is excluded
    assert rate == pytest.approx((0.10 + 0.08 + 0.12) / 3)
    assert (lo, hi) == (0.08, 0.12)
    assert names[0] == 'Tower Alpha'                         # text after the last " - "
    assert len(names[2]) == 28                               # long names are cut to 28 characters


def test_reserve_rate_refuses_a_missing_file_instead_of_falling_back(gpo, tmp_path, monkeypatch):
    monkeypatch.setattr(gpo, 'CAPEX_RESERVE_CSV', str(tmp_path / 'nothing.csv'))
    with pytest.raises(FileNotFoundError, match='Refusing to fall back'):
        gpo._load_capex_reserve()


def test_reserve_rate_refuses_a_file_without_reserve_observations(gpo, tmp_path, monkeypatch):
    path = tmp_path / CAPEX_RESERVE_FILE
    write_capex_csv(path, rows=CAPEX_ROWS[3:])               # only the full-repeat row
    monkeypatch.setattr(gpo, 'CAPEX_RESERVE_CSV', str(path))
    with pytest.raises(ValueError, match='no "reserve" observations'):
        gpo._load_capex_reserve()


def test_module_constants_come_from_the_loaded_table(gpo):
    assert gpo.CAPEX_RESERVE_N >= 1
    assert gpo.CAPEX_RESERVE_LO <= gpo.CAPEX_RESERVE_RATE <= gpo.CAPEX_RESERVE_HI
    assert len(gpo.CAPEX_RESERVE_PROJECTS) == gpo.CAPEX_RESERVE_N
    assert f'{gpo.CAPEX_RESERVE_N} real Savills projects' in gpo.CAPEX_RESERVE_SOURCE


# ---------------------------------------------------------------- Capex reserve formulas

@pytest.fixture
def rate10(gpo, monkeypatch):
    monkeypatch.setattr(gpo, 'CAPEX_RESERVE_RATE', 0.10)
    return 0.10


@pytest.mark.parametrize('drop_year', [2, 3, 4])
def test_years_before_the_drop_year_repeat_the_full_purchase(gpo, rate10, drop_year):
    for year in range(1, 5):
        formula, full = gpo._capex_reserve_formula('C5', year, drop_year)
        if year < drop_year:
            assert (formula, full) == ('=C5', True)
        else:
            assert (formula, full) == ('=C5*0.1', False)


def test_year_one_is_always_a_full_purchase_for_every_allowed_drop_year(gpo, rate10):
    assert all(gpo._capex_reserve_formula('C5', 1, d)[1] for d in (2, 3, 4))


def test_monthly_full_purchase_year_puts_the_lump_sum_in_month_one_only(gpo, rate10):
    assert gpo._capex_reserve_monthly_formula('C5', 1, 3) == ('=C5', 'FFF7CC')
    assert gpo._capex_reserve_monthly_formula('C5', 13, 3) == ('=C5', 'FFF7CC')
    for month in list(range(2, 13)) + list(range(14, 25)):
        assert gpo._capex_reserve_monthly_formula('C5', month, 3) == (0, None)


def test_monthly_reserve_years_spread_the_reserve_over_twelve_months(gpo, rate10):
    for month in (25, 36, 37, 48):
        assert gpo._capex_reserve_monthly_formula('C5', month, 3) == ('=C5*0.1/12', 'E2EFDA')


def test_drop_year_boundary_months(gpo, rate10):
    assert gpo._capex_reserve_monthly_formula('C5', 12, 2)[0] == 0           # last month of the full year
    assert gpo._capex_reserve_monthly_formula('C5', 13, 2)[0] == '=C5*0.1/12'  # first month of the reserve year


@pytest.mark.parametrize('drop_year', [2, 3, 4])
def test_monthly_table_adds_up_to_the_yearly_table(gpo, rate10, drop_year):
    """Same capex cell: each year of 12 monthly rows equals the yearly row for that year."""
    capex = 1_200_000
    for year in range(1, 5):
        yearly = evaluate(gpo._capex_reserve_formula('C5', year, drop_year)[0], C5=capex)
        monthly = 0
        for month in range((year - 1) * 12 + 1, year * 12 + 1):
            f = gpo._capex_reserve_monthly_formula('C5', month, drop_year)[0]
            monthly += f if isinstance(f, int) else evaluate(f, C5=capex)
        assert monthly == pytest.approx(yearly)


# ---------------------------------------------------------------- _fix_fake_formula_strings

def workbook_with(*cells, sheet2=()):
    wb = openpyxl.Workbook()
    ws = wb.active
    for i, value in enumerate(cells, start=1):
        ws.cell(row=i, column=1, value=value)
    if sheet2:
        ws2 = wb.create_sheet('Second')
        for i, value in enumerate(sheet2, start=1):
            ws2.cell(row=i, column=1, value=value)
    return wb


def test_prose_that_starts_with_equals_and_a_space_becomes_plain_text(gpo):
    wb = workbook_with('= Car Slots × 12.5 m²/slot', '=   padded note')
    gpo._fix_fake_formula_strings(wb)
    ws = wb.active
    assert ws['A1'].value == 'Car Slots × 12.5 m²/slot'
    assert ws['A2'].value == 'padded note'
    assert ws['A1'].data_type == 's' and ws['A2'].data_type == 's'


@pytest.mark.parametrize('formula', ['=A1+B1', '=SUM(A1:A3)', '=0', '="text"', '=(1+2)*3', "='Sheet 2'!B4", '=-A1'])
def test_real_formulas_are_left_alone(gpo, formula):
    wb = workbook_with(formula)
    gpo._fix_fake_formula_strings(wb)
    assert wb.active['A1'].value == formula
    assert wb.active['A1'].data_type == 'f'


@pytest.mark.parametrize('value', [None, 0, 5, 3.5, 'plain text', 'a = b', ' = leading space first', '=', ''])
def test_other_values_are_untouched(gpo, value):
    wb = workbook_with(value)
    gpo._fix_fake_formula_strings(wb)
    assert wb.active['A1'].value == value


def test_every_sheet_is_fixed_and_the_count_is_reported(gpo, capsys):
    wb = workbook_with('= one', '=A1', sheet2=['= two', '= three'])
    gpo._fix_fake_formula_strings(wb)
    assert wb['Second']['A1'].value == 'two'
    assert wb['Second']['A2'].value == 'three'
    assert wb.active['A2'].value == '=A1'
    assert 'Fixed 3 text annotation(s)' in capsys.readouterr().out


def test_nothing_printed_when_nothing_to_fix(gpo, capsys):
    gpo._fix_fake_formula_strings(workbook_with('=A1', 'text'))
    assert capsys.readouterr().out == ''


def test_a_fixed_workbook_saves_and_reads_back_as_text(gpo, tmp_path):
    wb = workbook_with('= Car Slots × 12.5 m²/slot', '=1+1')
    gpo._fix_fake_formula_strings(wb)
    path = tmp_path / 'fixed.xlsx'
    wb.save(path)
    ws = openpyxl.load_workbook(path).active
    assert ws['A1'].value == 'Car Slots × 12.5 m²/slot' and ws['A1'].data_type == 's'
    assert ws['A2'].value == '=1+1'


# ---------------------------------------------------------------- _strip_onedrive_zip_artifacts

PARTS = {'[Content_Types].xml': b'<types/>', 'xl/workbook.xml': b'<wb/>', 'xl/worksheets/sheet1.xml': b'<s1/>'}


def make_zip(path, parts=PARTS, trash=()):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
        for name in trash:
            z.writestr(name, b'xx')
    return str(path)


def read_zip(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


@pytest.fixture
def sleeps(monkeypatch):
    """Record time.sleep calls instead of waiting."""
    import time
    calls = []
    monkeypatch.setattr(time, 'sleep', lambda s: calls.append(s))
    return calls


def test_trash_entries_are_removed_and_real_parts_kept(gpo, tmp_path, sleeps, capsys):
    path = make_zip(tmp_path / 'a.xlsx', trash=['[trash]/0001.dat', '[trash]/0002.dat'])
    gpo._strip_onedrive_zip_artifacts(path)
    assert read_zip(path) == PARTS
    assert 'Stripped 2 OneDrive-injected' in capsys.readouterr().out


def test_a_clean_file_is_not_rewritten(gpo, tmp_path, sleeps, capsys):
    path = make_zip(tmp_path / 'clean.xlsx')
    os.utime(path, (1_700_000_000, 1_700_000_000))           # an old modified time shows any rewrite
    before = open(path, 'rb').read()
    gpo._strip_onedrive_zip_artifacts(path)
    assert open(path, 'rb').read() == before
    assert os.stat(path).st_mtime == 1_700_000_000
    assert capsys.readouterr().out == ''


def test_no_temporary_file_is_left_behind(gpo, tmp_path, sleeps):
    path = make_zip(tmp_path / 'a.xlsx', trash=['[trash]/0001.dat'])
    gpo._strip_onedrive_zip_artifacts(path)
    assert sorted(os.listdir(tmp_path)) == ['a.xlsx']


def test_it_stops_after_two_clean_checks(gpo, tmp_path, sleeps):
    path = make_zip(tmp_path / 'clean.xlsx')
    gpo._strip_onedrive_zip_artifacts(path, poll_interval=1.5)
    assert sleeps == [1.5, 1.5]


def test_it_keeps_watching_after_it_strips_something(gpo, tmp_path, sleeps):
    """One strip resets the clean streak: strip, then two clean checks = three polls."""
    path = make_zip(tmp_path / 'a.xlsx', trash=['[trash]/0001.dat'])
    gpo._strip_onedrive_zip_artifacts(path)
    assert len(sleeps) == 3


def test_trash_that_reappears_later_is_stripped_again(gpo, tmp_path, monkeypatch):
    """OneDrive injects its patch some seconds after the file lands: re-strip each time it comes back."""
    import time
    path = make_zip(tmp_path / 'a.xlsx')
    state = {'n': 0}

    def sleep(_s):
        state['n'] += 1
        if state['n'] == 2:                                  # appears during the second wait
            make_zip(path, trash=['[trash]/0009.dat'])

    monkeypatch.setattr(time, 'sleep', sleep)
    gpo._strip_onedrive_zip_artifacts(path)
    assert read_zip(path) == PARTS
    assert state['n'] == 4                                   # wait 1 clean; wait 2 injects, strip; waits 3-4 clean


def test_it_gives_up_after_max_polls_when_trash_never_stops(gpo, tmp_path, monkeypatch):
    import time
    path = make_zip(tmp_path / 'a.xlsx')
    polls = []

    def sleep(_s):
        polls.append(1)
        make_zip(path, trash=['[trash]/0001.dat'])

    monkeypatch.setattr(time, 'sleep', sleep)
    gpo._strip_onedrive_zip_artifacts(path, max_polls=4)
    assert len(polls) == 4                                   # no endless loop


def test_a_missing_or_corrupt_file_only_prints_a_warning(gpo, tmp_path, sleeps, capsys):
    gpo._strip_onedrive_zip_artifacts(str(tmp_path / 'nope.xlsx'))
    assert 'Could not check/strip zip artifacts (non-fatal)' in capsys.readouterr().out
    bad = tmp_path / 'bad.xlsx'
    bad.write_bytes(b'not a zip')
    gpo._strip_onedrive_zip_artifacts(str(bad))
    assert 'non-fatal' in capsys.readouterr().out
    assert bad.read_bytes() == b'not a zip'


def test_a_file_name_that_only_looks_like_trash_is_kept(gpo, tmp_path, sleeps):
    parts = dict(PARTS)
    parts['xl/trash/notes.xml'] = b'<n/>'                    # not under the "[trash]/" prefix
    path = make_zip(tmp_path / 'a.xlsx', parts=parts, trash=['[trash]/0001.dat'])
    gpo._strip_onedrive_zip_artifacts(path)
    assert read_zip(path) == parts
