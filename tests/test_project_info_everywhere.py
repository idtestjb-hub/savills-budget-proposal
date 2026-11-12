"""Change project-info-everywhere: the package's own master facts, the per-run fact sources, the 0. Info scale block and
parking rows, and the run page's project info. TEST DATA: invented projects only."""
import csv

import openpyxl
import pytest

import build_site_package as bsp
import generate_project_budget as gpb
import project_facts as pf

HEAD = ['Name', 'City_Province', 'District', 'TowerCount', 'FloorCount', 'GateCount', 'CarParkingSlots',
        'BikeParkingSlots', 'PoolCount', 'ElevatorCount', 'BasementCount', 'Street', 'Address_Raw']


def _master(tmp_path, rows):
    path = tmp_path / 'master.csv'
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        w.writerows(rows)
    return str(path)


# ---- site package: own master row ----------------------------------------------------------------------------------

def test_package_takes_the_one_matching_master_row(tmp_path):
    path = _master(tmp_path, [['Khu Thu Nghiem', 'HCM', 'Quận 9', '4', '20', '2', '300', '900', '1', '8', '2', '', '']])
    facts, notes = bsp.master_facts_for('KHU THỬ NGHIỆM', master_path=path)
    assert facts['gate_count'] == 2 and facts['car_slots'] == 300 and facts['basements'] == 2
    assert 'tower_count' not in facts
    assert {n['key'] for n in notes} >= {'tower_count', 'floor_count', 'elevators'}


def test_package_stops_on_two_rows_unless_one_is_named(tmp_path):
    path = _master(tmp_path, [['Khu Thu Nghiem Lo A', 'HCM', '', '1', '', '1', '', '', '', '', '', '', ''],
                              ['KHU THU NGHIEM LO A', 'HCM', '', '2', '', '2', '', '', '', '', '', '', '']])
    with pytest.raises(SystemExit) as e:
        bsp.master_facts_for('Khu Thu Nghiem Lo A', master_path=path)
    assert '2 dòng' in str(e.value) and '--master-row' in str(e.value)
    facts, _ = bsp.master_facts_for('x', master_row='KHU THU NGHIEM LO A', master_path=path)
    assert facts['gate_count'] == 2


def test_package_stops_without_a_row_unless_no_master(tmp_path):
    path = _master(tmp_path, [])
    with pytest.raises(SystemExit):
        bsp.master_facts_for('Khu Khac', master_path=path)
    assert bsp.master_facts_for('Khu Khac', no_master=True, master_path=path) == ({}, [])


# ---- per-run fact sources ------------------------------------------------------------------------------------------

def _form(values, products=()):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Project Info'
    r = 1
    for label, value in values.items():
        ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=value)
        r += 1
    for name, nfa, units in products:
        ws.cell(row=r, column=1, value=name)
        ws.cell(row=r, column=3, value=nfa)
        ws.cell(row=r, column=4, value=units)
        r += 1
    return wb


def test_sources_sheet_round_trip_and_blank_facts():
    wb = _form({'City / Province': 'Hà Nội', 'Gate / Entrance Count': 2, 'Number of Basements': 0,
                'Car Parking Slots': 120, 'Project Mode': 'Existing project'}, [('Apartment', 5000, 80)])
    pf.write_sources(wb, {'Gate / Entrance Count': 'danh sách master', 'Apartment': pf.SRC_FILE})
    facts = {f['label']: f for f in pf.facts_of(wb)}
    assert facts['Gate / Entrance Count']['source'] == 'danh sách master'
    assert facts['City / Province']['source'] == pf.SRC_FORM
    assert facts['Number of Basements']['blank'] and facts['Number of Basements']['source'] == ''
    assert facts[pf.CAR_OWNER_LABEL]['value'] == pf.CAR_OWNER_COMMON     # slots without an ownership read as common
    assert facts['Project Mode']['value'] == 'Dự án đang vận hành'
    assert facts['Apartment NFA']['value'] == 5000 and facts['Apartment units']['source'] == pf.SRC_FILE


def test_form_without_sources_sheet_reads_form_source():
    wb = _form({'Tower Count': 3})
    tower = next(f for f in pf.facts_of(wb) if f['label'] == 'Tower Count')
    assert tower['value'] == 3 and tower['source'] == pf.SRC_FORM


# ---- 0. Info block and parking rows --------------------------------------------------------------------------------

def _info_project(owner, car=300, moto=900):
    wb = _form({'Car Parking Slots': car, 'Moto Parking Slots': moto, pf.CAR_OWNER_LABEL: owner, 'Tower Count': 0})
    return dict(car_slots=car, moto_slots=moto, car_owner=owner, facts_list=pf.facts_of(wb))


@pytest.mark.parametrize('owner, row, other', [(pf.CAR_OWNER_DEV, 15, 16), (pf.CAR_OWNER_COMMON, 16, 15)])
def test_parking_rows_follow_ownership(monkeypatch, owner, row, other):
    monkeypatch.setattr(gpb, '_applied_parking_price', lambda project, key: 1_200_000 if key == 'car' else 145_000)
    ws = openpyxl.Workbook().active
    gpb._fill_info_parking(ws, _info_project(owner))
    assert ws[f'F{row}'].value == 300 and ws[f'I{row}'].value == 1_200_000
    assert ws[f'F{other}'].value is None and ws['F12'].value is None
    assert ws['F18'].value == 900 and ws['I18'].value == 145_000


def test_scale_block_lists_every_fact_and_flags_blanks():
    ws = openpyxl.Workbook().active
    project = _info_project(pf.CAR_OWNER_COMMON)
    last = gpb._write_info_scale_block(ws, project)
    assert ws['B23'].value.startswith('QUY MÔ DỰ ÁN')
    labels = [ws[f'B{r}'].value for r in range(25, last + 1)]
    assert len(labels) == len(project['facts_list'])
    tower_row = 25 + [f['label'] for f in project['facts_list']].index('Tower Count')
    assert ws[f'E{tower_row}'].value == pf.BLANK_TEXT and ws[f'C{tower_row}'].value is None
    assert ws[f'C{tower_row}'].fill.start_color.rgb.endswith('FFF2CC')
