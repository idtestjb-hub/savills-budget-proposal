"""Unit tests for webapp/facts_prefill.py (change prefill-review-facts): name folding, the master list lookup, the
earlier run's form, and the merge by priority. TEST DATA: invented projects only."""
import csv

import openpyxl

from webapp import facts_prefill as fp

MASTER_HEAD = ['Name', 'City_Province', 'District', 'TowerCount', 'FloorCount', 'GateCount', 'CarParkingSlots',
               'BikeParkingSlots', 'PoolCount']


def _master(tmp_path, rows):
    path = tmp_path / 'master.csv'
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(MASTER_HEAD)
        w.writerows(rows)
    return str(path)


def _form(tmp_path, values, name='form.xlsx'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Project Info'
    for i, (label, value) in enumerate(values.items(), start=1):
        ws.cell(row=i, column=1, value=label)
        ws.cell(row=i, column=2, value=value)
    path = tmp_path / name
    wb.save(path)
    return str(path)


def test_fold_drops_accents_case_spacing_and_punctuation():
    assert fp.fold('HOÀNG ANH GIAI VIỆT') == fp.fold('Hoang Anh Giai Viet') == 'hoanganhgiaiviet'
    assert fp.fold('HOANG ANH RIVER VIEW') == fp.fold('Hoang Anh Riverview')
    assert fp.fold('Dragon Parc1') == fp.fold('Dragon  Parc 1')
    assert fp.fold('Đông Đô') == 'dongdo'
    assert fp.fold('Masteri West Heights') != fp.fold('Masteri Thao Dien')


def test_master_unique_match_zero_is_no_value_and_pool_from_count(tmp_path):
    path = _master(tmp_path, [['Test Tower A', 'HCM', 'Quận 9', '1', '30', '0', '120', '', '1'],
                              ['Test Tower B', '', '', '0', '0', '2', '0', '500', '0']])
    a, notes = fp.master_facts('TEST TOWER A', path)
    assert a == {'city': 'HCM', 'district': 'Quận 9', 'floor_count': 30, 'car_slots': 120, 'has_pool': 'Yes'}
    assert notes == [dict(key='tower_count', text='master ghi 1 tháp; số tháp để PM kiểm và nhập')]   # towers never filled
    b, _ = fp.master_facts('test tower b', path)
    assert b == {'gate_count': 2, 'moto_slots': 500}          # zeros and blanks fill nothing, PoolCount 0 too


def test_master_floors_of_one_tower_only(tmp_path):
    path = _master(tmp_path, [['Test Park', 'HCM', '', '3', '29', '1', '', '', '']])
    facts, notes = fp.master_facts('Test Park', path)
    assert 'floor_count' not in facts and 'tower_count' not in facts
    assert notes == [dict(key='floor_count', text='master ghi 29 tầng/tháp với 3 tháp; số tầng cả dự án để PM nhập'),
                     dict(key='tower_count', text='master ghi 3 tháp; số tháp để PM kiểm và nhập')]


def test_master_duplicate_names_fill_nothing(tmp_path):
    path = _master(tmp_path, [['Test Twin', 'HCM', '', '1', '', '', '', '', ''],
                              ['TEST  TWIN', 'HCM', '', '2', '', '', '', '', '']])
    facts, notes = fp.master_facts('Test Twin', path)
    assert facts == {} and notes[0]['key'] == '' and '2 dòng trùng tên' in notes[0]['text']
    assert fp.master_facts('Test Other', path) == ({}, [])


def test_earlier_run_reads_its_form_and_skips_blank_forms(tmp_path):
    full = _form(tmp_path, {'City / Province': 'Hà Nội', 'Tower Count': 3, 'Floor Count': 0, 'Car Parking Slots': 400,
                            'Has Swimming Pool?': None}, 'full.xlsx')
    blank = _form(tmp_path, {'City / Province': None, 'Tower Count': 0}, 'blank.xlsx')
    runs = [dict(id='r3', project='Other Project', input_form=full),
            dict(id='r2', project='TEST TOWER', input_form=blank),           # newest of the project, but no facts
            dict(id='r1', project='Test Tower', input_form=full)]
    run, facts = fp.earlier_run(runs, 'Test  Tower')
    assert run['id'] == 'r1'
    assert facts == {'city': 'Hà Nội', 'tower_count': 3, 'car_slots': 400}   # 0 and a blank pool are no value


def test_merge_keeps_priority_and_lists_differing_sources():
    out = fp.merge([('run', 'lượt trước 20/10/2026', {'tower_count': 3, 'city': 'Hồ Chí Minh'}),
                    ('info', 'sheet 0. Info', {'car_slots': 472}),
                    ('master', 'danh sách master', {'tower_count': 2, 'city': 'Ho Chi Minh City', 'car_slots': 472})])
    assert out['tower_count']['value'] == 3 and out['tower_count']['source'] == 'run'
    assert out['tower_count']['others'] == [dict(source='master', label='danh sách master', value=2)]
    assert out['city']['others'] == []                 # 'Ho Chi Minh' and 'Hồ Chí Minh' are one city
    assert out['car_slots']['source'] == 'info' and out['car_slots']['others'] == []
    assert 'district' not in out


def test_prefill_without_file_or_run_uses_the_master(tmp_path):
    path = _master(tmp_path, [['Test Tower', 'HCM', '', '1', '20', '', '', '', '']])
    got = fp.prefill(dict(project='TEST TOWER', path=''), [], master_path=path)
    assert got['run_id'] is None and got['fields']['floor_count'] == dict(
        value=20, source='master', label='danh sách master', others=[])
