# One-time extraction record (design.md D2 — manual, reviewed once, not part of the pipeline).
#
# The AI GUIDELINE instruction text was dumped per code into extraction_worksheet.csv (see task 1.2),
# then a human turned each prose instruction into the structured rows below. This script is that
# hand-authored result; it does NOT read the guideline workbook. Re-run it to regenerate
#   data/master_list_verified/Costing_Method_Catalogue.csv
# after editing the rows here. When Savills revises the template, re-dump extraction_worksheet.csv,
# revise these rows, and run check_catalogue_drift.py.
import csv, os

# .../Budget_Agent/source_code/openspec/changes/adopt-guideline-as-costing-method-spec/ -> Budget_Agent
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
OUT = os.path.join(_ROOT, 'data', 'master_list_verified', 'Costing_Method_Catalogue.csv')

SOURCE_FILE = 'AI Guideline - 2027 Resi Budget Form (IT team) .xlsx'
SOURCE_VERSION = 'Phiên bản Số 01, tháng 08/2026 (Cover!F11); received in docs/ 2026-09-09; 25 sheets, 492 budget-line codes'

COLS = ['code', 'item_en', 'item_vi', 'section', 'method', 'method_detail', 'inputs',
        'occupancy_scaled', 'remark_components', 'legal_citation', 'guideline_sheet',
        'exensive_logic', 'precedence_note']

# section: revenue | management-expense | energy | repairs | sinking-fund | tax | nav
R = []

def row(**k):
    R.append({c: k.get(c, '') for c in COLS})

