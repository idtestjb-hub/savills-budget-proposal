"""The cleaning crew sized from fee-paying NFA (change fix-cleaning-staffing-ratio, rules decided 2026-10-19).

Rule source: openspec/changes/fix-cleaning-staffing-ratio/specs/cleaning-staffing-default/spec.md. Invented data only
(the sample fixture is synthetic; the form is built into a temporary folder).
"""
import os

import openpyxl
import pytest

import build_project_input_form as bpf
import generate_project_budget as g

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'verification', 'fixtures', 'Sample_Project_Input.xlsx')
LABEL = 'Cleaning: m² Fee-paying NFA per Cleaning Staff'
COMMON, SUPERVISOR = 'Cleaning - Common Area', 'Cleaning - Supervisor'
RATIOS = {'staff_per_gate': 1, 'sqm_per_patrol': 5000, 'nfa_per_cleaning_staff': 3300,
          'towers_per_supervisor': 2, 'sqm_per_gardener': 2000}


class Cell:
    def __init__(self, value):
        self.value = value


def crew(project, ratios=RATIOS):
    """(cleaners, supervisors) as _staff_on_duty gives them for rows still holding their seeded formulas."""
    out = []
    for pos in (COMMON, SUPERVISOR):
        n, _ = g._staff_on_duty(pos, None, Cell('=ROUNDUP(1,0)'), g.RATIO_DRIVEN_STAFFING[pos], project, ratios, 9)
        out.append(n)
    return tuple(out)


def project(nfa, towers, open_space=0):
    return {'total_nfa': nfa, 'towers': towers, 'open_space': open_space, 'gate_count': 1, 'garden_area': 0}


# ---------------------------------------------------------------- requirement 1: sized from fee-paying NFA
def test_standard_sample_gets_17_with_one_supervisor():
    assert crew(project(54400, 2)) == (16, 1)          # ROUNDUP(54,400 / 3,300) = 17, minus 1 supervisor


def test_open_space_does_not_count():
    assert crew(project(54400, 2, open_space=0)) == crew(project(54400, 2, open_space=45000))


def test_small_project_keeps_at_least_one_cleaner():
    assert crew(project(2000, 4)) == (1, 2)            # total 1, 2 supervisors, cleaners floored at 1


def test_pm_ratio_is_used():
    assert crew(project(60000, 2), dict(RATIOS, nfa_per_cleaning_staff=4000)) == (14, 1)


def test_typed_number_wins():
    n, basis = g._staff_on_duty(COMMON, 5, Cell(5), g.RATIO_DRIVEN_STAFFING[COMMON], project(54400, 2), RATIOS, 9)
    assert n == 5 and 'PM override' in basis


def test_basis_states_the_measure_and_the_subtraction():
    _, basis = g._staff_on_duty(COMMON, None, Cell('=X'), g.RATIO_DRIVEN_STAFFING[COMMON], project(54400, 2), RATIOS, 9)
    assert 'Fee-paying NFA (54,400 m²)' in basis and '= 17 on duty' in basis and 'minus 1 supervisor' in basis


def test_the_crew_lands_on_the_ratio_the_service_levels_sheet_measures():
    import service_levels as sl
    cleaners, sup = crew(project(54400, 2))
    assert sl.measure_cleaning(54400, cleaners + sup) == pytest.approx(54400 / 17)


# ---------------------------------------------------------------- requirement 2: default 3,300, old label not read
def _read(path):
    return g.read_input(path)


def test_an_older_form_uses_3300_and_says_the_field_is_missing(tmp_path):
    wb = openpyxl.load_workbook(FIXTURE)                 # the fixture predates the change: old label, old formula
    rs = wb['Roster Setup']
    assert any(str(c.value or '').startswith('Cleaning: m² Open Space per Cleaner') for c in rs['A'])
    p = tmp_path / 'old.xlsx'
    wb.save(p)
    proj, ratios, *_rest, demand = _read(str(p))
    assert ratios['nfa_per_cleaning_staff'] == 3300
    row = next(d for d in demand if d['Position'] == COMMON)
    assert row['StaffPerDay'] == 16
    assert 'the form has no such field' in row['Basis']


@pytest.mark.parametrize('raw,expected', [(4000, 4000), (None, 3300), (0, 3300)])
def test_the_new_field_is_read(tmp_path, raw, expected):
    wb = openpyxl.load_workbook(FIXTURE)
    rs = wb['Roster Setup']
    for c in rs['A']:
        if str(c.value or '').startswith('Cleaning: m² Open Space per Cleaner'):
            c.value = LABEL
            rs.cell(row=c.row, column=2).value = raw
    p = tmp_path / 'new.xlsx'
    wb.save(p)
    ratios = _read(str(p))[1]
    assert ratios['nfa_per_cleaning_staff'] == expected
    note = g._ratio_note('nfa_per_cleaning_staff')
    assert (note == '') if raw else ('blank or zero' in note)


# ---------------------------------------------------------------- the form the builder writes
@pytest.fixture
def built_form(tmp_path, monkeypatch):
    reports = tmp_path / 'reports'
    reports.mkdir()
    monkeypatch.setattr(bpf, 'OUT_DIR', str(reports))
    monkeypatch.setattr(bpf, 'FINAL_OUT', str(reports / 'Project_Budget_Input.xlsx'))
    monkeypatch.setattr(bpf, 'OUT', str(tmp_path / 'scratch.xlsx'))
    bpf.main()
    return str(reports / 'Project_Budget_Input.xlsx')


def test_builder_writes_the_new_field_and_formula(built_form):
    wb = openpyxl.load_workbook(built_form)
    rs = wb['Roster Setup']
    assert rs['A6'].value == LABEL and rs['B6'].value == 3300 and '3,324' in rs['B6'].comment.text
    sd = wb['Staffing Demand']
    f = next(sd.cell(row=r, column=3).value for r in range(5, sd.max_row + 1) if sd.cell(row=r, column=1).value == COMMON)
    assert f == ("=MAX(1,ROUNDUP(SUM('Project Info'!$C$22:$C$30)/'Roster Setup'!$B$6,0)"
                 "-ROUNDUP('Project Info'!$B$10/'Roster Setup'!$B$7,0))")
    pi = wb['Project Info']
    assert [pi.cell(row=r, column=1).value for r in (22, 30)] == ['Apartment', 'Nursery / Nhà trẻ']   # SUM range
    assert pi['C21'].value.startswith('NFA')


def test_builder_form_runs_through_the_reader(built_form):
    proj, ratios, *_rest, demand = _read(built_form)
    assert ratios['nfa_per_cleaning_staff'] == 3300 and g._ratio_note('nfa_per_cleaning_staff') == ''
    rows = {d['Position']: d['StaffPerDay'] for d in demand}
    total = -(-proj['total_nfa'] // 3300)
    sup = -(-proj['towers'] // 2)
    assert (rows[COMMON], rows[SUPERVISOR]) == (max(1, total - sup), sup)
