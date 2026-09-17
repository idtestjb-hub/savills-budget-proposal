# One-time migration (change apply-guideline-remark-model, task 1) — run once, reviewed, not part
# of the pipeline. It reads the current Costing_Method_Catalogue.csv and rewrites it with:
#   1. two new columns   : summary_recipe, fixed_sentence
#   2. a '#' header block : the VAT-treatment sentence rule (VN + EN) + the switch cell
#   3. summary_recipe / fixed_sentence filled on the ~19 codes that map to a '1. Summary' PART-1 row
#   4. new rows for every 'AI GUIDELINE'-instructed code that had no catalogue entry
#
# The 67 original rows keep their code / method / inputs / remark_components untouched (only the two
# new trailing columns are added, empty). check_catalogue_drift.py still passes: every code here
# (old and new) is a real '2. Budget-Management Fund' / '3. Budget-Sinking Fund' code.
#
# Source of the instruction text: docs/AI Guideline - 2027 Resi Budget Form (IT team).xlsx column W
# (2. Budget-Management Fund) and column L (1. Summary), dumped 2026-09-10 to
# scratchpad/guideline_remarks.txt + scratchpad/guideline_summary.txt. This script does NOT read
# that workbook.
import csv
import io
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))  # -> Budget_Agent
CATALOGUE = os.path.join(_ROOT, 'data', 'master_list_verified', 'Costing_Method_Catalogue.csv')

OLD_COLS = ['code', 'item_en', 'item_vi', 'section', 'method', 'method_detail', 'inputs',
            'occupancy_scaled', 'remark_components', 'legal_citation', 'guideline_sheet',
            'exensive_logic', 'precedence_note']
NEW_COLS = OLD_COLS + ['summary_recipe', 'fixed_sentence']

# ---------------------------------------------------------------------------------------------------
# The '#' header block appended after the existing header comments. check_catalogue_drift.py and the
# catalogue readers skip every line that starts with '#'; check_remark_content (verify.py 5d) parses
# the VAT sentence back out of it.
VAT_HEADER = """\
# ---------------------------------------------------------------------------------------------------
# REMARK CONTENT MODEL (change apply-guideline-remark-model, 2026-09-10):
#   remark_components : ordered parts a code's line-level remark (2. Budget-Management Fund col T) must carry.
#   summary_recipe    : for a code that maps to a '1. Summary' PART-1 row, the ordered parts its composed
#                       client-facing col-K narrative must carry (';'-separated).
#   fixed_sentence    : a legal / standard sentence the narrative must include verbatim.
# VAT-TREATMENT SENTENCE RULE (AI Guideline, universal — applies to every cost and revenue remark):
#   vat_switch_sheet = 2. Budget-Management Fund
#   vat_switch_cell = F7
#   (data-validation list: KHOÁN | KHÔNG KHOÁN | THU HỘ CHI HỘ)
#   KHOÁN                       -> figures EXCLUDE VAT  -> no sentence added
#   KHÔNG KHOÁN | THU HỘ CHI HỘ -> figures INCLUDE VAT  -> every remark must end with, with <year> = budget year:
#   vat_sentence_vi = Chi phí đã bao gồm VAT và được dự ước tại năm <year>.
#   vat_sentence_en = This figure is inclusive of VAT and estimated for year <year>.
# ---------------------------------------------------------------------------------------------------
"""