# ---------- navigation / section parents (method left blank; nav only) ----------
row(code='R', item_en='OPERATING FEES COLLECTION', item_vi='THU KINH PHÍ VẬN HÀNH',
    section='nav', method='section-total', method_detail='Template SUBTOTAL of RM..RI. Not written by the pipeline.',
    guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
row(code='E', item_en='MANAGEMENT EXPENSES', item_vi='CHI KINH PHÍ VẬN HÀNH',
    section='nav', method='section-total', method_detail='Template SUBTOTAL of EM..ESP. Not written by the pipeline.',
    guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')

# ---------- 2.1  REVENUE ----------
row(code='RM', item_en='Management fee', item_vi='Phí quản lý', section='revenue',
    method='area-x-rate', occupancy_scaled='yes',
    method_detail='Sum of the per-product rows RM.AP..RM.KG. Each product = fee area (0. Info col D) x '
      'applied rate (0. Info col I). For a project not yet at stable occupancy the monthly figure follows '
      'the resident fill-up curve (sheet "Tỷ lệ lấp đầy cư dân"), entered month by month via Schedule.',
    inputs='0. Info!D per product (fee area m2); 0. Info!I per product (VND/m2/month); F7 VAT model; resident fill-up curve',
    remark_components='fee area per product from 0. Info; applied rate per product from 0. Info (state VND/m2/month and VAT); months of management fee the developer prepays / pays on un-handed-over units; reference to "Tiến độ lấp đầy cư dân"',
    legal_citation='', guideline_sheet='1. Summary; 0. Info; 2. Budget-Management Fund',
    exensive_logic='not-covered', precedence_note='EXENSIVE LOGIC.xlsx covers management expenses only, not revenue codes.')
for c, en, vi in [
    ('RM.AP', 'Management fee of Apartment', 'Phí quản lý thu từ Căn hộ'),
    ('RM.OT', 'Management fee of Officetel', 'Phí quản lý thu từ Officetel'),
    ('RM.OF', 'Management fee of Office', 'Phí quản lý thu từ Office'),
    ('RM.SM', 'Management fee of Shopping Mall', 'Phí quản lý thu từ Thương mại'),
    ('RM.RE', 'Management fee of Retail', 'Phí quản lý thu từ Retail'),
    ('RM.SA', 'Management fee of Shop Apartment', 'Phí quản lý thu từ Shop Apartment'),
    ('RM.SH', 'Management fee of Shophouse', 'Phí quản lý hàng tháng từ nhà phố'),
    ('RM.VI', 'Management fee of Villas', 'Phí quản lý thu từ Biệt Thự'),
    ('RM.KG', 'Management fee of Kindergarten', 'Phí quản lý thu từ Nhà trẻ'),
]:
    row(code=c, item_en=en, item_vi=vi, section='revenue', method='area-x-rate', occupancy_scaled='yes',
        method_detail='Fee area (0. Info!D for this product) x applied rate (0. Info!I). New project: month by month off the resident fill-up curve via Schedule.',
        inputs='0. Info!D (fee area m2); 0. Info!I (VND/m2/month); F7 VAT model; resident fill-up curve',
        remark_components='fee area from 0. Info; rate from 0. Info with VAT status; fill-up basis',
        guideline_sheet='0. Info', exensive_logic='not-covered')
row(code='RM.0A', item_en='Management fee of Other Area', item_vi='Phí quản lý loại hình khác / CĐT đóng căn chưa bàn giao',
    section='revenue', method='developer-covers-unlet', occupancy_scaled='yes',
    method_detail='The developer pays management fee on units not yet handed over. Mirror of the fill-up curve: '
      '(100% - occupancy%) x total units x rate, month by month. Left blank until the occupancy ramp exists (D8).',
    inputs='total units (0. Info!E); rate (0. Info!I); resident fill-up curve',
    remark_components='units not handed over per month; rate; that the figure falls as occupancy rises',
    guideline_sheet='0. Info; Tỷ lệ lấp đầy cư dân', exensive_logic='not-covered',
    precedence_note='Method taken from the worked sample "Ngân sách mẫu ... tiền khai trương" (row RM.0A); guideline column itself is blank for this code.')
row(code='RM.PA', item_en='Management fee of Parking', item_vi='Phí quản lý các chỗ đậu xe',
    section='revenue', method='area-x-rate', occupancy_scaled='yes',
    method_detail='Only used when the developer keeps and self-operates the car park (0. Info row 15, case C): the monthly '
      'management fee at 0. Info!K12 goes here instead of parking usage revenue. Needs a parking area in m2 and a rate. '
      'Blank until parking area is captured (see change fix-parking-allocation-divide-by-zero).',
    inputs='0. Info!D12 (parking area m2); 0. Info!I (rate); parking ownership scenario',
    remark_components='parking area; rate; that this is the self-operated-car-park scenario',
    guideline_sheet='0. Info', exensive_logic='not-covered')
row(code='RPa', item_en='Monthly parking revenue', item_vi='Nguồn thu xe tháng', section='revenue',
    method='bays-x-fill-x-rate', occupancy_scaled='yes',
    method_detail='Sum of RP1 (motorbike), RP2 (car), RP3 (bicycle) etc. Each = bays x parking fill % x monthly rate, month by month '
      'off "Tiến độ lấp đầy bãi xe", via Schedule.',
    inputs='0. Info!F (bays per type); 0. Info!I (VND/bay/month); parking fill-up curve; developer revenue-share scenario',
    remark_components='assumption of ~2 motorbikes per apartment; motorbike monthly rate from 0. Info; ~7 of 100 apartments with a monthly bicycle, bicycle rate; reference to "Tiến độ lấp đầy bãi xe"',
    guideline_sheet='1. Summary; 0. Info', exensive_logic='not-covered')
row(code='RP1', item_en='Motorbike monthly parking', item_vi='Tiền thu từ gắn máy tháng', section='revenue',
    method='bays-x-fill-x-rate', occupancy_scaled='yes',
    method_detail='Motorbike bays x fill % x rate, month by month. Motorbike fill roughly tracks resident fill; if total bike bays < units, fill ramps ~2x faster.',
    inputs='0. Info!F (motorbike bays); 0. Info!I (VND/bay/month); parking fill-up curve',
    remark_components='bays; rate; fill-up basis', guideline_sheet='0. Info; Tiến độ lấp đầy bãi xe', exensive_logic='not-covered')
row(code='RP2', item_en='Car monthly parking', item_vi='Tiền thu từ xe ô tô tháng', section='revenue',
    method='bays-x-fill-x-rate', occupancy_scaled='yes',
    method_detail='Car bays x fill % x rate, month by month via Schedule into cols H:S. Car-park fill: 0% -> ~40-55% end of year 1 -> '
      '~70-80% end of year 2; ~2x faster if car bays are <= 50% of units. Revenue-share scenarios (developer gives / shares / keeps) '
      'change where the figure lands (RP2 vs ESS38 vs RM.PA).',
    inputs='0. Info!F (car bays); 0. Info!I (VND/bay/month); parking fill-up curve; ownership/revenue-share scenario',
    remark_components='car bays; rate; fill-up basis; which developer scenario applies',
    guideline_sheet='0. Info; Tiến độ lấp đầy bãi xe', exensive_logic='not-covered')
for c, en, vi in [('RP5', "Motorbike/bicycle daily visitors' parking", 'Tiền thu từ xe hai bánh vãng lai'),
                  ('RP6', "Car daily visitors' parking", 'Tiền thu từ xe ô tô vãng lai')]:
    row(code=c, item_en=en, item_vi=vi, section='revenue', method='visitor-parking-estimate', occupancy_scaled='yes',
        method_detail='Estimated daily visitor parking; guideline requires it whenever car parking revenue (scenario 1 or 2) is budgeted.',
        inputs='visitor volume assumption; daily rate', remark_components='visitor volume basis; daily rate',
        guideline_sheet='0. Info', exensive_logic='not-covered')
row(code='RO', item_en='Others (revenue)', item_vi='Khác', section='revenue', method='itemised-list',
    method_detail='Whatever sub-items RO1..RO33 carry a value. Summary remark lists every RO item that has a figure.',
    inputs='the RO sub-rows that are populated',
    remark_components='list of every populated RO sub-item',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='not-covered')
row(code='RI', item_en='Collect operating expenses already paid for common area fund',
    item_vi='Thu kinh phí vận hành đã chi hộ quỹ khai thác khu vực chung', section='revenue',
    method='linked-from-common-area-fund',
    method_detail='Equals the operating expenses the management fund paid on behalf of the common-area fund; taken from sheet "2.2 Common area Fund".',
    inputs='2.2 Common area Fund total paid on behalf',
    remark_components='that it is expenses paid on behalf of the common-area fund; reference to "2.2 Common area Fund"',
    guideline_sheet='1. Summary; 2.2 Common area Fund', exensive_logic='not-covered')

# ---------- 2.2  MANAGEMENT & ADMIN ----------
row(code='EMH', item_en='Human Resource (Management Company staff)', item_vi='Chi phí quản lý và nhân sự của Công ty Quản Lý',
    section='management-expense', method='headcount-from-staffing-sheet',
    method_detail='Total of EMH1..EMH12. Headcount and positions from sheet "A1. Staff cost 08.2026 (VN)", sized to project '
      'scale, segment and quality requirement; night/holiday shift time per law.',
    inputs='A1. Staff cost sheet (positions, headcount, salary); A5 PCCC training',
    remark_components="Management Company overhead (brand, software, head-office support) sized to workload and handover; BQL headcount by project scale/segment; night and holiday shift basis; reference to A1 staff cost sheet and A5 PCCC training; VAT-and-base-year note if figures include VAT",
    legal_citation='NĐ 105/2025/NĐ-CP (annual mandatory ATLĐ / PCCC training)',
    guideline_sheet='1. Summary; A1. Staff cost 08.2026 (VN)', exensive_logic='agrees',
    precedence_note='')
row(code='EMH1', item_en='Management fee for Savills', item_vi='Phí quản lý cố định của Savills',
    section='management-expense', method='contract-fixed-or-cpi-or-nfa',
    method_detail='Contract basis: fixed monthly fee x 12, or last year x (1+CPI), or NFA x unit price x 12. '
      'Left BLANK by the pipeline by design - no contract terms exist for a prospect. Pending PM decision D1 / docs/05 B1. '
      'While blank, every output must caveat that the surplus excludes Savills\' own fee.',
    inputs='contract value; CPI clause; NFA (Project Info B30/B31 when a basis is decided)',
    remark_components='the fee basis once decided; until then, a visible caveat that the surplus is not a profit',
    guideline_sheet='1. Summary; A1. Staff cost 08.2026 (VN)', exensive_logic='agrees',
    precedence_note='')
row(code='EMH2', item_en='Staff cost for Savills (gross payroll)', item_vi='Phí lương gộp',
    section='management-expense', method='headcount-x-salary-plus-employer-insurance',
    method_detail='Sum(headcount x salary x 12) + employer insurance contribution (~21.5% loading). Roster positions other than '
      'Security/Cleaning/Landscape, which are costed as outsourced contracts (see spec outsourced-service-costs).',
    inputs='roster positions and headcount; salary per position; statutory minimum wage; social-insurance rate',
    remark_components='headcount by position; salary basis; that employer insurance is included',
    legal_citation='statutory minimum wage by region; social-insurance rate',
    guideline_sheet='A1. Staff cost 08.2026 (VN)', exensive_logic='agrees', precedence_note='')
row(code='EMH3', item_en='Allowance for night shift / public holiday work', item_vi='Phụ cấp trực ca đêm, làm việc lễ/tết',
    section='management-expense', method='labour-law-driver',
    method_detail='(night shifts x allowance per shift x 12) + (holiday days x staff x allowance per day), at the multipliers labour law sets.',
    inputs='night-shift count; public-holiday count; allowance rates; staff on duty',
    remark_components='night-shift and holiday-shift counts; statutory multipliers used',
    legal_citation='Bộ luật Lao động 2019 Điều 112 (11 public holidays); night/holiday multipliers',
    guideline_sheet='A1.1 Allowance (From 08.2026)', exensive_logic='agrees', precedence_note='')
row(code='EMA', item_en='Administrative Expense (BQL office overhead)', item_vi='Chi phí quản lý văn phòng của VPBQL',
    section='management-expense', method='benchmark-by-comparable',
    method_detail='Guideline: benchmark each sub-item (EMA1..EMA19) against a comparable project scaled by area ratio '
      '("tam suất diện tích"); drinking water is sized by BQL headcount (1 L/person/day, 19 L bottle at 60,000 VND incl VAT). '
      'Pipeline currently writes one blended per-m2 ratio to the EMA catch-all row (EMA15).',
    inputs='comparable project EMA lines; project vs comparable area ratio; BQL headcount (for EMA7)',
    remark_components='every populated EMA sub-item listed; VAT-and-base-year note if figures include VAT',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='differs',
    precedence_note='EXENSIVE LOGIC.xlsx costs EMA sub-items as historical average + inflation / per-contract. Guideline says benchmark from a comparable by area ratio. Catalogue takes the guideline method; the per-line contract/consumption detail in EXENSIVE LOGIC still informs individual sub-items where a real basis exists.')
row(code='EMB', item_en='Bank and Audit', item_vi='Ngân hàng và kiểm toán', section='management-expense',
    method='benchmark-by-comparable',
    method_detail='Guideline: benchmark against a comparable project. EXENSIVE LOGIC: bank fee = transactions x fee + fixed charge; '
      'audit = annual engagement fee (lump sum).',
    inputs='comparable project EMB lines; (or) transaction volume, per-transaction fee, audit engagement fee',
    remark_components='every populated EMB sub-item listed; VAT note if applicable',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='differs',
    precedence_note='Guideline says benchmark by comparable; EXENSIVE LOGIC says transaction-volume / signed engagement. Where a real transaction count or engagement letter exists, use the EXENSIVE LOGIC formula for that sub-item.')

# ---------- 2.3  OUTSOURCED SERVICES ----------
row(code='ESC', item_en='Communication and Event', item_vi='Hoạt động cộng đồng và sự kiện', section='management-expense',
    method='programme-itemised',
    method_detail='Built item by item: events (budget per event x count), fire drill, Christmas and Lunar New Year lobby decoration '
      '(cost per lobby x lobby count), environmental incident-response plan.',
    inputs='number and scale of planned events; lobby count; fire-drill fees; env-plan fee',
    remark_components='number of events with the main event names for a year of operation; PCCC: year 1 has both a plan-preparation fee and an annual drill fee; Christmas lobby decoration (1 lobby x lobby count); Lunar New Year lobby decoration (1 lobby x reception-desk lobby count); VAT-and-base-year note if figures include VAT',
    legal_citation='PCCC regulation (annual fire drill)', guideline_sheet='1. Summary; 2. Budget-Management Fund',
    exensive_logic='agrees', precedence_note='')
row(code='ESC1', item_en='Events', item_vi='Tổ chức sự kiện', section='management-expense', method='programme-itemised',
    method_detail='Sum of (budget per event x number of events). Built event by event, never a flat inflation %.',
    inputs='number of events; budget per event; event scale',
    remark_components='number of events and their names', guideline_sheet='2. Budget-Management Fund', exensive_logic='agrees')
row(code='ESC2', item_en='Fire Drill', item_vi='Diễn tập PCCC', section='management-expense', method='regulation-count-x-cost',
    method_detail='Number of drills required per year x cost per drill. Year 1 of a new project also carries a one-off PCCC plan-preparation fee.',
    inputs='drills required per year; cost per drill; year-1 plan-preparation fee',
    remark_components='drills per year; that year 1 has an extra plan-preparation fee',
    legal_citation='PCCC regulation', guideline_sheet='2. Budget-Management Fund', exensive_logic='agrees')
row(code='ESC12', item_en='Mandatory environmental incident-response plan', item_vi='Kế hoạch phòng ngừa, ứng phó sự cố môi trường',
    section='management-expense', method='regulation-fixed-estimate',
    method_detail='Mandatory once a year. Guideline gives a provisional ~14,000,000 VND per occurrence, excl VAT.',
    inputs='one occurrence per year at ~14,000,000 VND excl VAT',
    remark_components='that it is a once-a-year legal requirement; the provisional amount',
    legal_citation='environmental incident-response plan requirement', guideline_sheet='2. Budget-Management Fund',
    exensive_logic='not-covered', precedence_note='Not in EXENSIVE LOGIC; guideline provides the figure directly.')
row(code='ESS1', item_en='Security service', item_vi='Dịch vụ bảo vệ', section='management-expense',
    method='contract-posts-x-24h-rate',
    method_detail='Vendor contract priced as posts x citywide 24h post rate x 12, blended for the project night-shift split. '
      'Post count and mix from sheet "A2. Bảo vệ - Security". No employer insurance loading - a vendor post price already covers it.',
    inputs='A2 Security sheet (post count and mix); citywide 24h post rate (Fact_MasterRateCard.csv, n=1)',
    remark_components='total posts, or total posts converted to 24h, broken down by position (e.g. team leader, shift leader, CCTV/FCC controller, amenity posts, doormen, apartment patrol, basement gate control, works-registration patrol, vehicle marshals); the 24h unit rate; VAT-and-base-year note if figures include VAT',
    guideline_sheet='1. Summary; A2. Bảo vệ - Security', exensive_logic='agrees', precedence_note='')
row(code='ESS4', item_en='Cleaning service for common area', item_vi='Dịch vụ vệ sinh công cộng',
    section='management-expense', method='contract-posts-x-rate', occupancy_scaled='yes',
    method_detail='Vendor contract as posts x citywide post rate x 12. Headcount and shift hours from sheet "A3. Vệ sinh - Cleaning". '
      "Spec's m2 x unit-price branch is unimplementable - no per-m2 cleaning rate in the source. Guideline ties the figure to resident occupancy for a new project.",
    inputs='A3 Cleaning sheet (headcount by role, shift hours); citywide post rate (n=1); resident fill-up curve',
    remark_components='total cleaners and shift hours by role (supervisor, team leader, periodic cleaner, waste collector, lobby/amenity cleaner, corridor cleaners morning+afternoon, basement car-park cleaner); cleaner unit rate (mandatory) and tea-lady/supervisor rate if any; VAT-and-base-year note',
    guideline_sheet='1. Summary; A3. Vệ sinh - Cleaning', exensive_logic='agrees',
    precedence_note="EXENSIVE LOGIC's primary is m2 x unit price x 12; that branch has no rate data, so the stated alternative 'monthly contract x 12' is used and the output says so (see spec logic-spec-method-alignment).")
row(code='ESS9', item_en='Normal garbage collection', item_vi='Thu gom rác sinh hoạt', section='management-expense',
    method='official-tariff-table',
    method_detail='Priced from the TPHCM household-waste tariff table in QĐ 67/2025, effective 01/06/2025 (see sheet "B2.6 Rác sinh hoạt (QD67)").',
    inputs='waste volume / product counts; QĐ 67/2025 tariff table',
    remark_components='the tariff basis (QĐ 67/2025); volume or unit basis used',
    legal_citation='Quyết định 67/2025 (TPHCM household-waste tariff, effective 01/06/2025)',
    guideline_sheet='2. Budget-Management Fund; B2.6 Rác sinh hoạt (QD67)', exensive_logic='agrees', precedence_note='')
row(code='ESS16', item_en='Landscaping service', item_vi='Dịch vụ chăm sóc cảnh quan, cây cảnh', section='management-expense',
    method='contract-headcount-x-12',
    method_detail='Monthly contract x 12, contract sized from headcount on sheet "A4. Cây xanh - Landscape".',
    inputs='A4 Landscape sheet (headcount); monthly contract rate',
    remark_components='landscape headcount; monthly contract basis; VAT note',
    guideline_sheet='A4. Cây xanh - Landscape', exensive_logic='agrees', precedence_note='')
row(code='ESI1', item_en='Risk asset insurance (incl. compulsory fire & explosion)', item_vi='Bảo hiểm rủi ro tài sản',
    section='management-expense', method='asset-value-x-premium-rate',
    method_detail='Insured asset value x premium rate. Guideline example: commercial apartment building = total asset value x 0.05%. '
      'Currently left at 0 by the pipeline - no asset value captured.',
    inputs='total insured asset value (or developer-provided contract value); premium rate per NĐ 105/2025',
    remark_components='asset value basis; premium rate; that it includes compulsory fire & explosion cover; VAT note',
    legal_citation='Nghị định 105/2025/NĐ-CP (effective 01/07/2025)',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='agrees', precedence_note='')
row(code='ESI2', item_en='Public liability insurance', item_vi='Bảo hiểm trách nhiệm công cộng', section='management-expense',
    method='annual-quotation',
    method_detail='Insurance premium as per annual quotation / coverage limit. Guideline column blank; method from EXENSIVE LOGIC.xlsx.',
    inputs='coverage limit; premium rate; risk profile',
    remark_components='coverage limit; premium basis; VAT note', guideline_sheet='1. Summary',
    exensive_logic='not-covered', precedence_note='Guideline column blank for ESI2; EXENSIVE LOGIC.xlsx is the sole authority (coverage-based, annual quotation).')
row(code='ESM', item_en='M&E Operation', item_vi='Vận hành M&E', section='management-expense', method='itemised-list',
    method_detail='Total of whatever ESM sub-items are populated (water testing, pool testing, pool chemicals, pool cleaning tools, '
      'HCMC fire-dept connection, small replacement materials, etc.).',
    inputs='the populated ESM sub-rows',
    remark_components='every populated ESM sub-item listed by name; VAT-and-base-year note',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='agrees', precedence_note='')
row(code='ESM2', item_en='Outsourcing Environmental Report', item_vi='Báo cáo môi trường định kỳ (quan trắc)',
    section='management-expense', method='regulation-count-x-cost',
    method_detail='Number of required reports per year x vendor cost per report.',
    inputs='reports required per year; vendor quotation',
    remark_components='reports per year; that it is a legal requirement',
    legal_citation='periodic environmental monitoring requirement', guideline_sheet='2. Budget-Management Fund',
    exensive_logic='agrees')
row(code='ESM3', item_en='Domestic water testing', item_vi='Kiểm định nước sinh hoạt', section='management-expense',
    method='frequency-x-unit-cost',
    method_detail='Required testing frequency per year x cost per test.',
    inputs='testing frequency per year; cost per test',
    remark_components='testing frequency; regulatory basis',
    legal_citation='domestic water quality regulation', guideline_sheet='2. Budget-Management Fund', exensive_logic='agrees')
row(code='ESM4', item_en='Chemicals for pool', item_vi='Hóa chất hồ bơi', section='management-expense', method='pool-volume-x-dose-x-price',
    method_detail='Pool volume (m3) x 2.5 kg/m3/month (midpoint of a stated 1-4 kg range) x 6,000 VND/kg x 12. Volume from '
      'intake field "Pool Volume (m3)"; falls back to a flat figure (~444 m3 equivalent) if blank, labelled as a fallback. '
      'Acid dosing is excluded and the row says so.',
    inputs='Pool Volume (m3) intake field; dose rate 2.5 kg/m3/month; unit price 6,000 VND/kg',
    remark_components='pool volume used (or that a fallback was used and what it does not vary with); the 1-4 kg range and the figures its ends produce; that acid is excluded',
    guideline_sheet='2. Budget-Management Fund', exensive_logic='agrees',
    precedence_note='Implemented per EXENSIVE LOGIC volume-based method by change align-methods-with-logic-spec / decision D5.')
row(code='ESM5', item_en='Pool water testing', item_vi='Kiểm định nước hồ bơi', section='management-expense', method='frequency-x-unit-cost',
    method_detail='Tests per year x unit cost.', inputs='tests per year; cost per test',
    remark_components='testing frequency; public-health basis', legal_citation='public health / pool water standards',
    guideline_sheet='2. Budget-Management Fund', exensive_logic='agrees')
row(code='ESM8', item_en='Connect to HCMC Fire Fighting Dept', item_vi='Phí kết nối với Trung tâm PCCC thành phố',
    section='management-expense', method='regulation-fixed-fee',
    method_detail='Annual fixed connection fee per the authority tariff.', inputs='annual connection fee',
    remark_components='that it is the official authority tariff', legal_citation='HCMC Fire Fighting Dept tariff',
    guideline_sheet='2. Budget-Management Fund', exensive_logic='agrees')

# ---------- 2.4  CAPEX ----------
row(code='EN', item_en='New Capital expenditure', item_vi='Chi phí đầu tư mua sắm thiết bị mới', section='management-expense',
    method='asset-list-sum-depreciated-24mo',
    method_detail='Sum(quantity x unit cost) across three asset groups: BQL office equipment, technical & PCCC tools, '
      'common-area / amenity equipment. Guideline: expected to be fully written off over the first 24 months of operation.',
    inputs='equipment list per group; unit cost; quantity',
    remark_components='the three asset groups named; that the cost is depreciated over the first 24 operating months; VAT-and-base-year note',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='agrees',
    precedence_note='Guideline adds the 24-month write-off framing on top of the EXENSIVE LOGIC Sum(qty x unit cost) capex method.')
for c, en, vi in [('EN1', 'New capex for MO', 'Trang thiết bị văn phòng ban quản lý'),
                  ('EN2', 'New capex for ME team', 'Trang thiết bị kỹ thuật & PCCC'),
                  ('EN3', 'New capex for Common area', 'Trang thiết bị khu công cộng'),
                  ('EN4', 'New capex for Tenant / amenity area', 'Trang thiết bị khu tiện ích/ khách thuê')]:
    row(code=c, item_en=en, item_vi=vi, section='management-expense', method='asset-list-sum-depreciated-24mo',
        method_detail='Sum(quantity x unit cost) for this asset group; written off over the first 24 operating months.',
        inputs='equipment list; unit cost; quantity',
        remark_components='asset group contents; 24-month write-off', guideline_sheet='1. Summary',
        exensive_logic='agrees')

# ---------- 2.5  ENERGY ----------
row(code='EE', item_en='Energy Consumption', item_vi='Năng lượng', section='nav', method='section-total',
    method_detail='Template SUBTOTAL of EEW/EEE/EED/EEG plus contingency.', guideline_sheet='2. Budget-Management Fund',
    exensive_logic='not-covered')
row(code='EEW', item_en='Water (public)', item_vi='Nước công cộng', section='energy', method='consumption-x-tariff',
    occupancy_scaled='yes',
    method_detail='Monthly common-area consumption (m3) x tariff x 12. Tariff build-up: base + VAT 5% + PBVMT 30% + VAT-on-PBVMT 8% '
      '(guideline cites 19,786 VND/m3 as the built-up example). Ramps with resident occupancy for a new project.',
    inputs='monthly common-area water m3; tariff per m3; resident fill-up curve',
    remark_components='monthly consumption in m3; tariff with the VAT/PBVMT build-up; that the year-1/year-2 figure follows resident occupancy; VAT-and-base-year note',
    legal_citation='SAWACO household-water tariff; PBVMT 30%; VAT 5%',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='agrees',
    precedence_note='Guideline and EXENSIVE LOGIC agree (usage x tariff). Active change cost-energy-from-consumption-and-tariff implements it; the pipeline today still uses a cost-per-m2 ratio (believed ~3.3x high).')
row(code='EEW.C', item_en='Water for Common Area and Facilities', item_vi='Nước công cộng khu vực chung',
    section='energy', method='consumption-x-tariff', occupancy_scaled='yes',
    method_detail='Monthly average m3 x tariff x 12. This is the leaf row the pipeline writes.',
    inputs='monthly common-area water m3; tariff per m3; resident fill-up curve',
    remark_components='consumption m3; tariff build-up; occupancy basis',
    legal_citation='SAWACO tariff; PBVMT 30%; VAT 5%', guideline_sheet='2. Budget-Management Fund', exensive_logic='agrees')
row(code='EEE', item_en='Electricity (public)', item_vi='Điện công cộng', section='energy', method='consumption-x-tariff',
    occupancy_scaled='yes',
    method_detail='Monthly kWh x tariff x 12. Tariff = under-6kV administrative rate, 2,226 VND/kWh per QĐ 1279/QĐ-BCT (09/05/2025). '
      'New project: month by month off the resident fill-up curve via Schedule. Floor: at 0% occupancy electricity is ~40% of full load; '
      'ramps evenly to full by ~40% occupancy (full capacity x tariff).',
    inputs='monthly common-area kWh; tariff per kWh (QĐ 1279); operating hours; facility load; resident fill-up curve',
    remark_components='total monthly kWh; the tariff and its QĐ 1279/QĐ-BCT basis; that year-1/year-2 follow resident occupancy with a ~40% floor at zero occupancy; VAT-and-base-year note',
    legal_citation='Quyết định 1279/QĐ-BCT ngày 09/05/2025 (điện dưới 6kV, đơn vị hành chính sự nghiệp, 2.226 đ/kWh)',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='agrees',
    precedence_note='Guideline and EXENSIVE LOGIC agree (projected kWh x updated tariff, follow EVN structure). Guideline adds the 40% occupancy floor. Active change cost-energy-from-consumption-and-tariff.')
row(code='EEE.C', item_en='Electricity for Common Area', item_vi='Điện khu công cộng khu vực chung', section='energy',
    method='consumption-x-tariff', occupancy_scaled='yes',
    method_detail='Projected annual kWh x updated tariff. Leaf row the pipeline writes. 40% floor at zero occupancy, ramps to full by ~40%.',
    inputs='monthly common-area kWh; tariff per kWh (QĐ 1279); resident fill-up curve',
    remark_components='monthly kWh; tariff and QĐ 1279 basis; occupancy floor and ramp',
    legal_citation='Quyết định 1279/QĐ-BCT ngày 09/05/2025', guideline_sheet='2. Budget-Management Fund', exensive_logic='agrees')
row(code='EED', item_en='Diesel (generator fuel)', item_vi='Dầu máy phát điện', section='energy', method='consumption-x-tariff',
    method_detail='Consumption-based: (running hours x fuel consumption rate L/h x diesel price/L) x 12. Guideline: state generator count and each unit kVA; '
      'per year ~12h no-load test + ~8h on-load backup (grid faults + transformer/MSB maintenance). Diesel price = DO 0.005S, Vùng 1, '
      'listed price on the budget date.',
    inputs='generator count and kVA; annual test hours (~12); annual backup hours (~8); fuel consumption rate (L/h); DO 0.005S Vùng 1 price',
    remark_components='generator count and each unit kVA; annual test and backup hours; the DO 0.005S Vùng 1 price and its date; VAT note',
    legal_citation='DO 0.005S Vùng 1 listed fuel price', guideline_sheet='1. Summary; 2. Budget-Management Fund',
    exensive_logic='agrees',
    precedence_note='Guideline and EXENSIVE LOGIC agree (run hours x consumption x price x 12). Active change cost-energy-from-consumption-and-tariff. Not occupancy-scaled - driven by test/backup hours, not fill.')
row(code='EED.C', item_en='Diesel for common-area back-up generators', item_vi='Dầu chạy máy phát điện khu công cộng',
    section='energy', method='consumption-x-tariff',
    method_detail='(running hours x consumption rate x diesel price) x 12. Leaf row the pipeline writes.',
    inputs='generator run hours; consumption rate L/h; diesel price',
    remark_components='generator count and kVA; test/backup hours; fuel price and date',
    legal_citation='DO 0.005S Vùng 1 listed fuel price', guideline_sheet='2. Budget-Management Fund', exensive_logic='agrees')
row(code='EEG', item_en='Gas', item_vi='Gas', section='energy', method='unclear',
    method_detail='Guideline column blank; no method stated. Usually zero for a residential project.',
    inputs='', remark_components='', guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered',
    precedence_note='No method in either source; left unclear.')
row(code='EE#', item_en='Energy contingency', item_vi='Dự phòng năng lượng', section='energy', method='linked-remark',
    method_detail='Contingency on the energy section; guideline says link the remark from the corresponding code in "2. Budget-Management Fund".',
    inputs='energy section total', remark_components='that it is an energy-section contingency',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='not-covered')

# ---------- 2.6  REPAIRS / SINKING / TAX ----------
row(code='ER', item_en='Repairs and Maintenance', item_vi='Sửa chữa & bảo dưỡng', section='repairs', method='itemised-list',
    method_detail='Total of whatever ER sub-items are populated. Most technical maintenance/replacement is expected to be '
      'budgeted from the Sinking Fund; the management fund typically carries only tank cleaning, drainage/manhole cleaning, '
      'STP sludge removal and septic-tank pump-out (the ERCS group).',
    inputs='the populated ER sub-rows (ERCS group in the common case)',
    remark_components='every populated ER sub-item listed by name; that technical maintenance is largely on the Sinking Fund; VAT-and-base-year note',
    guideline_sheet='1. Summary; 2. Budget-Management Fund', exensive_logic='not-covered',
    precedence_note='ER detail is not in EXENSIVE LOGIC Sheet1 (management-expense scope). Guideline: list populated items.')
for c, en, vi in [('ERCS1', 'Water tank periodical cleaning', 'Vệ sinh bồn nước định kỳ'),
                  ('ERCS2', 'Drainage and manhole cleaning', 'Vệ sinh cống rãnh, hố ga'),
                  ('ERCS3', 'STP periodical cleaning / sludge removal', 'Hút vệ sinh bùn trạm xử lý chất thải'),
                  ('ERCS4', 'Septic tank clearance / suction', 'Hút hầm cầu'),
                  ('ERCS5', 'Sewage interceptor clearance / suction', 'Hút mỡ bể tách dầu mỡ')]:
    row(code=c, item_en=en, item_vi=vi, section='repairs', method='frequency-x-unit-cost',
        method_detail='Scheduled cleaning/suction: frequency per year x unit cost. Benchmark unit cost from a comparable project.',
        inputs='frequency per year; unit cost (benchmark)',
        remark_components='frequency; unit-cost basis', guideline_sheet='2. Budget-Management Fund', exensive_logic='not-covered')
row(code='ESH', item_en='Expense sharing', item_vi='Chi phí chia sẻ', section='management-expense', method='unclear',
    method_detail='Township / shared-area cost allocation. Guideline column blank; project-specific.',
    inputs='township MF rate; shared area', remark_components='', guideline_sheet='2. Budget-Management Fund',
    exensive_logic='not-covered', precedence_note='No method stated in either source; project-specific, left unclear.')
row(code='ESP', item_en='Parking Operation Expense', item_vi='Chi phí vận hành bãi xe', section='management-expense', method='unclear',
    method_detail='Cost of operating the car park when it sits in the management fund. Guideline column blank; project-specific.',
    inputs='parking operation cost basis', remark_components='', guideline_sheet='2. Budget-Management Fund',
    exensive_logic='not-covered', precedence_note='No method stated; left unclear.')
row(code='E.S', item_en='Repairs and Maintenance using Sinking Fund', item_vi='Sửa chữa & bảo trì dùng Quỹ bảo trì',
    section='sinking-fund', method='reserve-schedule',
    method_detail='Sinking-fund maintenance/replacement schedule. Reserve rate derived from real projects (0.1093 per change derive-capex-reserve-rate); drop-year still open.',
    inputs='asset base; reserve rate; drop-year schedule',
    remark_components='reserve rate and its basis; which items are on the Sinking Fund vs the management fund',
    guideline_sheet='3. Budget-Sinking Fund; 3.1 Report-Sinking Fund', exensive_logic='not-covered',
    precedence_note='Governed by change derive-capex-reserve-rate, not the guideline column.')
row(code='CIT2', item_en='Corporate Income Tax on extra input cash flow', item_vi='Thuế TNDN trên doanh thu cộng thêm',
    section='tax', method='rate-on-extra-revenue',
    method_detail='Provisional: 20% of total extra revenue; if a BQT (owners board) is formed, 5% VAT + 5% CIT instead. '
      'Reference figure only - depends on real revenue/cost and a tax-authority request.',
    inputs='extra revenue; whether a BQT tax code exists',
    remark_components='that it is a reference figure contingent on a tax-authority request; the 20% (or 5%+5%) basis',
    legal_citation='CIT on extra revenue (tax-authority discretion)', guideline_sheet='1. Summary',
    exensive_logic='not-covered')

with open(OUT, 'w', newline='', encoding='utf-8-sig') as f:
    f.write('# Costing Method Catalogue - extracted from: %s\n' % SOURCE_FILE)
    f.write('# Source version: %s\n' % SOURCE_VERSION)
    f.write('# Superseded template retained as backup: input/template/202608 - 2027 Resi Budget Form.xlsx (19 sheets)\n')
    f.write('# Authority: this catalogue governs METHOD SELECTION and REMARK CONTENT per code.\n')
    f.write("#   EXENSIVE LOGIC.xlsx governs formula mechanics where the two agree ('exensive_logic' column: agrees|differs|not-covered|mechanics-only).\n")
    f.write('# Codes not listed here are not yet catalogued (distinct from having no method); EXENSIVE LOGIC.xlsx alone applies to them.\n')
    f.write('# occupancy_scaled=yes: figure varies month by month with the fill-up curve (downstream change: occupancy ramp / D8).\n')
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    for r in R:
        w.writerow(r)

print('wrote', len(R), 'rows ->', OUT)
from collections import Counter
print('by section:', Counter(r['section'] for r in R))
print('by exensive_logic:', Counter(r['exensive_logic'] for r in R))
print('occupancy_scaled=yes:', sum(1 for r in R if r['occupancy_scaled'] == 'yes'))
print('method=unclear:', [r['code'] for r in R if r['method'] == 'unclear'])
print('differs rows:', [r['code'] for r in R if r['exensive_logic'] == 'differs'])
