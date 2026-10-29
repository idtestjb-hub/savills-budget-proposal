"""review_import.py on invented workbooks (change add-budget-renewal-mode, design D12). No real file, no real name."""
import datetime
import hashlib
import os
import shutil

import openpyxl
import pytest

import existing_staffing as es
import existing_utilities as eu
import review_import as ri
from input_labels import SheetLabels

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(os.path.dirname(HERE), 'verification', 'fixtures', 'Sample_Operating_Input.xlsx')   # has the operating fields
MONTHS = [datetime.datetime(2026, m, 1) for m in range(1, 13)]


def _fund_sheet(ws, layout, lines, vat_text='(Excluding VAT/ Chưa gồm thuế GTGT)', decoy=True):
    """A fund sheet with the form's conventions: code column, indicator to its left, R / E / PL1 / PL2 rows, a year
    column that ties, twelve month columns, a decoy 'approved' column that does not tie. `lines`: (section, code,
    indicator, annual, months or None, item)."""
    code_c, name_c, value_c, m0 = layout
    ws.cell(row=4, column=code_c, value=vat_text)
    ws.cell(row=5, column=name_c, value='Project Name:\nTên dự án:')
    ws.cell(row=5, column=name_c + 2, value='ZZ TEST TOWER')
    ws.cell(row=5, column=value_c, value='Budget Year:')
    ws.cell(row=5, column=value_c + 1, value=2026)
    ws.cell(row=6, column=name_c, value='Starting Month:')
    ws.cell(row=6, column=name_c + 2, value=datetime.datetime(2026, 1, 1))
    ws.cell(row=6, column=value_c, value='Ending Month:')
    ws.cell(row=6, column=value_c + 1, value=datetime.datetime(2026, 12, 31))
    ws.cell(row=9, column=code_c, value='CODE\nMã')
    ws.cell(row=9, column=name_c, value='ITEMS\nHạng mục')
    ws.cell(row=9, column=value_c, value='Estimate budget of Year 2026')
    ws.cell(row=10, column=value_c, value='Total Budget of Year\nTổng ngân sách')
    ws.cell(row=10, column=value_c + 1, value='Average Month')
    ws.cell(row=9, column=value_c + 4, value='Remarks\nGhi chú')
    if decoy:
        ws.cell(row=9, column=value_c - 2, value='Approved budget of Year 2025')
    for i, d in enumerate(MONTHS):
        ws.cell(row=10, column=m0 + i, value=d)
    r = 12
    totals = {'R': 0.0, 'E': 0.0}
    rows = {}
    ws.cell(row=r, column=code_c - 1, value='A')
    ws.cell(row=r, column=code_c, value='R')
    rows['R'] = r
    r += 1
    section = 'R'
    for sec, code, ind, annual, months, item in lines:
        if sec == 'E' and section == 'R':
            ws.cell(row=r, column=code_c - 1, value='B')
            ws.cell(row=r, column=code_c, value='E')
            rows['E'] = r
            r += 1
            section = 'E'
        ws.cell(row=r, column=code_c, value=code)
        ws.cell(row=r, column=name_c, value=item)
        if ind:
            ws.cell(row=r, column=code_c - 1, value=ind)
        if annual is not None:
            ws.cell(row=r, column=value_c, value=annual)
            if decoy:
                ws.cell(row=r, column=value_c - 2, value=annual * 0.9)
            if months is None:
                months = [annual / 12.0] * 12
            for i, v in enumerate(months):
                ws.cell(row=r, column=m0 + i, value=v)
            if not ind:
                totals[sec] += annual
        rows[code] = r
        r += 1
    ws.cell(row=r, column=code_c, value='PL1')
    ws.cell(row=r, column=value_c, value=totals['R'] - totals['E'])
    r += 1
    ws.cell(row=r, column=code_c, value='VAT')
    ws.cell(row=r, column=value_c, value=1000.0)
    r += 1
    ws.cell(row=r, column=code_c, value='PL2')
    r += 1
    for sec in ('R', 'E'):
        ws.cell(row=rows[sec], column=value_c, value=totals[sec])
        if decoy:
            ws.cell(row=rows[sec], column=value_c - 2, value=totals[sec] * 0.5)
    return rows, totals