# ---------------------------------------------------------------------------------------------------
# summary_recipe (and fixed_sentence) keyed by the catalogue `code` that owns each '1. Summary'
# PART-1 row. Security / Cleaning / Other-service rows have no dedicated summary code, so their
# recipe rides on the leaf-service code the pipeline fills (ESS1 / ESS4 / ESS16).
SUMMARY_RECIPES = {
    'RM': ("chargeable area by product (m2 apartment / shophouse / nursery) from 0. Info; "
           "applied management-fee rate by product (VND/m2/month) with its VAT status from 0. Info; "
           "the developer pre-collection assumption — the developer pays the fee on units not yet "
           "handed over, falling to zero as occupancy rises; reference to 'Ty le lap day cu dan'"),
    'RPa': ("assumption of ~2 motorbikes per apartment at the monthly motorbike rate from 0. Info; "
            "~7 monthly bicycles per 100 apartments at the bicycle rate from 0. Info; "
            "distributed by the parking fill-up curve; reference to 'Tien do lap day bai xe'"),
    'RO': "every RO* sub-item that carries a figure on '2. Budget-Management Fund', by name",
    'RI': ("operating expenses the management fund paid on behalf of the common-area fund; "
           "reference to '2.2 Common area Fund'"),
    'EMH': ("the Management Company overhead (brand, software, head-office support) sized to workload "
            "and to the reality of product handover; BQL headcount by project scale and segment, with "
            "the night-shift and public-holiday basis; reference to 'A1. Staff cost 08.2026 (VN)' for "
            "the staffing detail and to 'A5. Tro cap PCCC' for mandatory annual training"),
    'EMA': "every EMA* sub-item that carries a figure, by name",
    'EMB': "every EMB* sub-item that carries a figure, by name",
    'ESC': ("number of events with the names of the main events in an operating year; "
            "PCCC — a new project's year 1 carries both a plan-drafting fee and the annual drill fee; "
            "Christmas and Lunar New Year lobby decoration (cost per lobby x number of lobbies with a "
            "reception desk)"),
    'ESS1': ("total security posts (or total posts converted to 24h), broken out by role from the "
             "roster / 'A2. Bao ve - Security'; the 24h post unit rate"),
    'ESS4': ("total cleaning headcount and shift hours, broken out by role from the roster / "
             "'A3. Ve sinh - Cleaning'; the cleaner unit rate and any tea-lady / supervisor rate"),
    'ESS16': "every ES* service item other than security and cleaning that carries a figure, by name",
    'ESI1': ("asset risk insurance including compulsory fire and explosion cover (VND/year); "
             "public-liability insurance (VND/year)"),
    'ESM': "every ESM* sub-item that carries a figure, by name",
    'EN': ("the three capex groups — BQL office equipment, technical and PCCC tools, "
           "common-area / amenity equipment; that the cost is depreciated over the first 24 "
           "operating months"),
    'EEW': ("assumed common-area consumption in m3/month; the tariff with its build-up "
            "(base + VAT 5% + PBVMT 30% + VAT-on-PBVMT 8%); that the year-1 / year-2 figure follows "
            "the resident fill-up"),
    'EEE': ("assumed total consumption in kWh/month; the 2,226 VND/kWh tariff per QD 1279/QD-BCT "
            "09/05/2025 (duoi 6 kV, don vi hanh chinh su nghiep); that the year-1 / year-2 figure "
            "follows the fill-up curve, floored at ~40% of full load at zero occupancy and reaching "
            "full load by ~40% occupancy"),
    'EED': ("generator count and each unit's capacity (kVA); ~12 h/year no-load test plus ~8 h/year "
            "on-load backup (grid faults and transformer / main-LV-panel maintenance); the DO 0.005S "
            "Vung 1 listed diesel price on the budget date"),
    'ER': "every ER* sub-item that carries a figure, by name",
}
SUMMARY_FIXED = {
    # summary row 34 (Accreditation) — the recipe rides on E.S? no: it maps to ESA*/ESL* leaves.
    # ESA6 is the first ESA leaf that has a catalogue row after this migration; the composer applies
    # this sentence to the Accreditation narrative directly (see _SUMMARY_FIXED_SENTENCE there).
    'ESA-ACCREDITATION': ("Theo Dieu 150 Luat Nha o 2023 va Dieu 32 Quy che quan ly, su dung nha chung "
                          "cu, mot so chi phi kiem dinh khi van hanh co the su dung Quy bao tri."),
}

