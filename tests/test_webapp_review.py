"""Trang web: chế độ Review (api/reviews), Lịch sử dự án (api/history), Clone (api/runs/<id>/input), dựng lại lượt từ đĩa.

Lượt chạy được dựng giả trong thư mục tạm (không chạy pipeline), trừ một test end-to-end chạy review_run.py thật trên
file ngân sách bịa của tests/test_review_import.py (bỏ qua khi máy không có Excel). Dữ liệu và tên dự án đều bịa.
"""
import json
import os
import time

import openpyxl
import pytest

os.environ['BUDGET_WEB_AUTH'] = 'off'
pytest.importorskip('fastapi')
from fastapi.testclient import TestClient  # noqa: E402

from webapp import fill_input, history, results, server  # noqa: E402
from tests.test_review_import import build_prior_workbook  # noqa: E402

DELIV = 'Khu Thu Nghiem - Sample Consulting Budget.xlsx'
INTERNAL = ['Project_Budget_Output.xlsx', 'Roster_Demand_Model.xlsx']


@pytest.fixture
def runs_dir(tmp_path, monkeypatch):
    d = tmp_path / 'web_runs'
    d.mkdir()
    monkeypatch.setattr(server, 'RUNS_DIR', str(d))
    server._runs.clear()
    server._active['id'] = None
    yield d
    server._runs.clear()
    server._active['id'] = None


@pytest.fixture
def client():
    return TestClient(server.app)


def _new_run(runs_dir, run_id='20261019-100000_Khu-Thu-Nghiem', with_input=True):
    """Một lượt 'new' như server đời trước để lại (không có web_meta.json): run_log json + 3 file + form."""
    wd = runs_dir / run_id
    (wd / 'run_log').mkdir(parents=True)
    (wd / 'run_log' / '20261019-100100_x.json').write_text(json.dumps(dict(
        status='ok', project_name='Khu Thu Nghiem', budget_year=2027, vat_basis='inclusive',
        revenue_vnd=10.0, expense_vnd=4.0, fund_surplus_vnd=6.0)), encoding='utf-8')
    for name in [DELIV] + INTERNAL:
        (wd / name).write_bytes(b'PK\x03\x04 test')
    if with_input:
        fill_input.write_input(dict(scalars=dict(project_name='Khu Thu Nghiem', city='Ho Chi Minh City', district='Quan 9',
                                                 tower_count=3, floor_count=60, gate_count=2, has_pool='Yes',
                                                 pool_volume=450, car_slots=120, moto_slots=900),
                                    products=[dict(name='Apartment', gfa=50000, nfa=42000, units=400)]),
                               str(wd / 'Project_Budget_Input.xlsx'))
    (wd / 'run.log').write_text('[1/2] x\n[2/2] y\n', encoding='utf-8')
    return wd


def _review_run(runs_dir, run_id='20261020-090000_review-Khu-Thu-Nghiem'):
    """Một lượt 'review' đã xong: review_summary.json, review_notes.json, run\\3 file, input\\form, web_meta.json."""
    wd = runs_dir / run_id
    (wd / 'run').mkdir(parents=True)
    (wd / 'input').mkdir()
    for name in [DELIV] + INTERNAL:
        (wd / 'run' / name).write_bytes(b'PK\x03\x04 test')
    (wd / 'input' / 'Project_Budget_Input.xlsx').write_bytes(b'PK')
    (wd / 'review_summary.json').write_text(json.dumps(dict(
        meta=dict(prior_year=2026, budget_year=2027, deliverable_incl=True, file_incl=False, file_name='approved_2026.xlsx',
                  period_text='01/2026–12/2026', project='Khu Thu Nghiem', ran_at='2026-10-20T09:01:00',
                  workdir=str(wd), form='x', deliverable='y', analysis='z'),
        summary=dict(MF=dict(R=dict(approved=100.0, converted=108.0, tool=90.0, diff=-18.0, pct=-0.1667),
                             E=dict(approved=80.0, converted=86.4, tool=70.0, diff=-16.4, pct=-0.19),
                             S=dict(converted=21.6, tool=20.0, approved=20.0, diff=-1.6, pct=-0.074))),
        counts=dict(lines=5, both=3, only_approved=1, only_tool=1, not_on_form=1, no_method=1, tool_zero=0),
        ties=[dict(kind='công cụ = bản giao', fund='MF', section='R', left=90.0, right=90.0, diff=0.0, ok=True),
              dict(kind='duyệt = file nguồn', fund='MF', section='E', left=80.0, right=81.5, diff=-1.5, ok=False)],
        top=[dict(code='ESS38', item='Chia sẻ doanh thu bãi xe', converted=10.0, tool_num=0.0, diff=-10.0, pct=-1.0,
                  label='Chưa có phương pháp', remark='', fund='MF', section='E')])), encoding='utf-8')
    (wd / 'review_notes.json').write_text(json.dumps(dict(
        notes=[dict(kind='để trống, PM điền', where='Site Area', text='file ngân sách không có dữ kiện này (ghi 0)'),
               dict(kind='không có trên form 2027', where='ESA1', text='dòng 40: Safe inspection = 5,000,000')],
        filled=dict(blank=['Site Area'], facts=['City / Province'], rates={'Apartment': [20000.0, 'incl. VAT']}, parking={}),
        exit_code=1)), encoding='utf-8')
    history.write_meta(str(wd), kind='review', project='Khu Thu Nghiem', user='pm.test', started='2026-10-20T09:00:00',
                       status='done', rc=1, finished='2026-10-20T09:02:00', source='file approved_2026.xlsx',
                       budget_year=2027, prior_year=2026)
    (wd / 'run.log').write_text('[1/4] a\n    phân tích: z\n[4/4] b\n', encoding='utf-8')
    return wd