MF_LINES = [
    ('R', 'RM', 'I.0', None, None, 'Management fee'),
    ('R', 'RM.AP', None, 2_400_000_000.0, None, 'Management fee of Apartment'),
    ('R', 'RM.OT', None, 0.0, None, 'Management fee of Officetel'),
    ('R', 'RP', 'I.1', None, None, 'Parking'),
    ('R', 'RP1', None, 120_000_000.0, None, 'Motorbike monthly parking'),
    ('R', 'RP2', None, 600_000_000.0, None, 'Car monthly parking'),
    ('R', 'RO2a', None, 12_000_000.0, None, 'Bank interest on Savills account'),
    ('E', 'EMH', 'I.1', None, None, 'Staff'),
    ('E', 'EMH2', None, 1_200_000_000.0, None, 'Staff cost'),
    ('E', 'EMH3', None, 30_000_000.0, None, 'Holiday duty'),
    ('E', 'EMH4', None, 0.0, None, 'Fire duty'),
    ('E', 'EEE', 'IV.2', None, None, 'Electricity'),
    ('E', 'EEE.C', None, 480_000_000.0, None, 'Electricity for common area'),
    ('E', 'EEW.C', None, 60_000_000.0, None, 'Water for common area'),
    ('E', 'ESS1', None, 900_000_000.0, [80_000_000.0] * 12, 'Security service'),   # months do not match
    ('E', 'ESA1', None, 5_000_000.0, None, 'Safe inspection for lifts'),            # not on the 2027 form
    ('E', 'ESM4', None, 24_000_000.0, None, 'Pool chemicals'),
]
CA_LINES = [
    ('R', 'RA1', None, 36_000_000.0, None, 'Advertising'),
    ('R', 'RP5', None, 24_000_000.0, None, 'Visitor parking'),
    ('R', 'RO2', None, 1_200_000.0, None, 'Bank interest'),
    ('E', 'EMH2', None, 100_000_000.0, None, 'Staff share'),
    ('E', 'EMH3', None, 2_000_000.0, None, 'Holiday share'),
    ('E', 'EEE.C', None, 40_000_000.0, None, 'Electricity share'),
    ('E', 'EEW.C', None, 4_000_000.0, None, 'Water share'),
    ('E', 'ESS1', None, 50_000_000.0, None, 'Security share'),
    ('E', 'ESS4', None, 30_000_000.0, None, 'Cleaning share'),
    ('E', 'EN1', None, 2_000_000.0, None, 'Bank fee'),
    ('E', 'EN2', None, 1_000_000.0, None, 'Audit'),
    ('E', 'ESM4', None, 3_000_000.0, None, 'Pool share'),
]
MF_LAYOUT = (25, 26, 37, 43)    # Y, Z, AK, AQ
CA_LAYOUT = (25, 26, 33, 38)    # Y, Z, AG, AL