# ---------------------------------------------------------------------------------------------------
# New rows for every 'AI GUIDELINE'-instructed code with no catalogue entry. Terse: the instruction
# is captured in method_detail + remark_components. section/method reuse the catalogue's vocabulary.
_BENCHMARK = 'benchmark-by-comparable'
_BENCH_DETAIL = ("Guideline: price by benchmarking a comparable project of similar area "
                 "(\"lay benchmark theo du an tuong duong theo tan suat dien tich\").")
_BENCH_COMPONENTS = ("that the figure is benchmarked from a comparable project; which comparable and "
                     "the area-ratio basis")
_THU_HO = ("that the VPC (Savills) budget does not estimate pass-through / collect-on-behalf "
           "(\"thu ho\") revenue for this line")

NEW_ROWS = []


def _n(**k):
    r = {c: '' for c in NEW_COLS}
    r.update(k)
    NEW_ROWS.append(r)


# --- revenue: Others (RO*) ---
_n(code='RO1', item_en='Commission', item_vi='Hoa hong', section='revenue', method=_BENCHMARK,
   method_detail=_BENCH_DETAIL, remark_components=_BENCH_COMPONENTS,
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='RO2a', item_en='Bank interest on Savills account', item_vi='Lai tien gui tai khoan dung ten Savills',
   section='revenue', method=_BENCHMARK, method_detail=_BENCH_DETAIL, remark_components=_BENCH_COMPONENTS,
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered',
   precedence_note='Template ships this row as Half a Year with only one payment month filled — see change reconcile-summary-with-detail-sheets.')
