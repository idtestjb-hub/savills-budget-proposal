"""
Build `data/master_list_verified/Dim_ReferenceProject.csv` once from the figures the code used to hold as literals
(change reference-projects-by-key, task 1.1). Office-only script: it is the one place that may still spell the
reference projects' names, because its job is to move them into data.

    python build_reference_registry.py [--out <csv>] [--check]

--check reads the file back and verifies: 8 rows, every name variant used by the four fact files resolves to exactly
one key, the keys are R01..R08. The script never touches the fact files.
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import reference_projects as rp  # noqa: E402

BUDGET_AGENT = os.path.dirname(HERE)
DATA = os.path.join(BUDGET_AGENT, 'data')
FACT_FILES = (
    ('generation_A_star_schema/Fact_OPEX.csv', 'Project'),
    ('generation_A_star_schema/Fact_Capex_Rescanned.csv', 'Project'),
    ('generation_A_star_schema/Fact_CapexReserve.csv', 'Project'),
    ('master_list_verified/Ref_ComparableVATBasis.csv', 'project_key'),
)
# Rows of the VAT-basis file that belong to a master-list project, not a reference project (kept keyed by name).
NOT_REFERENCE = {'rivergate residence'}

# The figures as they were in master_comparables.HAND_VERIFIED_COMPARABLES (TotalNFA = product-only subtotal where the
# source "0. Info" sheet gave one) and estimate_capex_qty.VERIFIED_NFA_FOR_ITEMS (the capex scaling NFA, the source
# file's grand total where that is what the study measured). Copied verbatim on 2026-11-06, not re-derived.
ROWS = [
    dict(RefKey='R01', DisplayName='11D Thi Sách', Aliases=['11D Thi Sach'],
         TotalNFA_m2=16783.14, CapexNFA_m2=16783.14, ApartmentUnits=157, TotalUnits=162,
         MgmtRate_VND_m2_month=None, MgmtRateVAT=None, District='District 1', City='Hồ Chí Minh', Comparable=1,
         ExcludedFromRanking='', Roles=[rp.ROLE_CAPEX_ITEMS],
         Source='TotalNFA: Dim_Property_v2_verified.csv. Info sheet layout not yet parsed for a per-m² rate.',
         LocationSource="Address is the project's own street number (Bến Nghé Ward) — confirmed, not inferred from the "
                        "street name, via a contractor financial disclosure (Vietstock, re: Hòa Bình Corp/HBC) and "
                        "real-estate press, both independently naming the address in District 1, HCMC. Verified by web "
                        "research 2026-09-17.",
         VerifiedOn='2026-09-17'),
    dict(RefKey='R02', DisplayName='A&K Tower', Aliases=[],
         TotalNFA_m2=64124.00, CapexNFA_m2=64124.00, ApartmentUnits=1155, TotalUnits=1162,
         MgmtRate_VND_m2_month=None, MgmtRateVAT=None, District='Thuận An', City='Hồ Chí Minh', Comparable=1,
         ExcludedFromRanking='', Roles=[rp.ROLE_UTILITIES_BASE, rp.ROLE_CAPEX_ITEMS],
         Source='TotalNFA: Dim_Property_v2_verified.csv. Uses "Info "/"Master Info" sheet layout, not "0. Info"; no '
                'per-m² rate parsed yet.',
         LocationSource='An Phú 17 Street, An Phú Ward, Thuận An (pre-2025-merger Bình Dương province, now part of Hồ '
                        'Chí Minh City) — developer OBC Holdings. Corroborated by an exact match on unit count (1,155 '
                        "apartments) and by the project's own materials naming Savills as development/operating "
                        'partner. District kept at the old Thuận An granularity to match this column\'s convention '
                        'elsewhere; city set to the current post-merger name. Verified by web research 2026-09-17.',
         VerifiedOn='2026-09-17'),
    dict(RefKey='R03', DisplayName='Lumi Prestige & Elite',
         Aliases=['202602 - Budget Lumi Prestige & Elite (Internal) v17 (Excl VAT) Ext bản in pre'],
         TotalNFA_m2=124954.90, CapexNFA_m2=134117.40, ApartmentUnits=1575, TotalUnits=1600,
         MgmtRate_VND_m2_month=21000, MgmtRateVAT='excl. VAT', District='Nam Từ Liêm', City='Hà Nội', Comparable=1,
         ExcludedFromRanking='Hà Nội is a different city from Hồ Chí Minh and its neighbouring provinces — every other '
                             'property in this pool is HCMC-metro (HCMC, Bình Dương/Dĩ An/Thuận An, Đồng Nai, Bà '
                             'Rịa-Vũng Tàu). A Hà Nội management-fee rate has no bearing on an HCMC-area property '
                             '(user, 2026-09-17: "they are 2 separated city"). Kept in the registry because the '
                             'NFA/rate/source data is real and may serve a genuine Hà Nội project.',
         Roles=[rp.ROLE_CAPEX_ITEMS],
         Source='NFA: "0. Info" sheet, "Các loại hình sản phẩm" (product-types) subtotal row — Apartment+Shophouse, '
                'NOT the 134,117 grand total (that included parking; fixed 2026-08-13). Rate: same sheet, row '
                '"Apartment". CapexNFA = the 134,117 grand total, the basis the capex study measured.',
         LocationSource='Matches a megaproject in Tây Mỗ Ward, Nam Từ Liêm, Hà Nội — its phase 2 (4 towers) is '
                        'reported at exactly 1,600 units, matching TotalUnits here exactly. Genuinely Hà Nội, not Hồ '
                        'Chí Minh City. The "& Elite" part is not independently confirmed (may be an internal sub-phase '
                        'label); the phase-2 identification itself is high-confidence. Verified by web research '
                        '2026-09-17.',
         VerifiedOn='2026-09-17'),
    dict(RefKey='R04', DisplayName='Lumi Signature',
         Aliases=['202602 - Budget Lumi Signature (Internal) v17 (Excl VAT) Ext bản in pre'],
         TotalNFA_m2=184707.00, CapexNFA_m2=195269.50, ApartmentUnits=2375, TotalUnits=2410,
         MgmtRate_VND_m2_month=17000, MgmtRateVAT='excl. VAT', District='Nam Từ Liêm', City='Hà Nội', Comparable=1,
         ExcludedFromRanking='Same reason as R03: a Hà Nội project in an HCMC-metro pool.',
         Roles=[rp.ROLE_CAPEX_ITEMS],
         Source='NFA: "0. Info" sheet, "Các loại hình sản phẩm" (product-types) subtotal row — Apartment+Shophouse, '
                'NOT the 195,269 grand total (that included parking; fixed 2026-08-13). Rate: same sheet, row '
                '"Apartment". CapexNFA = the 195,269 grand total, the basis the capex study measured.',
         LocationSource='Same megaproject as R03 — its phase 1 (5 towers). No official total-unit figure found; '
                        '~2,400 units estimated (4,000 project total minus phase 2\'s 1,600) is within 0.4% of '
                        'TotalUnits here (2,410), supporting the match. Also genuinely Hà Nội. Verified by web research '
                        '2026-09-17.',
         VerifiedOn='2026-09-17'),
    dict(RefKey='R05', DisplayName='Green Skyline',
         Aliases=['20260204 - Budget - Green Skyline ngân sách Pre +Operation năm 1'],
         TotalNFA_m2=92100.09, CapexNFA_m2=99252.45, ApartmentUnits=1251, TotalUnits=1297,
         MgmtRate_VND_m2_month=15000, MgmtRateVAT='incl. VAT', District='Dĩ An', City='Hồ Chí Minh', Comparable=1,
         ExcludedFromRanking='', Roles=[rp.ROLE_CAPEX_ITEMS],
         Source='NFA: "0. Info" sheet, "Các loại hình sản phẩm" (product-types) subtotal row — Apartment+Shophouse+'
                'Nursery, NOT the 99,252 grand total (that included parking; fixed 2026-08-13). Rate: same sheet, row '
                '"Apartment". CapexNFA = the 99,252 grand total, the basis the capex study measured.',
         LocationSource='Full address (Dim_Property_Residential.csv) plus multiple independent developer/listing sites '
                        'confirm Đông Hòa Ward, Dĩ An City, pre-2025-merger Bình Dương province, now part of Hồ Chí '
                        'Minh City. District at the old Dĩ An granularity (this column\'s convention); city is the '
                        'post-merger value, consistent with Fact_ProjectLocation.csv ("Ho Chi Minh City" there, '
                        'normalised to "Hồ Chí Minh" here). Verified by web research 2026-09-17.',
         VerifiedOn='2026-09-17'),
    dict(RefKey='R06', DisplayName='Fiato Airport - F Zone G2', Aliases=[],
         TotalNFA_m2=35836.27, CapexNFA_m2=35836.27, ApartmentUnits=393, TotalUnits=432,
         MgmtRate_VND_m2_month=None, MgmtRateVAT=None, District='Nhơn Trạch', City='Đồng Nai', Comparable=1,
         ExcludedFromRanking='', Roles=[rp.ROLE_CAPEX_ITEMS],
         Source='TotalNFA: Dim_Property_v2_verified.csv. Uses a "Master Info" sheet layout, not "0. Info"; no per-m² '
                'rate parsed yet.',
         LocationSource='Tôn Đức Thắng St., Nhơn Trạch, Đồng Nai (near the new Long Thành airport, not Tân Sơn Nhất) '
                        '— multiple listings describe the building as "Chung cư G2, F", matching this entry\'s and '
                        'R07\'s "F Zone" naming. Verified by web research 2026-09-17.',
         VerifiedOn='2026-09-17'),
    dict(RefKey='R07', DisplayName='Fiato Airport - F Zone MF Pre/Y1/Y2', Aliases=[],
         TotalNFA_m2=35836.27, CapexNFA_m2=35836.27, ApartmentUnits=393, TotalUnits=469,
         MgmtRate_VND_m2_month=18000, MgmtRateVAT='excl. VAT', District='Nhơn Trạch', City='Đồng Nai', Comparable=1,
         ExcludedFromRanking='', Roles=[rp.ROLE_CAPEX_ITEMS],
         Source='TotalNFA reused from R06 (same physical apartment building, different budget-phase file — not '
                'independently re-verified for this file). Rate: "0. Info" sheet, row "Apartment", read 2026-08-12.',
         LocationSource='Same physical building as R06 — see that entry for the location evidence. Verified by web '
                        'research 2026-09-17.',
         VerifiedOn='2026-09-17'),
    dict(RefKey='R08', DisplayName='Parking Building',
         Aliases=['202602 - Budget Parking Building (Internal) v17 (Excl VAT) Ext bản in'],
         TotalNFA_m2=None, CapexNFA_m2=None, ApartmentUnits=0, TotalUnits=0,
         MgmtRate_VND_m2_month=None, MgmtRateVAT=None, District=None, City=None, Comparable=0,
         ExcludedFromRanking='No apartment product (its own Info sheet shows 0 for every apartment field): never a '
                             'meaningful comparable. Kept as the parking reference for utilities (reference-only '
                             'figures beside the utilities base) and as a capex-reserve observation.',
         Roles=[rp.ROLE_PARKING_BASE],
         Source='Parking structure budget among the eight original files; utility costs and quantities hand-read into '
                'Fact_OPEX.csv (reference only, not blended into any ratio); capex line items present but not used for '
                'scaling (no residential NFA).',
         LocationSource='', VerifiedOn='2026-09-17'),
]


def _cell(v):
    if v is None:
        return ''
    if isinstance(v, list):
        return '|'.join(v)
    if isinstance(v, float):
        return f'{v:.2f}'.rstrip('0').rstrip('.') if v != int(v) else str(int(v))
    return str(v)


def write(out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
        fh.write('# Reference-project registry (change reference-projects-by-key, 2026-11-06). One row per real budget the '
                 'tool prices from; every other file joins on RefKey.\n')
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(rp.COLUMNS)
        for r in ROWS:
            w.writerow([_cell(r[c]) for c in rp.COLUMNS])
    print(f'Wrote {len(ROWS)} rows -> {out}')


def check(out):
    rows = rp.load(out, force=True)
    ok = True
    if [r['key'] for r in rows] != [f'R{i:02d}' for i in range(1, 9)]:
        print('FAIL: keys are not R01..R08'); ok = False
    for rel, col in FACT_FILES:
        p = os.path.join(DATA, *rel.split('/'))
        with open(p, encoding='utf-8-sig', newline='') as fh:
            names = {(row.get(col) or '').strip() for row in csv.DictReader(ln for ln in fh if not ln.startswith('#'))}
        unmapped = sorted(n for n in names if n and rp.key_for_name(n, out) is None and rp.norm(n) not in NOT_REFERENCE)
        status = 'OK ' if not unmapped else 'FAIL'
        if unmapped:
            ok = False
        print(f'{status} {rel}: {len(names)} distinct names, unmapped: {unmapped}')
    for role in (rp.ROLE_UTILITIES_BASE, rp.ROLE_PARKING_BASE):
        n = len(rp.by_role(role, out))
        print(f'{"OK " if n == 1 else "FAIL"} role {role}: {n} row(s)')
        ok = ok and n == 1
    print(f'{"OK " if len(rp.by_role(rp.ROLE_CAPEX_ITEMS, out)) == 7 else "FAIL"} role capex_items: '
          f'{len(rp.by_role(rp.ROLE_CAPEX_ITEMS, out))} rows (expected 7)')
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=rp.REGISTRY_CSV)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    if not a.check or not os.path.isfile(a.out):
        write(a.out)
    return 0 if check(a.out) else 1


if __name__ == '__main__':
    sys.exit(main())
