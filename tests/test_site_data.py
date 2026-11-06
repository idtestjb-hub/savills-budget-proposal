"""site_data.py: the trimmed, anonymised reference data of a site package (change site-data-isolation). Invented names;
the real data folder is only checked for the presence of the KEEP files."""
import csv
import os

import openpyxl
import pytest

import site_data as sd


def _csv(path, header, rows, comments=()):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        fh.writelines(comments)
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(header)
        w.writerows(rows)


def _read(path):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        lines = [l for l in fh.read().splitlines() if not l.startswith('#')]
    return list(csv.reader(lines))


@pytest.fixture
def data(tmp_path):
    src = tmp_path / 'data'
    # Only the masked files carry invented rows; the plain reference files are one-line stand-ins.
    _csv(str(src / 'master_list_verified' / 'Dim_Property_Residential.csv'),
         ['PropertyType', 'SourceRow', 'No', 'Name', 'Address_Raw', 'Street', 'District', 'City_Province', 'NFA_m2', 'NFA_raw', 'MgmtFeeRate_Primary'],
         [['Residential', '5', '1', 'Tháp Mây Xanh', '12 Đường Lớn', 'Đường Lớn', 'Quận 1', 'Hồ Chí Minh', '50000', '50,000 (ước)', '15000'],
          ['Residential', '6', '2', 'KHU THU NGHIEM', '7 Ngõ Nhỏ', 'Ngõ Nhỏ', 'Quận 2', 'Hồ Chí Minh', '36680', '36680', '12000'],
          ['Residential', '7', '3', 'A&K Tower', '9 Phố', 'Phố', 'Quận 1', 'Hồ Chí Minh', '64124', '64124', '18000'],
          ['Residential', '8', '4', 'Biệt Thự Sông', '', '', 'Thủ Đức', 'Hồ Chí Minh', '20000', '', '']])
    _csv(str(src / 'master_list_verified' / 'Fact_ProjectLocation.csv'),
         ['asset_name', 'property_type', 'new_ward', 'new_province_city', 'latitude', 'longitude'],
         [['Tháp Mây Xanh', 'Residential', 'Bến Nghé', 'Ho Chi Minh City', '10.77', '106.70'],
          ['Văn Phòng Đỏ', 'Commercial', 'Bến Thành', 'Ho Chi Minh City', '10.78', '106.69']],
         comments=['# Real property locations, source: docs/ProjectLocation.xlsx\n'])
    _csv(str(src / 'generation_A_star_schema' / 'Fact_CapexReserve.csv'),
         ['ObservationType', 'Project', 'Year1Sheet', 'ImpliedRateAnnualised', 'SourceFile'],
         [['reserve', '202602 - Budget Tháp Mây Xanh', '2a.Budget-MF', '0.11', '202602 - Budget Tháp Mây Xanh.xlsx']])
    _csv(str(src / 'generation_A_star_schema' / 'Fact_OPEX.csv'),
         ['Project', 'Category', 'MonthlyVND', 'Source', 'PriceAsOf', 'RefKey'],
         [['A&K Tower', 'Electricity', '262210141', 'D3a sheet', '~2020 (AK Tower budget)', 'R02'],
          ['Bãi Xe Thử', 'Water', '100', 'D2 sheet', '2026-01-01', 'R08']])
    _csv(str(src / 'master_list_verified' / 'Ref_ComparableVATBasis.csv'),
         ['project_key', 'product', 'basis', 'source_text', 'checked_on', 'RefKey'],
         [['A&K Tower', 'Apartment', 'excl', 'Hand-verified', '2026-10-18', 'R02']])
    _csv(str(src / 'master_list_verified' / 'Dim_Property_Commercial.csv'), ['PropertyType', 'Name'],
         [['Commercial', 'Văn Phòng Đỏ'], ['Commercial', 'AIG']])
    # Reference-project registry: the utilities base is spelled two ways across the files ('A&K Tower' in the master
    # list, OPEX and VAT files; 'AK Tower' as an alias) and must get ONE pseudonym (change reference-projects-by-key).
    _csv(str(src / 'master_list_verified' / 'Dim_ReferenceProject.csv'),
         ['RefKey', 'DisplayName', 'Aliases', 'TotalNFA_m2', 'CapexNFA_m2', 'ApartmentUnits', 'TotalUnits',
          'MgmtRate_VND_m2_month', 'MgmtRateVAT', 'District', 'City', 'Comparable', 'ExcludedFromRanking', 'Roles',
          'Source', 'LocationSource', 'VerifiedOn'],
         [['R02', 'A&K Tower', 'AK Tower', '64124', '64124', '1155', '1162', '', '', 'Quận 1', 'Hồ Chí Minh', '1', '',
           'utilities_base|capex_items', 'Info sheet of A&K Tower', 'Street of A&K Tower, verified', '2026-09-17'],
          ['R08', 'Bãi Xe Thử', '', '', '', '0', '0', '', '', '', '', '0', 'no apartments', 'parking_base', 'src', '', '2026-09-17']],
         comments=['# Reference-project registry (test)\n'])
    for rel in sd.KEEP:
        p = src.joinpath(*rel.split('/'))
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('a,b\n1,2\n', encoding='utf-8')
    return src


