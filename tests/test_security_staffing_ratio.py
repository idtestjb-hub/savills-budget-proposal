"""Security posts sized from fee-paying NFA (change size-security-from-fee-nfa, rules decided 2026-10-19).

Rule source: openspec/changes/size-security-from-fee-nfa/specs/security-staffing-default/spec.md. Invented data only
(the sample fixture is synthetic; the form is built into a temporary folder).
"""
import os

import openpyxl
import pytest

import build_project_input_form as bpf
import generate_project_budget as g

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'verification', 'fixtures', 'Sample_Project_Input.xlsx')
LABEL = 'Security: 24h Posts per 10,000 m² Fee-paying NFA'
OLD_LABEL = 'Security: m² Open Space per Patrol Staff'
MORNING, AFTERNOON, NIGHT = g.SECURITY_PATROL_ROWS
OLD_ROW = g.OLDER_FORM_PATROL_ROW
RATIOS = {'staff_per_gate': 1, 'posts24_per_10k_nfa': 1.7, 'nfa_per_cleaning_staff': 3300,
          'towers_per_supervisor': 2, 'sqm_per_gardener': 2000}


class Cell:
    def __init__(self, value):
        self.value = value


def patrol(project, ratios=RATIOS):
    """The three patrol rows as _staff_on_duty gives them for rows still holding their seeded formulas."""
    out = []
    for pos in (MORNING, AFTERNOON, NIGHT):
        n, _ = g._staff_on_duty(pos, None, Cell('=MAX(0,1)'), g.RATIO_DRIVEN_STAFFING[pos], project, ratios, 11)
        out.append(n)
    return tuple(out)


def project(nfa, gates, open_space=0):
    return {'total_nfa': nfa, 'gate_count': gates, 'open_space': open_space, 'towers': 2, 'garden_area': 0}


# ---------------------------------------------------------------- requirement 1: sized from fee-paying NFA
def test_a_large_project_gets_18_posts_and_16_patrol_per_shift():
    assert g._security_posts(project(101948, 1), RATIOS) == (18, 18)     # ROUNDUP(10.1948 x 1.7 = 17.33) = 18
    assert patrol(project(101948, 1)) == (16, 16, 16)                     # 18 - 1 gate post - 1 CCTV post


def test_the_gates_are_the_floor():
    assert g._security_posts(project(10000, 3), RATIOS) == (4, 2)        # 3 gate posts + CCTV beat ROUNDUP(1.7) = 2
    assert patrol(project(10000, 3)) == (0, 0, 0)


def test_open_space_does_not_count():
    assert patrol(project(54400, 2, open_space=0)) == patrol(project(54400, 2, open_space=45000))


def test_a_round_product_rounds_up_as_excel_does():
    assert g._security_posts(project(100000, 1), RATIOS) == (17, 17)     # 10 x 1.7 = 17 exactly, not 18


def test_the_gate_rule_not_the_gate_rows_is_subtracted():
    assert g._security_gate_posts({'gate_count': 3}, dict(RATIOS, staff_per_gate=1.5)) == 5   # ROUNDUP(4.5)
    assert patrol(project(50000, 3), dict(RATIOS, staff_per_gate=1.5)) == (3, 3, 3)          # 9 - 5 - 1


def test_pm_ratio_is_used():
    assert patrol(project(50000, 1), dict(RATIOS, posts24_per_10k_nfa=2.5)) == (11, 11, 11)   # ROUNDUP(12.5) = 13


def test_typed_number_wins():
    n, basis = g._staff_on_duty(NIGHT, 5, Cell(5), g.RATIO_DRIVEN_STAFFING[NIGHT], project(54400, 2), RATIOS, 13)
    assert n == 5 and 'PM override' in basis


def test_basis_states_the_measure_the_floor_and_the_subtraction():
    _, basis = g._staff_on_duty(MORNING, None, Cell('=X'), g.RATIO_DRIVEN_STAFFING[MORNING], project(54400, 2), RATIOS, 11)
    assert 'Fee-paying NFA (54,400 m²)' in basis and '= 10 post(s)' in basis     # ROUNDUP(5.44 x 1.7 = 9.248)
    assert '2 gate post(s)' in basis and '= 10 post(s) in all' in basis and 'minus the gate posts' in basis