_n(code='RO2b', item_en='Bank interest on BOC account', item_vi='Lai tien gui tai khoan dung ten Ban quan tri',
   section='revenue', method=_BENCHMARK, method_detail=_BENCH_DETAIL, remark_components=_BENCH_COMPONENTS,
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='RO3.A', item_en='Water fee of Apartment (collected on behalf)', item_vi='Tien nuoc thu tu can ho (thu ho)',
   section='revenue', method='not-estimated', method_detail='Guideline: the VPC budget does not estimate thu-ho revenue.',
   remark_components=_THU_HO, guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='RO4.A', item_en='Electricity fee of Apartment (collected on behalf)', item_vi='Tien dien thu tu can ho (thu ho)',
   section='revenue', method='not-estimated', method_detail='Guideline: the VPC budget does not estimate thu-ho revenue.',
   remark_components=_THU_HO, guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='RO5', item_en='Electricity fee of Developer / Contractors (collected on behalf)',
   item_vi='Tien dien thu tu CDT / nha thau (thu ho)', section='revenue', method='not-estimated',
   method_detail='Guideline: the VPC budget does not estimate thu-ho revenue.', remark_components=_THU_HO,
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='RO8', item_en='Laundry', item_vi='Giat ui', section='revenue', method='conditional-luxury-only',
   method_detail='Guideline: only luxury-grade projects estimate this revenue.',
   remark_components='that this revenue is estimated only for luxury-grade projects',
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='RO18', item_en='Others (revenue sub-item)', item_vi='Khac', section='revenue', method=_BENCHMARK,
   method_detail=_BENCH_DETAIL, remark_components=_BENCH_COMPONENTS,
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='RO23', item_en='Collect water bill from residents (on behalf)', item_vi='Thu ho tien nuoc sinh hoat tu cu dan',
   section='revenue', method='not-estimated', method_detail='Guideline: the VPC budget does not estimate thu-ho revenue.',
   remark_components=_THU_HO, guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='RM.OA2', item_en='Collect costs related to Fire Insurance', item_vi='Thu ho chi phi bao hiem chay no',
   section='revenue', method='mirror-of-ESI1',
   method_detail='Guideline: blank if the management fee already includes building insurance; otherwise equal to the figure entered at ESI1.',
   inputs='whether the management fee includes insurance; ESI1 figure', remark_components='whether the fee already covers insurance; if not, that this equals ESI1',
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='RI1', item_en='Collect operating expenses already paid for common-area fund',
   item_vi='Thu kinh phi van hanh da chi ho quy khai thac khu vuc chung', section='revenue',
   method='linked-from-common-area-fund', method_detail="Guideline: take the figure from cell AH40.",
   inputs="'2. Budget-Management Fund'!AH40", remark_components='that it is operating expense paid on behalf of the common-area fund; the source cell',
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')

# --- management expense: EMH4 ---
_n(code='EMH4', item_en='Staff related cost (mandatory annual training, allowances)',
   item_vi='Huan luyen bat buoc hang nam (ATLD, PCCC), phu cap truong/pho ban PCCC', section='management-expense',
   method='regulation-driven', method_detail="Mandatory annual ATLD / PCCC training and PCCC officer allowances; see sheet 'A5. Tro cap PCCC'.",
   inputs="'A5. Tro cap PCCC' sheet", remark_components='headcount trained; that ATLD/PCCC training is a legal requirement; the PCCC officer allowance basis',
   legal_citation='NĐ 105/2025/NĐ-CP (annual mandatory ATLĐ / PCCC training)',
   guideline_sheet="2. Budget-Management Fund; A5. Trợ cấp PCCC", exensive_logic='agrees')

# --- management expense: EMA1..EMA19 (benchmark, with two specific ones) ---
_n(code='EMA1', item_en='Telephone & internet fee', item_vi='Chi phi dien thoai va internet', section='management-expense',
   method='benchmark-or-package', method_detail='Guideline: benchmark, or estimate from an FPT business internet package plus a hotline subscription (~500,000 VND/month).',
   remark_components='the internet package basis; the ~500k/month hotline subscription',
   guideline_sheet='2. Budget-Management Fund', exensive_logic='differs')
_n(code='EMA7', item_en='Drinking water', item_vi='Chi phi nuoc uong', section='management-expense',
   method='headcount-x-consumption', method_detail='BQL headcount x 1 L/person/day; 19 L bottle at 60,000 VND incl VAT; covers BQL and resident-reception water.',
   inputs='BQL headcount; 1 L/person/day; 60,000 VND per 19 L bottle incl VAT', occupancy_scaled='',
   remark_components='BQL headcount; 1 L/person/day; 60,000 VND per 19 L bottle incl VAT; that it covers BQL and reception',
   guideline_sheet='2. Budget-Management Fund', exensive_logic='differs')
for _c, _en, _vi in [
    ('EMA2', 'Stationery', 'Chi phi van phong pham'),
    ('EMA3', 'Printing ink', 'Muc in'),
    ('EMA4', 'Photocopy rental', 'Thue may photocopy'),
    ('EMA5', 'Printing (accounting books, receipts)', 'Phi in an'),
    ('EMA6', 'Postage service', 'Chi phi gui thu (EMS)'),
    ('EMA8', 'Taxi coupon / employee parking', 'Chi phi taxi cong viec / phi gui xe nhan vien'),
    ('EMA9', 'Office equipment maintenance', 'Bao tri trang thiet bi van phong BQL'),
    ('EMA11', 'Building management software', 'Phan mem quan ly toa nha'),
    ('EMA12', 'SMS', 'Chi phi tin nhan SMS'),
    ('EMA14', 'Necessities for MO / night-shift staff', 'Nhu yeu pham cho van phong BQL / nhan vien truc dem'),
    ('EMA17', 'Local authority security contribution', 'Dong quy an ninh phuong'),
    ('EMA19', 'E-invoice', 'Chi phi hoa don dien tu'),
]:
    _n(code=_c, item_en=_en, item_vi=_vi, section='management-expense', method=_BENCHMARK,
       method_detail=_BENCH_DETAIL, remark_components=_BENCH_COMPONENTS,
       guideline_sheet='2. Budget-Management Fund', exensive_logic='differs')
_n(code='EMA15', item_en='Others (Administrative Expense catch-all)', item_vi='Khac', section='management-expense',
   method='section-catch-all',
   method_detail='The pipeline writes one blended per-m2 ratio for the whole EMA section on this leaf row; no data says how it splits across EMA1..EMA19.',
   remark_components='that it is the EMA section catch-all — one blended ratio, not a per-line breakdown',
   guideline_sheet='2. Budget-Management Fund', exensive_logic='differs')

# --- management expense: EMB1..EMB5 (benchmark) ---
for _c, _en, _vi, _sheet in [
    ('EMB1', 'Bank transaction fees', 'Phi giao dich ngan hang', '3. Budget-Sinking Fund'),
    ('EMB2', 'Cash collection', 'Phi ngan hang thu tien tai cho', '2. Budget-Management Fund'),
    ('EMB3', 'Consultancy fee', 'Chi phi tu van', '2. Budget-Management Fund'),
    ('EMB4', 'Operation auditing fee', 'Chi phi kiem toan van hanh', '2. Budget-Management Fund'),
    ('EMB5', 'Energy auditing fee', 'Chi phi kiem toan nang luong', '2. Budget-Management Fund'),
]:
    _n(code=_c, item_en=_en, item_vi=_vi, section='management-expense', method=_BENCHMARK,
       method_detail=_BENCH_DETAIL, remark_components=_BENCH_COMPONENTS,
       guideline_sheet=_sheet, exensive_logic='differs')

# --- management expense: EMO1..EMO10 (owners board — mostly year-2+, project-specific) ---
_n(code='EMO1', item_en='Salary subsidies for owners board (BOC)', item_vi='Phu cap luong cho Ban quan tri',
   section='management-expense', method='formula-from-year-2',
   method_detail='Usually zero in year 1. From year 2: project < 500 units -> 3 BOC members; >= 500 units -> 5 members. Member pay = 1 regional minimum wage; chair = 1.5x.',
   inputs='unit count; regional minimum wage', remark_components='that year 1 is usually zero; member count by project size; that pay is 1 (chair 1.5) regional minimum wage',
   legal_citation='statutory minimum wage by region', guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='EMO2', item_en='Training for owners board (BOC)', item_vi='Tap huan nghiep vu cho Ban quan tri',
   section='management-expense', method='estimate-or-benchmark',
   method_detail='Usually zero in year 1; estimated only once EMO1 exists. ~3-5 million VND/year, or benchmark from a comparable.',
   remark_components='that it depends on EMO1; the ~3-5 million VND/year basis',
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
for _c, _en, _vi in [
    ('EMO3', 'Access card printing', 'In an the tu'),
    ('EMO4', 'Parking card printing', 'In an the xe'),
    ('EMO5', 'Swimming wristband', 'Vong tay ho boi'),
]:
    _n(code=_c, item_en=_en, item_vi=_vi, section='management-expense', method='not-estimated',
       method_detail='Guideline: not estimated ("khong du uoc chi phi").',
       remark_components='that the guideline does not estimate this cost',
       guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
for _c, _en, _vi in [
    ('EMO9', 'Operating expense to maintain certification (WELL, ...)', 'Chi phi van hanh lien quan chung nhan (WELL...)'),
    ('EMO10', 'Certification renewal (WELL, ...)', 'Chi phi gia han giay chung nhan toa nha (WELL...)'),
]:
    _n(code=_c, item_en=_en, item_vi=_vi, section='management-expense', method='manual-per-project',
       method_detail='Guideline: adjusted manually per project ("hieu chinh thu cong sau").',
       remark_components='that this is set manually per project',
       guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')

# --- service / M&E / accreditation ---
_n(code='ESM25', item_en='Cross-check of wastewater-treatment water quality', item_vi='Kiem tra cheo chat luong nuoc he XLNT',
   section='management-expense', method='frequency-x-unit-cost',
   method_detail='Estimated once per quarter at ~3,500,000 VND/occurrence (per SCE), excl VAT — a cross-check of the STP contractor\'s treated-water quality.',
   inputs='4 occurrences/year; ~3,500,000 VND each excl VAT', remark_components='quarterly frequency; ~3.5 million VND/occurrence excl VAT (per SCE); that it cross-checks the STP contractor',
   guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
_n(code='ESA6', item_en='Safety inspection for passenger up-lifts', item_vi='Kiem dinh an toan thang nang nguoi',
   section='sinking-fund', method='fund-allocation-rule',
   method_detail='Guideline: use the sinking fund if the equipment was bought with the sinking fund, the operating fund if bought with the operating fund; if the purchasing fund is unknown, use the sinking fund when the equipment is fixed to the building, otherwise the operating fund.',
   remark_components='which fund pays and why (how the equipment was bought / whether it is fixed to the building)',
   guideline_sheet='3. Budget-Sinking Fund', exensive_logic='not-covered')
for _c, _en, _vi in [
    ('ESA11', 'Safety inspection for air compressor', 'Kiem dinh an toan may bom hoi'),
    ('ESA12', 'Inspection & registration for electric car', 'Dang kiem xe o to dien'),
]:
    _n(code=_c, item_en=_en, item_vi=_vi, section='sinking-fund', method='fund-allocation-rule',
       method_detail='Guideline: sinking fund if bought with the sinking fund, otherwise the operating fund.',
       remark_components='which fund pays and why', guideline_sheet='3. Budget-Sinking Fund', exensive_logic='not-covered')
_n(code='ESA16', item_en='Safety inspection for water meter', item_vi='Kiem dinh dong ho nuoc',
   section='sinking-fund', method='fund-allocation-rule',
   method_detail='Guideline: use the sinking fund if the water meter is common property; do not use the sinking fund if it is privately owned.',
   remark_components='whether the meter is common or private property; which fund pays',
   guideline_sheet='3. Budget-Sinking Fund', exensive_logic='not-covered')


# =================================================================================================
def main():
    with open(CATALOGUE, encoding='utf-8-sig') as f:
        raw = f.read()
    lines = raw.splitlines()
    header_comments = [ln for ln in lines if ln.startswith('#')]
    body = '\n'.join(ln for ln in lines if not ln.startswith('#'))
    rows = list(csv.DictReader(io.StringIO(body)))
    assert [c for c in rows[0].keys()] == OLD_COLS, rows[0].keys()
    existing_codes = {r['code'] for r in rows}

    # 1. new columns on the existing rows (empty)
    for r in rows:
        r.setdefault('summary_recipe', '')
        r.setdefault('fixed_sentence', '')

    # 2. fill summary_recipe / fixed_sentence on codes that own a '1. Summary' PART-1 row
    by_code = {r['code']: r for r in rows}
    for code, recipe in SUMMARY_RECIPES.items():
        if code in by_code:
            by_code[code]['summary_recipe'] = recipe

    # 3. append the new instructed-code rows (skip any that already exist)
    added = [r for r in NEW_ROWS if r['code'] not in existing_codes]
    dup = [r['code'] for r in NEW_ROWS if r['code'] in existing_codes]
    if dup:
        print('skipped (already present):', dup)
    # ESA6 owns the Accreditation ('1. Summary' row 34) recipe — first ESA leaf with a catalogue row
    for r in added:
        if r['code'] == 'ESA6':
            r['summary_recipe'] = 'every ESA* / ESL* accreditation sub-item that carries a figure, by name'
            r['fixed_sentence'] = SUMMARY_FIXED['ESA-ACCREDITATION']
    out_rows = rows + added

    # 4. write back: original '#' comments + the VAT header block + CSV
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=NEW_COLS, lineterminator='\n')
    w.writeheader()
    for r in out_rows:
        w.writerow({c: r.get(c, '') for c in NEW_COLS})

    with open(CATALOGUE, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(header_comments) + '\n')
        f.write(VAT_HEADER)
        f.write(buf.getvalue())

    print(f'catalogue rows: {len(rows)} -> {len(out_rows)}  (+{len(added)})')
    print(f'summary_recipe filled on: {sorted(c for c in SUMMARY_RECIPES if c in by_code)}')
    print(f'summary codes with no catalogue row (recipe applied in the composer directly): '
          f'{sorted(c for c in SUMMARY_RECIPES if c not in by_code)}')


if __name__ == '__main__':
    main()