def test_keep_files_exist_in_the_real_data_folder():
    missing = [rel for rel in sd.KEEP if not os.path.isfile(os.path.join(sd.DATA_DIR, *rel.split('/')))]
    assert missing == []


def test_build_copies_only_keep_files_and_masks_names_consistently(data, tmp_path):
    dst = tmp_path / 'pkg_data'
    out = sd.build(str(data), str(dst), own_names=['Khu Thu Nghiem'])
    assert sorted(out['copied']) == sorted(sd.KEEP)
    walked = sorted(os.path.relpath(os.path.join(d, f), dst).replace(os.sep, '/') for d, _, fs in os.walk(dst) for f in fs)
    assert walked == sorted(sd.KEEP)                                     # Dim_Property_Commercial.csv is not in the package
    res = _read(str(dst / 'master_list_verified' / 'Dim_Property_Residential.csv'))
    head, rows = res[0], res[1:]
    by = {r[head.index('Name')]: r for r in rows}
    assert 'Tháp Mây Xanh' not in by and 'Biệt Thự Sông' not in by
    assert 'KHU THU NGHIEM' in by and 'A&K Tower' not in by               # own project kept, the reference budget masked
    ak = out['pseudonyms'][sd.norm('A&K Tower')]
    assert ak == out['pseudonyms'][sd.norm('AK Tower')] == 'Dự án tham chiếu 01'   # one code for both spellings, assigned first
    assert by[ak][head.index('NFA_m2')] == '64124' and by[ak][head.index('Address_Raw')] == ''
    p1 = next(n for n in by if n.startswith('Dự án tham chiếu') and n != ak)
    r = by[p1]
    assert r[head.index('Address_Raw')] == '' and r[head.index('Street')] == '' and r[head.index('NFA_raw')] == ''
    assert r[head.index('NFA_m2')] in ('50000', '20000') and r[head.index('District')] in ('Quận 1', 'Thủ Đức')
    reg = _read(str(dst / 'master_list_verified' / 'Dim_ReferenceProject.csv'))
    rh, rrows = reg[0], {r[0]: r for r in reg[1:]}
    assert rrows['R02'][rh.index('DisplayName')] == ak and rrows['R02'][rh.index('Aliases')] == ''
    assert rrows['R02'][rh.index('Source')] == '' and rrows['R02'][rh.index('LocationSource')] == ''
    assert rrows['R02'][rh.index('TotalNFA_m2')] == '64124' and rrows['R02'][rh.index('Roles')] == 'utilities_base|capex_items'
    assert rrows['R08'][rh.index('DisplayName')].startswith('Dự án tham chiếu')
    loc = _read(str(dst / 'master_list_verified' / 'Fact_ProjectLocation.csv'))
    names = {r[0] for r in loc[1:]}
    assert out['pseudonyms'][sd.norm('Tháp Mây Xanh')] in names        # same code in both files
    assert 'Văn Phòng Đỏ' not in names and loc[1][4] == '10.77'          # coordinates kept, name masked
    with open(dst / 'master_list_verified' / 'Fact_ProjectLocation.csv', encoding='utf-8-sig') as fh:
        first = fh.readline()
    assert first.startswith('# Bản rút gọn')                              # office comment line replaced
    capex = _read(str(dst / 'generation_A_star_schema' / 'Fact_CapexReserve.csv'))
    assert capex[1][1].startswith('Dự án tham chiếu') and capex[1][4] == '' and capex[1][3] == '0.11'
    opex = _read(str(dst / 'generation_A_star_schema' / 'Fact_OPEX.csv'))
    assert opex[1][0] == ak and opex[2][0] == rrows['R08'][rh.index('DisplayName')] and opex[1][3] == ''
    assert opex[1][4] == f'~2020 ({ak} budget)' and opex[2][4] == '2026-01-01'   # name inside a text column replaced
    vat = _read(str(dst / 'master_list_verified' / 'Ref_ComparableVATBasis.csv'))
    assert vat[1][0] == ak and vat[1][3] == 'Hand-verified'               # the validator needs source_text


