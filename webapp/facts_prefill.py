"""Dữ kiện điền sẵn cho mục 2 của tab Review (change prefill-review-facts).

Ba nguồn, theo thứ tự ưu tiên: lượt chạy trước của cùng dự án (form nhập liệu của lượt đó), sheet 0. Info của file
ngân sách đã duyệt (số chỗ đậu xe), danh sách master Dim_Property_Residential.csv. Cùng dự án = tên giống nhau sau khi
gấp (bỏ dấu, đ -> d, chữ thường, bỏ mọi ký tự không phải chữ hoặc số); không khớp gần đúng. Số 0 hoặc ô trống = chưa có
số, ở mọi nguồn. Số PM sửa trên trang vẫn thắng: trang gửi giá trị đang có trong ô.
"""
import csv
import os
import shutil
import tempfile
import unicodedata

import openpyxl

from input_labels import SheetLabels
from webapp import fill_input

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_CSV = os.path.join(os.path.dirname(SOURCE_DIR), 'data', 'master_list_verified', 'Dim_Property_Residential.csv')

# Ô của mục 2 -> nhãn trên form nhập liệu (fill_input.SCALARS)
FIELDS = ('city', 'district', 'tower_count', 'floor_count', 'gate_count', 'has_pool', 'pool_volume', 'car_slots',
          'moto_slots', 'elevators', 'basements', 'pool_count', 'street')
NUMERIC = {'tower_count', 'floor_count', 'gate_count', 'pool_volume', 'car_slots', 'moto_slots', 'elevators',
           'basements', 'pool_count'}
MASTER_COLUMNS = {'city': 'City_Province', 'district': 'District', 'tower_count': 'TowerCount',
                  'floor_count': 'FloorCount', 'gate_count': 'GateCount', 'car_slots': 'CarParkingSlots',
                  'moto_slots': 'BikeParkingSlots', 'basements': 'BasementCount', 'pool_count': 'PoolCount',
                  'street': 'Street'}
SRC_RUN, SRC_INFO, SRC_MASTER = 'run', 'info', 'master'
# Ô của mục 2 -> nhãn Project Info (change project-info-everywhere): một bảng dùng chung cho trang và lúc chạy.
LABELS = {k: fill_input.SCALARS[k][1] for k in FIELDS}
SOURCE_MASTER = 'danh sách master'


def fold(name):
    """Tên dự án đã gấp: 'KHU THỬ NGHIỆM' == 'Khu Thu Nghiem', 'THAP MAY XANH' == 'Tháp Mây Xanh'."""
    s = unicodedata.normalize('NFD', str(name or '').replace('đ', 'd').replace('Đ', 'D'))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return ''.join(c for c in s if c.isalnum())


def _clean(key, value):
    """Giá trị dùng được, hoặc None: số 0 và ô trống là chưa có số."""
    if value is None:
        return None
    if key in NUMERIC:
        try:
            v = float(str(value).replace(',', '').strip())
        except ValueError:
            return None
        if v <= 0:
            return None
        return int(v) if v == int(v) else v
    if key == 'has_pool':
        t = str(value).strip().lower()
        return 'Yes' if t in ('yes', 'có', 'co') else ('No' if t in ('no', 'không', 'khong') else None)
    text = ' '.join(str(value).split())
    return text or None


def master_facts(name, path=MASTER_CSV):
    """(facts, notes) từ danh sách master cho dự án `name`; notes = [dict(key, text)], key '' là ghi chú chung. facts rỗng
    khi không có dòng khớp hoặc khớp từ hai dòng."""
    key = fold(name)
    if not key or not os.path.exists(path):
        return {}, []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        hits = [r for r in csv.DictReader(fh) if fold(r.get('Name')) == key]
    if not hits:
        return {}, []
    if len(hits) > 1:
        return {}, [dict(key='', text=f'danh sách master có {len(hits)} dòng trùng tên "{hits[0].get("Name", "")}", '
                                       f'không dùng')]
    return row_facts(hits[0])


def master_rows(name, path=MASTER_CSV):
    """Các dòng master có tên gấp trùng `name` (để bên đóng gói chọn khi trùng)."""
    key = fold(name)
    if not key or not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return [r for r in csv.DictReader(fh) if fold(r.get('Name')) == key]


def master_row_by_name(name, path=MASTER_CSV):
    """Dòng master có tên đúng y `name` (sau khi bỏ khoảng trắng hai đầu), hoặc None."""
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8-sig', newline='') as fh:
        hits = [r for r in csv.DictReader(fh) if (r.get('Name') or '').strip() == (name or '').strip()]
    return hits[0] if len(hits) == 1 else None


def row_facts(row):
    """(facts, notes) của một dòng master, theo các quy tắc đã chốt (28/10, 29/10/2026)."""
    facts = {k: _clean(k, row.get(col)) for k, col in MASTER_COLUMNS.items()}
    if facts.get('street') is None:
        facts['street'] = _clean('street', row.get('Address_Raw'))
    notes = []
    towers = facts.get('tower_count')
    elevators = _clean('elevators', row.get('ElevatorCount'))
    if elevators is not None:
        # Master ghi tổng số thang của dự án; ô trên form là số thang mỗi tháp: chỉ chia được khi dự án có một tháp.
        if towers == 1:
            facts['elevators'] = elevators
        else:
            notes.append(dict(key='elevators', text=f'master ghi {elevators:g} thang máy cả dự án với {towers or "?"} '
                                                     f'tháp; số thang mỗi tháp để PM nhập'))
    if facts.get('floor_count') is not None and towers != 1:
        # Master ghi số tầng của một tháp; ô trên trang là tổng các tháp (người dùng chốt 28/10/2026).
        notes.append(dict(key='floor_count', text=f'master ghi {facts["floor_count"]:g} tầng/tháp với {towers or "?"} '
                                                   f'tháp; số tầng cả dự án để PM nhập'))
        facts['floor_count'] = None
    if towers is not None:
        # Số tháp của master không tự điền (người dùng chốt 29/10/2026: một dự án trong master ghi 22 tháp), vì nó vào số giám sát
        # vệ sinh và giá thật; chỉ ghi chú để PM nhập.
        notes.append(dict(key='tower_count', text=f'master ghi {towers:g} tháp; số tháp để PM kiểm và nhập'))
        facts['tower_count'] = None
    pools = facts.get('pool_count')                           # số dương, hoặc None khi 0 / trống
    facts['has_pool'] = 'Yes' if pools else None
    return {k: v for k, v in facts.items() if v is not None}, notes