def build_prior_workbook(path, with_ca=True, with_info=True):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Cover'
    if with_info:
        info = wb.create_sheet('0. Info')
        info['A1'] = 'INFORMATION OF ZZ Test Tower'
        for c, h in enumerate(['Hạng mục', 'GFA\n(m2)', 'NFA/ NSA\n(Diện tích thu phí)', 'Số sản phẩm', 'Số ô', 'Ghi chú',
                               '', 'Đơn giá phí áp dụng', 'Đơn vị tính'], start=1):
            info.cell(row=6, column=c, value=h)
        info.append(['Các loại hình sản phẩm thu phí quản lý', 0, 54_000, 500])
        info.append(['Apartment', None, 52_000, 480, None, None, None, 20_000, 'đ/ m2/ tháng'])
        info.append(['Shophouse', None, 2_000, 20, None, None, None, 25_000])
        info.append(['Office'])
        info.append(['Bãi xe'])
        info.append(['Bãi xe ô tô', None, 9_000, None, 2])
        info.append(['Bãi xe gắn máy', None, None, None, 1_500])
        info.append(['TỔNG CỘNG', 0, 54_000, 500])
    mf = wb.create_sheet('2. Budget-Management Fund')
    _, tot_mf = _fund_sheet(mf, MF_LAYOUT, MF_LINES)
    wb.create_sheet('2.1 Report-Management Fund')['A1'] = 'report'
    tot_ca = None
    if with_ca:
        ca = wb.create_sheet('2.2 Common area Fund')
        _, tot_ca = _fund_sheet(ca, CA_LAYOUT, CA_LINES)
    wb.save(path)
    return tot_mf, tot_ca


@pytest.fixture
def prior_path(tmp_path):
    p = os.path.join(tmp_path, 'approved_2026.xlsx')
    build_prior_workbook(p)
    return p


def test_reader_ties_and_reads_every_leaf(prior_path, tmp_path):
    prior = ri.read_prior_budget(prior_path, workdir=str(tmp_path))
    mf = prior.funds['MF']
    assert mf.value_how == 'reconciled'
    assert mf.vat_basis == 'excl'
    assert len(mf.month_cols) == 12 and mf.period[0] == (2026, 1) and mf.period[-1] == (2026, 12)
    for sec in ('R', 'E'):
        assert abs(mf.section_total(sec) - mf.anchors[sec]) <= 1.0
    codes = {l.code: l for l in mf.lines}
    assert 'RM' not in codes and 'EMH' not in codes          # group rows are not leaves
    assert codes['RM.AP'].annual == 2_400_000_000.0
    assert codes['RM.AP'].months == [200_000_000.0] * 12
    assert codes['RM.AP'].section == 'R' and codes['EMH2'].section == 'E'
    assert prior.budget_year == 2026
    assert prior.project_name == 'ZZ TEST TOWER'
    assert 'VAT' not in codes                                 # section D is not read


def test_decoy_column_is_not_the_year_column(prior_path, tmp_path):
    prior = ri.read_prior_budget(prior_path, workdir=str(tmp_path))
    assert prior.funds['MF'].value_col == 37                  # AK, not the 'Approved budget' decoy at AI


def test_months_that_do_not_match_are_flagged_and_year_column_kept(prior_path, tmp_path):
    prior = ri.read_prior_budget(prior_path, workdir=str(tmp_path))
    ess1 = next(l for l in prior.funds['MF'].lines if l.code == 'ESS1')
    assert ess1.annual == 900_000_000.0
    assert ri.FLAG_MONTHS in ess1.flags
    rp1 = next(l for l in prior.funds['MF'].lines if l.code == 'RP1')
    assert rp1.flags == []


def test_code_not_on_2027_form_is_kept_and_listed(prior_path, tmp_path):
    prior = ri.read_prior_budget(prior_path, workdir=str(tmp_path))
    esa1 = next(l for l in prior.funds['MF'].lines if l.code == 'ESA1')
    assert esa1.on_form is False and ri.FLAG_NOT_ON_FORM in esa1.flags
    assert any(k == ri.NOTE_NOT_ON_FORM and w == 'ESA1' for k, w, _ in prior.notes)
    assert abs(prior.funds['MF'].section_total('E') - prior.funds['MF'].anchors['E']) <= 1.0   # still in the total
    ro2a = next(l for l in prior.funds['MF'].lines if l.code == 'RO2a')
    assert ro2a.on_form is True                               # RO2a exists on the 2027 Management Fund sheet


def test_common_area_sheet_is_read_with_its_own_layout(prior_path, tmp_path):
    prior = ri.read_prior_budget(prior_path, workdir=str(tmp_path))
    ca = prior.funds['CA']
    assert ca.value_col == 33 and ca.month_cols[0] == 38
    assert abs(ca.section_total('E') - ca.anchors['E']) <= 1.0
    assert {l.code for l in ca.lines if l.section == 'R'} == {'RA1', 'RP5', 'RO2'}