def test_leak_words_and_find_leaks(data, tmp_path):
    store = tmp_path / 'store'
    _csv(str(store / 'dim_file.csv'), ['file_id', 'file_name'], [['abc', 'Budget 2026 Sao Mai_rv1.xlsx'], ['def', 'Budget 2026 Khu Thu Nghiem.xlsx'], ['ghi', 'NGÂN SÁCH NĂM 2026 (final).xlsx']])
    words = sd.leak_words(str(data), own_names=['Khu Thu Nghiem'], store_dir=str(store))
    assert 'Tháp Mây Xanh' in words and 'Văn Phòng Đỏ' in words and 'Biệt Thự Sông' in words
    assert 'Budget 2026 Sao Mai_rv1' in words
    assert 'A&K Tower' in words and 'AK Tower' in words and 'Bãi Xe Thử' in words      # registry names and aliases
    assert 'KHU THU NGHIEM' not in words and 'AIG' not in words                        # own, too short
    assert 'Budget 2026 Khu Thu Nghiem' not in words                                        # own file name in the store
    assert 'NGÂN SÁCH NĂM 2026 (final)' not in words                                        # generic title, no project name
    pkg = tmp_path / 'pkg'
    (pkg / 'python').mkdir(parents=True)
    (pkg / 'python' / 'x.py').write_text('Tháp Mây Xanh', encoding='utf-8')          # runtime is not scanned
    (pkg / 'app').mkdir()
    (pkg / 'app' / 'ok.csv').write_text('Dự án tham chiếu 01,50000\n', encoding='utf-8')
    (pkg / 'app' / 'bad.txt').write_text('ghi chú về tháp mây xanh', encoding='utf-8')
    wb = openpyxl.Workbook()
    wb.active['A1'] = 'Văn Phòng Đỏ'
    wb.save(pkg / 'app' / 'bad.xlsx')
    hits = dict(sd.find_leaks(str(pkg), words))
    assert set(hits) == {os.path.join('app', 'bad.txt'), os.path.join('app', 'bad.xlsx')}
    assert hits[os.path.join('app', 'bad.txt')] == ['Tháp Mây Xanh']


def test_pseudonyms_are_stable_per_name():
    p = sd.Pseudonyms(keep=['Khu Thu Nghiem'])
    assert p('Tháp A') == 'Dự án tham chiếu 01' and p(' tháp a ') == 'Dự án tham chiếu 01'
    assert p('Tháp B') == 'Dự án tham chiếu 02' and p('KHU THU NGHIEM') == 'KHU THU NGHIEM' and p('') == ''


def test_pseudonyms_group_the_name_variants_of_one_reference_project():
    # rule source: spec budget-site-package, scenario "Own project and coded names" (one code per key, registry first)
    grouped = {sd.norm('A&K Tower'): 'R02', sd.norm('AK Tower'): 'R02', sd.norm('Bãi Xe Thử'): 'R08',
               sd.norm('Khu Thu Nghiem'): 'R09'}
    p = sd.Pseudonyms(keep=['Khu Thu Nghiem'], grouped=grouped)
    assert p('A&K Tower') == p('ak tower') == 'Dự án tham chiếu 01'
    assert p('Bãi Xe Thử') == 'Dự án tham chiếu 02'
    assert p('Khu Thu Nghiem') == 'Khu Thu Nghiem'                     # own project wins over its registry group
    assert p('Tháp Mới') == 'Dự án tham chiếu 03'                      # other names continue the numbering