def master_fallback(facts, name, keep=(), path=MASTER_CSV):
    """Lúc chạy Review (change project-info-everywhere): ô dữ kiện còn trống lấy từ master theo tên gấp.

    `facts` = {nhãn Project Info: giá trị, '_sources': {...}} như server gửi; sửa tại chỗ. `keep` = các khoá đã có số từ
    file ngân sách đã duyệt (số chỗ đậu xe), master không ghi đè. Trả (danh sách nhãn đã điền, ghi chú)."""
    mfacts, notes = master_facts(name, path)
    sources = facts.setdefault('_sources', {})
    added = []
    for key, value in mfacts.items():
        label = LABELS[key]
        if key in keep or label in facts:
            continue
        facts[label] = value
        sources[label] = SOURCE_MASTER
        added.append(label)
    return added, [n['text'] for n in notes]


def run_facts(form_path):
    """Dữ kiện mục 2 trong form nhập liệu của một lượt. Ô trống, số 0 và 'Có hồ bơi?' để trống là chưa có số."""
    wb = openpyxl.load_workbook(form_path, read_only=True, data_only=True)
    try:
        L = SheetLabels(wb['Project Info'])
        out = {}
        for key in FIELDS:
            label = fill_input.SCALARS[key][1]
            v = _clean(key, L.value(label)) if L.has(label) else None
            if v is not None:
                out[key] = v
        return out
    finally:
        wb.close()


def earlier_run(runs, name):
    """(run, facts) của lượt mới nhất cùng dự án có ít nhất một dữ kiện; (None, {}) nếu không có. `runs` theo
    history.scan: mới nhất trước."""
    key = fold(name)
    for run in runs:
        if not key or fold(run.get('project')) != key or not run.get('input_form'):
            continue
        try:
            facts = run_facts(run['input_form'])
        except Exception:      # noqa: BLE001 - form hỏng hay đang bị khoá: bỏ qua lượt đó
            continue
        if facts:
            return run, facts
    return None, {}


def info_facts(path):
    """Số chỗ đậu ô tô / xe máy trên sheet 0. Info của file ngân sách đã duyệt; {} khi không đọc được."""
    import review_import as ri
    tmp = tempfile.mkdtemp(prefix='facts_')
    wb = None
    try:
        wb, _ = ri.open_workbook(path, workdir=tmp)
        info = ri.read_info(wb)
        out = {'car_slots': _clean('car_slots', info.car_bays), 'moto_slots': _clean('moto_slots', info.moto_bays)}
        return {k: v for k, v in out.items() if v is not None}
    except Exception:          # noqa: BLE001 - file không đọc được: nguồn này không có gì
        return {}
    finally:
        if wb is not None:
            wb.close()
        shutil.rmtree(tmp, ignore_errors=True)


def merge(sources):
    """sources: [(source, label, facts)] theo thứ tự ưu tiên. Trả {key: dict(value, source, label, others)} với
    others = các nguồn sau có giá trị khác."""
    out = {}
    for key in FIELDS:
        found = [(s, label, facts[key]) for s, label, facts in sources if key in facts]
        if not found:
            continue
        s, label, value = found[0]
        others = [dict(source=s2, label=l2, value=v2) for s2, l2, v2 in found[1:] if _differs(key, v2, value)]
        out[key] = dict(value=value, source=s, label=label, others=others)
    return out


def _place(text):
    """Tên tỉnh / quận để so: các cách viết TP.HCM là một ('HCM', 'Ho Chi Minh City', 'TP. Hồ Chí Minh')."""
    import utility_tariffs as ut
    return ut.HCMC if ut.region_of(text) == ut.HCMC else fold(text)


def _differs(key, a, b):
    if key == 'city':
        return _place(a) != _place(b)
    if key == 'district':
        return fold(a) != fold(b)
    return a != b


def prefill(entry, runs, master_path=MASTER_CSV):
    """Dữ kiện mục 2 cho dòng kho `entry` (library.load()). Trả dict(fields, notes, run_id)."""
    name = entry.get('project') or ''
    run, rfacts = earlier_run(runs, name)
    ifacts = info_facts(entry['path']) if entry.get('path') else {}
    mfacts, notes = master_facts(name, master_path)
    run_label = ''
    if run:
        started = str(run.get('started') or '')
        day = f'{started[8:10]}/{started[5:7]}/{started[:4]}' if len(started) >= 10 else ''
        run_label = f'lượt trước {day}'.strip()
    fields = merge([(SRC_RUN, run_label, rfacts), (SRC_INFO, 'sheet 0. Info', ifacts),
                    (SRC_MASTER, 'danh sách master', mfacts)])
    return dict(fields=fields, notes=notes, run_id=run['id'] if run else None)