# ---- history.py ----------------------------------------------------------------------------------

def test_history_scan_describes_old_and_review_runs(runs_dir):
    _new_run(runs_dir)
    _review_run(runs_dir)
    (runs_dir / 'not a run.txt').write_text('x')
    rows = history.scan(str(runs_dir))
    assert [r['kind'] for r in rows] == ['review', 'new']           # mới nhất trước
    rv, nw = rows
    assert nw['project'] == 'Khu Thu Nghiem' and nw['budget_year'] == 2027 and nw['status'] == 'done'
    assert nw['started'] == '2026-10-19T10:00:00' and nw['user'] == '' and nw['input_form'].endswith('Project_Budget_Input.xlsx')
    assert rv['prior_year'] == 2026 and rv['user'] == 'pm.test' and rv['status'] == 'done' and rv['source'].startswith('file')
    assert [o['kind'] for o in rv['outputs']] == ['deliverable', 'analysis', 'roster']
    assert rv['input_form'].endswith(os.path.join('input', 'Project_Budget_Input.xlsx'))


def test_history_failed_when_outputs_missing(runs_dir):
    wd = runs_dir / '20261019-110000_Hong'
    wd.mkdir()
    (wd / DELIV).write_bytes(b'PK')
    history.write_meta(str(wd), kind='new', project='Hong', status='running')   # server dừng giữa chừng
    row = history.describe(str(wd))
    assert row['status'] == 'failed' and row['project'] == 'Hong'


def test_review_summary_reader(runs_dir):
    wd = _review_run(runs_dir)
    s = results.review_summary(str(wd))
    assert s['kind'] == 'review' and s['meta']['prior_year'] == 2026 and 'workdir' not in s['meta']
    assert s['summary']['MF']['S']['tool'] == 20.0 and s['counts']['no_method'] == 1
    assert [t['ok'] for t in s['ties']] == [True, False]
    assert s['top'][0]['code'] == 'ESS38' and len(s['notes']) == 2 and s['filled']['blank'] == ['Site Area']
    assert results.review_summary(str(runs_dir))['note'].startswith('Chưa có review_summary.json')
    assert results.summarize_run(str(wd), 'review')['kind'] == 'review'


# ---- API: lịch sử, dựng lại từ đĩa, Clone -----------------------------------------------------------

def test_api_history_and_rehydrate(client, runs_dir):
    _new_run(runs_dir)
    wd = _review_run(runs_dir)
    body = client.get('/api/history').json()
    assert [r['kind'] for r in body['runs']] == ['review', 'new'] and body['active'] is None
    rv = body['runs'][0]
    assert rv['can_clone'] and rv['can_gen'] and len(rv['outputs']) == 3 and 'path' not in rv['outputs'][0]
    assert rv['budget_year'] == 2027 and rv['prior_year'] == 2026 and rv['user'] == 'pm.test'
    # lượt của phiên server trước: api/runs/<id> dựng lại từ thư mục
    run = client.get(f'/api/runs/{wd.name}').json()
    assert run['kind'] == 'review' and run['status'] == 'done' and run['rc'] == 1
    assert run['summary']['summary']['MF']['R']['tool'] == 90.0 and run['log'][0] == '[1/4] a'
    assert client.get(f'/api/runs/{wd.name}/files/{DELIV}').status_code == 200      # file nằm trong run\\
    assert client.get('/api/runs/20261020-000000_khong-co').status_code == 404
    assert client.get('/api/runs/..').status_code == 404