def test_the_posts_land_on_the_ratio_the_service_levels_sheet_measures():
    import service_levels as sl
    total, _ = g._security_posts(project(101948, 1), RATIOS)
    assert sl.measure_security(101948, total) == pytest.approx(18 / 10.1948)
    assert 1.5 <= sl.measure_security(101948, total) <= 3.0                     # Tiêu chuẩn band


# ---------------------------------------------------------------- requirement 2: default 1.7, old label not read, older form
def _read(path):
    return g.read_input(path)


def _rows(demand):
    return {d['Position']: d for d in demand}


def test_an_older_form_uses_1_7_and_counts_its_patrol_row_on_three_shifts(tmp_path):
    wb = openpyxl.load_workbook(FIXTURE)                 # the fixture predates the change: old label, one patrol row
    rs = wb['Roster Setup']
    assert any(str(c.value or '') == OLD_LABEL for c in rs['A'])
    sd = wb['Staffing Demand']
    assert [sd.cell(row=r, column=1).value for r in range(5, sd.max_row + 1)].count(OLD_ROW) == 1
    p = tmp_path / 'old.xlsx'
    wb.save(p)
    proj, ratios, *_rest, demand = _read(str(p))
    assert ratios['posts24_per_10k_nfa'] == 1.7
    rows = _rows(demand)
    assert OLD_ROW not in rows
    assert (proj['total_nfa'], proj['gate_count']) == (54400, 2)         # ROUNDUP(5.44 x 1.7 = 9.248) = 10, minus 2, minus 1
    assert g._security_patrol_per_shift(proj, ratios)[0] == 7
    assert [rows[n]['StaffPerDay'] for n in (MORNING, AFTERNOON, NIGHT)] == [7, 7, 7]
    assert [rows[n]['ShiftCode'] for n in (MORNING, AFTERNOON, NIGHT)] == ['S', 'C', 'D']
    assert len({(rows[n]['CoverageDays'], rows[n]['AvgDailyRate'], rows[n]['SourceRow']) for n in (MORNING, AFTERNOON, NIGHT)}) == 1
    assert 'the form has no such field' in rows[MORNING]['Basis'] and 'counted as a 24-hour post' in rows[MORNING]['Basis']
    assert rows[NIGHT]['Basis'].startswith('Added by the run from Staffing Demand row 11')
    # The three rows sit together where the old row was, so the form's order is kept.
    names = [d['Position'] for d in demand]
    i = names.index(MORNING)
    assert names[i:i + 3] == [MORNING, AFTERNOON, NIGHT]


def test_a_number_typed_on_the_older_forms_patrol_row_counts_on_three_shifts(tmp_path):
    wb = openpyxl.load_workbook(FIXTURE)
    sd = wb['Staffing Demand']
    r = next(r for r in range(5, sd.max_row + 1) if sd.cell(row=r, column=1).value == OLD_ROW)
    sd.cell(row=r, column=3).value = 4
    p = tmp_path / 'typed.xlsx'
    wb.save(p)
    rows = _rows(_read(str(p))[-1])
    assert [rows[n]['StaffPerDay'] for n in (MORNING, AFTERNOON, NIGHT)] == [4, 4, 4]
    assert 'PM override' in rows[MORNING]['Basis']


def test_an_older_forms_patrol_row_moved_off_the_morning_shift_is_left_alone(tmp_path):
    wb = openpyxl.load_workbook(FIXTURE)
    sd = wb['Staffing Demand']
    r = next(r for r in range(5, sd.max_row + 1) if sd.cell(row=r, column=1).value == OLD_ROW)
    sd.cell(row=r, column=2).value = '24H'
    p = tmp_path / 'moved.xlsx'
    wb.save(p)
    rows = _rows(_read(str(p))[-1])
    assert OLD_ROW in rows and rows[OLD_ROW]['StaffPerDay'] == 7 and MORNING not in rows