def test_missing_common_area_sheet_is_a_note_not_a_stop(tmp_path):
    p = os.path.join(tmp_path, 'mf_only.xlsx')
    build_prior_workbook(p, with_ca=False)
    prior = ri.read_prior_budget(p, workdir=str(tmp_path))
    assert 'CA' not in prior.funds
    assert any(k == ri.NOTE_UNREAD and w == ri.FUND_SHEETS['CA'] for k, w, _ in prior.notes)


def test_pdf_and_xlsb_and_no_fund_sheet_are_refused(tmp_path):
    for name in ('budget.pdf', 'budget.xlsb'):
        p = os.path.join(tmp_path, name)
        open(p, 'wb').write(b'x')
        with pytest.raises(ri.PriorBudgetError) as exc:
            ri.read_prior_budget(p, workdir=str(tmp_path))
        assert name in str(exc.value)
    wb = openpyxl.Workbook()
    wb.active.title = 'Nothing'
    p = os.path.join(tmp_path, 'empty.xlsx')
    wb.save(p)
    with pytest.raises(ri.PriorBudgetError) as exc:
        ri.read_prior_budget(p, workdir=str(tmp_path))
    assert 'Management Fund' in str(exc.value)
    with pytest.raises(ri.PriorBudgetError):
        ri.read_prior_budget(os.path.join(tmp_path, 'absent.xlsx'), workdir=str(tmp_path))


def test_info_sheet_products_parking_and_name(prior_path, tmp_path):
    wb, _ = ri.open_workbook(prior_path, str(tmp_path))
    info = ri.read_info(wb)
    assert info.name == 'ZZ Test Tower'
    assert info.products['Apartment']['nfa'] == 52_000 and info.products['Apartment']['units'] == 480
    assert info.products['Apartment']['rate'] == 20_000
    assert info.products['Shophouse']['nfa'] == 2_000
    assert 'Office' not in info.products                      # a product row without a figure is not recorded
    assert info.moto_bays == 1_500 and info.car_bays == 2
    assert any(k == ri.NOTE_CHECK and w == 'Car Parking Slots' for k, w, _ in info.notes)


def test_info_sheet_missing_gives_a_note(tmp_path):
    p = os.path.join(tmp_path, 'no_info.xlsx')
    build_prior_workbook(p, with_info=False)
    wb, _ = ri.open_workbook(p, str(tmp_path))
    info = ri.read_info(wb)
    assert info.products == {} and info.notes and info.notes[0][0] == ri.NOTE_UNREAD


def test_template_codes_and_method_texts():
    codes = ri.template_codes()
    assert 'RM.AP' in codes['MF'] and 'EEE.C' in codes['MF'] and 'RP5' in codes['CA']
    assert 'ESA1' not in codes['MF']
    methods = ri.catalogue_methods()
    missing = sorted({m for m, _ in methods.values() if m and m not in ri.METHOD_VI})
    assert missing == [], f'catalogue methods without a Vietnamese text: {missing}'
    assert ri.method_vi('benchmark-by-comparable') == 'so sánh dự án tương đương'
    assert ri.no_vat('EMH2') and ri.no_vat('CIT1a') and ri.no_vat('RO2a') and not ri.no_vat('EEE.C')