def test_api_history_viewer_sees_only_deliverable(client, runs_dir):
    wd = _review_run(runs_dir)
    body = client.get('/api/history', headers={'X-Hub-Role': 'viewer'}).json()
    assert [o['kind'] for o in body['runs'][0]['outputs']] == ['deliverable']
    run = client.get(f'/api/runs/{wd.name}', headers={'X-Hub-Role': 'viewer'}).json()
    assert [o['kind'] for o in run['outputs']] == ['deliverable']
    assert not [ln for ln in run['log'] if 'phân tích' in ln]
    assert run['summary']['summary']['MF']['R']['tool'] == 90.0           # viewer vẫn thấy tóm tắt
    assert client.get(f'/api/runs/{wd.name}/files/{INTERNAL[0]}', headers={'X-Hub-Role': 'viewer'}).status_code == 403


def test_api_input_for_clone(client, runs_dir):
    wd = _new_run(runs_dir)
    d = client.get(f'/api/runs/{wd.name}/input').json()
    assert d['kind'] == 'new' and d['scalars']['project_name'] == 'Khu Thu Nghiem'
    assert d['scalars']['city'] == 'Ho Chi Minh City' and d['scalars']['tower_count'] == 3
    assert next(p for p in d['products'] if p['name'] == 'Apartment')['nfa'] == 42000
    wd2 = _new_run(runs_dir, '20261019-120000_Khong-Form', with_input=False)
    assert client.get(f'/api/runs/{wd2.name}/input').status_code == 404


# ---- API: api/reviews (worker giả) -------------------------------------------------------------------

@pytest.fixture
def fake_worker(monkeypatch):
    seen = {}

    def worker(run_id):
        run = server._runs[run_id]
        seen['run'] = run
        rd = os.path.join(run['workdir'], 'run')
        os.makedirs(rd, exist_ok=True)
        for name in [DELIV] + INTERNAL:
            open(os.path.join(rd, name), 'wb').write(b'PK')
        run['rc'], run['outputs'], run['status'] = 0, server._outputs(run['workdir']), 'done'
        run['finished'] = '2026-10-20T10:00:05'
        history.write_meta(run['workdir'], status='done', rc=0)
        server._active['id'] = None

    monkeypatch.setattr(server, '_worker', worker)
    return seen


def _prior_file(tmp_path):
    p = tmp_path / 'NS duyet 2026 (ban cuoi).xlsx'
    build_prior_workbook(str(p))
    return p


def test_review_from_upload_writes_prior_and_facts(client, runs_dir, fake_worker, tmp_path):
    p = _prior_file(tmp_path)
    facts = dict(city='Ho Chi Minh City', district='', tower_count='2', floor_count='', gate_count='1', has_pool='Yes',
                 pool_volume='300', car_slots='', moto_slots='')
    with open(p, 'rb') as fh:
        r = client.post('/api/reviews', files={'prior': (p.name, fh, 'application/octet-stream')},
                        data={'facts': json.dumps(facts)}, headers={'X-Hub-User': 'pm.test'})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['kind'] == 'review' and body['id'].endswith('_review-NS-duyet-2026-ban-cuoi')
    run = fake_worker['run']
    cmd = run['cmd']
    assert cmd[3] == os.path.join(server.HERE, 'review_run.py') and '--recalc' not in cmd
    prior_path = cmd[cmd.index('--prior') + 1]
    assert prior_path.startswith(os.path.join(run['workdir'], 'prior')) and os.path.getsize(prior_path) == p.stat().st_size
    with open(cmd[cmd.index('--facts') + 1], encoding='utf-8') as fh:
        written = json.load(fh)
    assert written['City / Province'] == 'Ho Chi Minh City' and written['Tower Count'] == 2
    assert written['Has Swimming Pool?'] == 'Yes' and written['Pool Volume'] == 300 and written['Gate / Entrance Count'] == 1
    assert 'District' not in written and 'Floor Count' not in written            # ô trống không thành dữ kiện
    assert written['_sources']['City / Province'] == 'nhập trên trang web'
    meta = history.read_meta(run['workdir'])
    assert meta['kind'] == 'review' and meta['user'] == 'pm.test' and meta['source'].startswith('file NS duyet')
    time.sleep(0.2)
    got = client.get(f'/api/runs/{body["id"]}').json()
    assert got['status'] == 'done' and [o['kind'] for o in got['outputs']] == ['deliverable', 'analysis', 'roster']