def test_an_older_form_prices_the_same_posts_as_a_new_form(tmp_path):
    """The money, the posts and the night blend of ESS1 do not depend on which form the PM used."""
    from generate_project_output import SERVICE_CATEGORY_KEYWORDS, SERVICE_EXCLUDE_KEYWORDS, NIGHT_SHIFT_CODES
    old = _read(FIXTURE)[-1]
    wb = openpyxl.load_workbook(FIXTURE)
    sd = wb['Staffing Demand']
    r = next(r for r in range(5, sd.max_row + 1) if sd.cell(row=r, column=1).value == OLD_ROW)
    for name, code, offset in ((MORNING, 'S', 0), (AFTERNOON, 'C', 1), (NIGHT, 'D', 2)):
        sd.insert_rows(r + offset) if offset else None
        sd.cell(row=r + offset, column=1).value = name
        sd.cell(row=r + offset, column=2).value = code
        sd.cell(row=r + offset, column=3).value = '=MAX(0,1)'
        sd.cell(row=r + offset, column=4).value = 7
        sd.cell(row=r + offset, column=5).value = 224000
    p = tmp_path / 'new.xlsx'
    wb.save(p)
    new = _read(str(p))[-1]

    def posts(demand):
        kws = SERVICE_CATEGORY_KEYWORDS['Security']
        matched = [d for d in demand if any(k in d['Position'].lower() for k in kws)
                   and not any(ex in d['Position'].lower() for ex in SERVICE_EXCLUDE_KEYWORDS)]
        roles = sum(-(-d['StaffPerDay'] * 7 // 6) for d in matched)
        night = sum(-(-d['StaffPerDay'] * 7 // 6) for d in matched if d['ShiftCode'] in NIGHT_SHIFT_CODES)
        return roles, night
    assert posts(old) == posts(new)


@pytest.mark.parametrize('raw,expected', [(2.5, 2.5), (None, 1.7), (0, 1.7)])
def test_the_new_field_is_read(tmp_path, raw, expected):
    wb = openpyxl.load_workbook(FIXTURE)
    rs = wb['Roster Setup']
    for c in rs['A']:
        if str(c.value or '') == OLD_LABEL:
            c.value = LABEL
            rs.cell(row=c.row, column=2).value = raw
    p = tmp_path / 'new.xlsx'
    wb.save(p)
    ratios = _read(str(p))[1]
    assert ratios['posts24_per_10k_nfa'] == expected
    note = g._ratio_note('posts24_per_10k_nfa')
    assert (note == '') if raw else ('blank or zero' in note)


def test_the_old_label_is_never_read_as_the_ratio(tmp_path):
    wb = openpyxl.load_workbook(FIXTURE)
    rs = wb['Roster Setup']
    for c in rs['A']:
        if str(c.value or '') == OLD_LABEL:
            rs.cell(row=c.row, column=2).value = 5000     # would be 5,000 posts per 10,000 m² if read
    p = tmp_path / 'old.xlsx'
    wb.save(p)
    assert _read(str(p))[1]['posts24_per_10k_nfa'] == 1.7


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


def test_builder_writes_the_new_field_and_three_patrol_rows(built_form):
    wb = openpyxl.load_workbook(built_form)
    rs = wb['Roster Setup']
    assert rs['A5'].value == LABEL and rs['B5'].value == 1.7 and '1.719' in rs['B5'].comment.text
    assert not any(str(c.value or '') == OLD_LABEL for c in rs['A'])
    sd = wb['Staffing Demand']
    rows = {sd.cell(row=r, column=1).value: [sd.cell(row=r, column=c).value for c in (2, 3, 4)]
            for r in range(5, sd.max_row + 1)}
    assert OLD_ROW not in rows
    formula = ("=MAX(0,ROUNDUP(SUM('Project Info'!$C$22:$C$30)/10000*'Roster Setup'!$B$5,0)"
               "-ROUNDUP('Project Info'!$B$11*'Roster Setup'!$B$4,0)-1)")
    assert rows[MORNING] == ['S', formula, 7]
    assert rows[AFTERNOON] == ['C', formula, 7]
    assert rows[NIGHT] == ['D', formula, 7]
    pi = wb['Project Info']
    assert pi['A11'].value == 'Gate / Entrance Count'          # the gate cell the formula points at
    assert [pi.cell(row=r, column=1).value for r in (22, 30)] == ['Apartment', 'Nursery / Nhà trẻ']   # SUM range


def test_builder_form_runs_through_the_reader_and_matches_the_rule(built_form):
    proj, ratios, *_rest, demand = _read(built_form)
    assert ratios['posts24_per_10k_nfa'] == 1.7 and g._ratio_note('posts24_per_10k_nfa') == ''
    rows = _rows(demand)
    assert OLD_ROW not in rows
    expected, _ = g._security_patrol_per_shift(proj, ratios)
    assert [rows[n]['StaffPerDay'] for n in (MORNING, AFTERNOON, NIGHT)] == [expected] * 3
    assert all('Added by the run' not in rows[n]['Basis'] for n in (MORNING, AFTERNOON, NIGHT))
