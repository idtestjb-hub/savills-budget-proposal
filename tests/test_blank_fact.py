"""Ô dữ kiện để trống cho PM dù master có số (build_site_package --blank-fact, site.json blank_facts; change
add-sinking-fund, người dùng chốt 16/11/2026 cho tổng số thang máy): gói không mang số, và Review trong gói không lấy
lại số master khi PM để trống. TEST DATA: dự án và danh sách master đều bịa."""
import csv
import json
import os

import pytest

import build_site_package as bsp
from webapp import facts_prefill as fp

LIFTS = 'Total Elevators (incl. service)'
HEAD = ['Name', 'City_Province', 'District', 'TowerCount', 'FloorCount', 'GateCount', 'CarParkingSlots',
        'BikeParkingSlots', 'PoolCount', 'ElevatorCount', 'BasementCount', 'Street', 'Address_Raw']


def _master(tmp_path):
    path = tmp_path / 'master.csv'
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        w.writerow(['Test Six', 'HCM', 'Quận 1', '6', '21', '1', '', '', '2', '1', '1', '', ''])
    return str(path)


def test_master_fallback_leaves_a_blanked_label_empty(tmp_path):
    path = _master(tmp_path)
    facts = {'City / Province': 'HCM', '_sources': {}, '_no_master': [LIFTS]}
    added, _ = fp.master_fallback(facts, 'TEST SIX', path=path)
    assert LIFTS not in facts and LIFTS not in added
    assert '_no_master' not in facts                                     # never written to the form as a label
    assert facts['Gate / Entrance Count'] == 1                           # the other blanks still come from the master
    plain = {'City / Province': 'HCM', '_sources': {}}
    fp.master_fallback(plain, 'TEST SIX', path=path)
    assert plain[LIFTS] == 1                                             # without the flag the master fills it


def test_blank_facts_for_drops_the_value_and_notes_it():
    facts, notes = {'city': 'HCM', 'total_lifts': 1}, []
    assert bsp.blank_facts_for(['total_lifts', 'total_lifts'], facts, notes) == ['total_lifts']
    assert 'total_lifts' not in facts and facts['city'] == 'HCM'
    assert [n['key'] for n in notes] == ['total_lifts'] and 'PM nhập' in notes[0]['text']
    with pytest.raises(SystemExit):
        bsp.blank_facts_for(['not_a_fact'], {}, [])


@pytest.mark.parametrize('typed, expect_flag', [(None, True), ('12', False)])
def test_site_review_sends_the_blanked_labels(tmp_path, monkeypatch, typed, expect_flag):
    os.environ['BUDGET_WEB_AUTH'] = 'off'
    pytest.importorskip('fastapi')
    from webapp import server
    d = tmp_path / 'site'
    d.mkdir()
    (d / 'site.json').write_text(json.dumps(dict(project='Test Six', prior_file='', facts=dict(city='HCM'),
                                                 blank_facts=['total_lifts'])), encoding='utf-8')
    monkeypatch.setattr(server, 'SITE_DIR', str(d))
    raw = dict(city='HCM') if typed is None else dict(city='HCM', total_lifts=typed)
    fact_map = server._facts_from_form(raw)
    server._mark_package_facts(fact_map, raw)
    if expect_flag:
        assert fact_map['_no_master'] == [LIFTS] and LIFTS not in fact_map
    else:
        assert '_no_master' not in fact_map and fact_map[LIFTS] == 12      # the PM's figure wins
    monkeypatch.setattr(server, 'SITE_DIR', None)
    plain = server._facts_from_form(dict(city='HCM'))
    server._mark_package_facts(plain, dict(city='HCM'))
    assert '_no_master' not in plain                                     # outside a package nothing changes
    assert os.path.isfile(d / 'site.json')