def _sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def test_write_form_fills_existing_mode_and_reads_back(prior_path, tmp_path):
    prior = ri.read_prior_budget(prior_path, workdir=str(tmp_path))
    wb, _ = ri.open_workbook(prior_path, str(tmp_path))
    info = ri.read_info(wb)
    base = os.path.join(tmp_path, 'base.xlsx')
    shutil.copyfile(FIXTURE, base)
    before = _sha(base)
    facts = {'Tower Count': 3, 'Gate / Entrance Count': 2, 'Site Area': 9_000, '_sources': {'Tower Count': 'test'}}
    path, notes, filled = ri.write_form(prior, info, facts, os.path.join(tmp_path, 'out'), base_form=base)
    assert _sha(base) == before                                 # the named form is not changed
    assert os.path.basename(path).startswith('base_REVIEW_')
    wbv = openpyxl.load_workbook(path, data_only=True)
    L = SheetLabels(wbv['Project Info'])
    assert L.value('Project Name') == 'ZZ TEST TOWER'
    assert L.value('Project Mode') == es.MODE_EXISTING
    assert L.value('Prior Budget Year') == 2026
    if L.has('Budget Start Month'):                             # the standard fixture predates the field
        assert L.value('Budget Start Month') == datetime.datetime(2027, 1, 1)
    assert L.value('Tower Count') == 3 and L.value('Site Area') == 9_000
    assert L.value('Floor Count') == 0                          # numeric fact the file lacks: 0, listed
    assert L.value('Moto Parking Slots') == 1_500
    assert L.value('Stable Operation?') == 'Yes'
    assert L.value('Actual Car Parking Revenue') == 50_000_000  # RP2 600,000,000 / 12
    assert L.value('Actual Motorbike Parking Revenue') == 10_000_000
    assert filled['parking'] == {'car': 50_000_000, 'moto': 10_000_000}
    assert filled['rates']['Apartment'] == (20_000, 'excl. VAT')
    assert 'Floor Count' in filled['blank'] and 'Tower Count' in filled['facts']
    assert any(k == ri.NOTE_BLANK and w == 'Floor Count' for k, w, _ in notes)
    ex = es.read_existing(wbv, L)
    assert ex.lines['EMH2'].approved == 1_200_000_000.0 and ex.lines['EMH3'].approved == 30_000_000.0
    assert ex.roster == []
    ui = eu.read_utilities(wbv, L)
    assert ui.settings['EEE.C'].approved == 480_000_000.0 and ui.settings['EEE.C'].approved_incl_vat is False
    assert ui.settings['EEW.C'].approved == 60_000_000.0
    lines, notes_back = ri.read_prior_budget_sheet(wbv)
    by = {(l['fund'], l['code']): l for l in lines}
    assert len(lines) == len(list(prior.lines()))
    assert by[('2. Budget-Management Fund', 'RM.AP')]['approved'] == 2_400_000_000.0
    assert by[('2. Budget-Management Fund', 'RM.AP')]['months'] == [200_000_000.0] * 12
    assert by[('2. Budget-Management Fund', 'RM.AP')]['incl_vat'] is False
    assert ri.FLAG_MONTHS in by[('2. Budget-Management Fund', 'ESS1')]['flags']
    assert len(notes_back) == len(notes)


def test_fresh_form_is_built_in_the_work_folder_only(prior_path, tmp_path, monkeypatch):
    import build_project_input_form as bpf
    live = bpf.FINAL_OUT
    prior = ri.read_prior_budget(prior_path, workdir=str(tmp_path))
    wb, _ = ri.open_workbook(prior_path, str(tmp_path))
    info = ri.read_info(wb)
    stamp = _sha(live) if os.path.exists(live) else None
    path, notes, filled = ri.write_form(prior, info, {}, os.path.join(tmp_path, 'fresh'))
    assert os.path.exists(path) and os.path.dirname(path) == os.path.join(tmp_path, 'fresh')
    assert (_sha(live) if os.path.exists(live) else None) == stamp
    assert bpf.FINAL_OUT == live
    wbv = openpyxl.load_workbook(path, data_only=True)
    assert ri.SHEET in wbv.sheetnames and es.ROSTER_SHEET in wbv.sheetnames
    assert 'Tower Count' in filled['blank']