def test_review_requires_city_and_xlsx(client, runs_dir, fake_worker, tmp_path):
    p = _prior_file(tmp_path)
    with open(p, 'rb') as fh:
        r = client.post('/api/reviews', files={'prior': (p.name, fh)}, data={'facts': json.dumps(dict(city=' '))})
    assert r.status_code == 400 and 'Tỉnh / thành phố' in r.json()['detail']
    r = client.post('/api/reviews', files={'prior': ('ns.pdf', b'%PDF')}, data={'facts': json.dumps(dict(city='HCM'))})
    assert r.status_code == 400 and '.xlsx' in r.json()['detail']
    r = client.post('/api/reviews', data={'facts': json.dumps(dict(city='HCM'))})
    assert r.status_code == 400 and 'Chưa chọn file' in r.json()['detail']
    r = client.post('/api/reviews', data={'facts': 'not json', 'source_run': 'x'})
    assert r.status_code == 400
    assert not os.listdir(runs_dir)                                               # không tạo thư mục lượt


def test_gen_from_old_run_uses_its_deliverable_with_recalc(client, runs_dir, fake_worker):
    wd = _new_run(runs_dir)
    r = client.post('/api/reviews', data={'source_run': wd.name, 'facts': json.dumps(dict(city='Ho Chi Minh City', tower_count='3'))})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['source'] == f'lượt {wd.name}' and body['project'] == 'Khu Thu Nghiem'
    cmd = fake_worker['run']['cmd']
    assert '--recalc' in cmd and cmd[cmd.index('--prior') + 1] == str(wd / DELIV)
    assert body['id'].endswith('_review-Khu-Thu-Nghiem')
    r = client.post('/api/reviews', data={'source_run': '20261019-000000_khong-co', 'facts': json.dumps(dict(city='HCM'))})
    assert r.status_code == 404


def test_one_run_at_a_time_across_both_kinds(client, runs_dir, monkeypatch, tmp_path):
    monkeypatch.setattr(server, '_worker', lambda run_id: None)      # giữ lượt ở trạng thái running
    r = client.post('/api/runs', json=dict(scalars=dict(project_name='Bận'), products=[]))
    assert r.status_code == 200
    p = _prior_file(tmp_path)
    with open(p, 'rb') as fh:
        r = client.post('/api/reviews', files={'prior': (p.name, fh)}, data={'facts': json.dumps(dict(city='HCM'))})
    assert r.status_code == 409
    assert client.get('/api/history').json()['active'] == server._active['id']
    assert client.get('/api/history').json()['runs'][0]['status'] == 'running'


# ---- End-to-end: review_run.py thật (Excel) ---------------------------------------------------------

def _excel_available():
    try:
        import pythoncom
        import win32com.client as w
        pythoncom.CoInitialize()
        xl = w.DispatchEx('Excel.Application')
        xl.Quit()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _excel_available(), reason='Excel is needed for the Review sheet')
def test_end_to_end_review_through_the_api(client, runs_dir, tmp_path):
    p = _prior_file(tmp_path)
    facts = dict(city='Ho Chi Minh City', tower_count='2', floor_count='20', gate_count='2', has_pool='Yes',
                 pool_volume='300', car_slots='150')
    with open(p, 'rb') as fh:
        r = client.post('/api/reviews', files={'prior': (p.name, fh)}, data={'facts': json.dumps(facts)})
    assert r.status_code == 200, r.text
    rid = r.json()['id']
    deadline = time.time() + 420
    while time.time() < deadline:
        run = client.get(f'/api/runs/{rid}').json()
        if run['status'] != 'running':
            break
        time.sleep(2)
    assert run['status'] == 'done', '\n'.join(run['log'][-30:])
    assert run['rc'] == 0 and len(run['outputs']) == 3
    s = run['summary']
    assert s['kind'] == 'review' and s['meta']['prior_year'] == 2026 and s['meta']['budget_year'] == 2027
    assert len(s['ties']) == 8 and all(t['ok'] for t in s['ties'])
    assert s['summary']['MF']['R']['tool'] > 0 and s['counts']['lines'] > 0
    assert any(n['kind'] == 'không có trên form 2027' and n['where'] == 'ESA1' for n in s['notes'])
    assert 'City / Province' in s['filled']['facts']
    analysis = next(o for o in run['outputs'] if o['kind'] == 'analysis')
    wb = openpyxl.load_workbook(os.path.join(run['workdir'], 'run', analysis['name']), read_only=True)
    assert wb.sheetnames[-1] == 'Review'
    wb.close()
    hist = client.get('/api/history').json()['runs']
    assert hist[0]['id'] == rid and hist[0]['status'] == 'done' and hist[0]['kind'] == 'review' and hist[0]['can_gen']
    assert hist[0]['project'] == 'ZZ TEST TOWER'