def test_a_workbook_read_through_its_repaired_copy_releases_the_source(tmp_path):
    """A defined name openpyxl refuses (`#N/A` print titles) sends the read to a repaired copy; the source file is
    released at once, not at garbage collection (on Windows a held file cannot be renamed or deleted)."""
    import zipfile
    good = os.path.join(tmp_path, 'good.xlsx')
    wb = openpyxl.Workbook()
    wb.active.title = 'Sheet A'
    wb.active['A1'] = 1
    wb.save(good)
    bad = os.path.join(tmp_path, 'bad.xlsx')
    with zipfile.ZipFile(good) as zin, zipfile.ZipFile(bad, 'w') as zout:
        for it in zin.infolist():
            b = zin.read(it.filename)
            if it.filename == 'xl/workbook.xml':
                b = b.replace(b'<definedNames/>', b'<definedNames><definedName name="_xlnm.Print_Titles" '
                                                  b'localSheetId="0">#N/A</definedName></definedNames>')
            zout.writestr(it, b)
    wb, used = ri.open_workbook(bad, str(tmp_path / 'work'))
    try:
        assert used.endswith('bad__repaired.xlsx')     # the first open failed on the defined name
        assert wb['Sheet A']['A1'].value == 1
        os.rename(bad, bad + '.moved')             # raises PermissionError on Windows while the source is held
    finally:
        wb.close()


# ---- change fix-review-reading-gaps ----
def _cell_of(ws, col, value):
    return next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=col).value == value)


def test_a_month_text_in_the_remarks_column_does_not_hide_the_twelve_months(prior_path, tmp_path):
    wb = openpyxl.load_workbook(prior_path)
    ws = wb['2. Budget-Management Fund']
    ws.cell(row=11, column=MF_LAYOUT[2] + 4, value='Dự kiến doanh thu năm 2026: số đến 12/2025')    # Remarks, rows 8-14
    wb.save(prior_path)
    mf = ri.read_prior_budget(prior_path, workdir=str(tmp_path)).funds['MF']
    assert len(mf.month_cols) == 12 and mf.period[0] == (2026, 1) and mf.period[-1] == (2026, 12)
    assert not any('cột tháng' in f for f in mf.flags)


def test_the_longest_run_is_taken_when_no_run_has_twelve_months(prior_path, tmp_path):
    wb = openpyxl.load_workbook(prior_path)
    ws = wb['2. Budget-Management Fund']
    ws.cell(row=10, column=MF_LAYOUT[3] + 11).value = None                      # December header gone: 11 months
    ws.cell(row=11, column=MF_LAYOUT[2] + 4, value='12/2025')
    wb.save(prior_path)
    mf = ri.read_prior_budget(prior_path, workdir=str(tmp_path)).funds['MF']
    assert len(mf.month_cols) == 11 and mf.period[0] == (2026, 1)
    assert 'tìm thấy 11 cột tháng thay vì 12' in mf.flags


def test_an_error_remark_becomes_a_reminder_text(prior_path, tmp_path):
    wb = openpyxl.load_workbook(prior_path)
    ws = wb['2.2 Common area Fund']
    ws.cell(row=_cell_of(ws, CA_LAYOUT[0], 'EN1'), column=CA_LAYOUT[2] + 4, value='#REF!')
    wb.save(prior_path)
    en1 = next(l for l in ri.read_prior_budget(prior_path, workdir=str(tmp_path)).funds['CA'].lines if l.code == 'EN1')
    assert en1.remark == '(ghi chú trong file gốc là ô lỗi #REF!)'


def test_a_staff_cost_sheet_is_never_the_management_fund():
    names = ['Cover', '1. Summary (N1) 100%', '2. Budget-M Fund (N1) 100%', '2.1. Staff cost From Savills',
             '2.1.1. Ca đêm Lễ Tết (năm 1)', '2. Budget-M Fund (N1) hv']
    with pytest.raises(ri.PriorBudgetError, match='no Management Fund budget sheet found'):
        ri.choose_fund_sheets(names)
    assert ri.choose_fund_sheets(names + ['2. Budget-Management Fund'])['MF'] == '2. Budget-Management Fund'
