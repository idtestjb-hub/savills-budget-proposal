# -*- coding: utf-8 -*-
"""
Extracts real OPEX/Utilities cost data (Electricity, Water, Diesel/Generator Fuel, Pool Salt,
Repairs & Maintenance) directly from the 8 real project files' own "D" series sheets — no prior
extraction of this category exists anywhere in this codebase (unlike Staff/Service/Capex, which
all had earlier ETL passes to build on).

CONSUMPTION x TARIFF (change cost-energy-from-consumption-and-tariff, 2026-09-10): the three energy
categories (Electricity, Water, Diesel) are now stored as two halves — `Quantity` + `Unit` +
`UnitPrice` + `PriceAsOf` beside the existing `MonthlyVND`. The costing spec states a
consumption-based method for all three and the source workbooks already work that way; the flat
`MonthlyVND` was the extraction collapsing it. `MonthlyVND` is kept unchanged so every current
reader still works, and for the two non-energy rows (Repairs, Admin) it stays the only figure.
The tariffs come from the method catalogue (`ENERGY_TARIFFS` below); A&K Tower's consumption is
DERIVED as recorded-cost / tariff because the A&K source workbook is not in this repository clone
(see the change design D6). Nothing here is re-read from a workbook — the figures are the same
hand-verified ones, now split.

WHY ELEVATOR/LIGHTING/SYSTEM MAINTENANCE CONTRACTS DON'T APPEAR HERE AT ALL, stated plainly since
it's easy to mistake for a gap rather than a real finding: A&K Tower's own real budget sheet
("A2.1 Thiết lập chi tiết", row 287) has a cell note citing actual Vietnamese law — maintenance
CONTRACT costs (elevator, MSB electrical panel, etc.) are funded from a legally separate "quỹ bảo
trì" (the one-time 2% maintenance fund collected at handover, per Housing Law 2023 Article 150 and
Construction Law Article 3), NOT from the ongoing management fee this tool's Staff/Service/OPEX
sheets model. What A&K DOES budget monthly under "Repairs and Maintenance" is a much narrower
materials/spare-parts-only line (33,165,000 VND/year) — real, small, and the only piece of this
category that legitimately belongs in a management-fee-funded operating budget.

HAND-VERIFIED, NOT a blind scanner, and here's why: OPEX sheet structure is far LESS consistent
across the 8 files than Capex was. Capex's "find the Unit Price column by text, take Qty/Total as
neighbors" trick worked everywhere because all 8 files share roughly the same Capex table shape.
OPEX does not:
  - A&K Tower / Fiato G2 / Fiato MF share one detailed engineering-load-calc structure for
    Electricity (163 real equipment rows, kWh math, cost = rate x consumption).
  - Parking Building has a completely different, much simpler combined "Summary Chi phí Điện,
    Nước, Dầu" sheet — one labeled total per category, no line-item detail.
  - Green Skyline's water/electricity sheet is not a real-consumption extraction target at all —
    it's a bespoke COMPARATIVE estimate against a different reference building (Estella Heights),
    scaling by floor-area/unit-count ratios. Real methodology, but not a number to lift directly.
  - Lumi Prestige & Elite / Lumi Signature only have a Garbage Collection sheet — no Water/
    Electricity/Diesel sheets exist in either file.
  - 11D Thi Sách has no OPEX-like sheets at all.
A blind keyword scanner would either miss real totals (Green Skyline) or grab the wrong one (the
Electricity sheets have TWO rows containing "Tổng" — "Tổng tiền điện..." is the real cost total,
"Tổng tiêu thụ điện..." right below it is a consumption total, not cost — silently taking the
wrong one would be a real, hard-to-notice bug). So this script hand-locates each real total by
its exact cell, the same standard as master_comparables.py's HAND_VERIFIED_COMPARABLES.

A REAL BUG CAUGHT AND CORRECTED while building this: A&K's own Electricity sheets have an
orphaned, broken column (a leftover duplicate calc, `=E*#REF!*G*H`, from a corrupted cell
reference) that looks alarming on a shallow read. It does NOT feed the real grand-total formula
(`=SUM(M10:M160)`), which depends only on the clean I->L->M formula chain. Verified by reading the
underlying FORMULAS (not just cached values) before concluding anything was actually broken.

A REAL DUPLICATION CAUGHT: Fiato Airport F Zone G2's OPEX sheets contain numbers IDENTICAL to
A&K Tower's, to the exact decimal (136,937,719.16815072 for Tower A electricity, in both files).
These are not independent real data for Fiato — they're the same template/placeholder values
copied into a different file. Treated as ONE real data point (A&K), not two.

Independent real data points, after all this: 2 (A&K Tower, Parking Building) for Water/
Electricity/Diesel. Parking Building is a parking structure, not a residential tower — its
numbers are real but not comparable in kind to a residential prospect, so they're recorded here
for reference but NOT blended into the per-NFA ratio estimate_opex.py derives (that uses A&K
alone, n=1, stated plainly). Pool Salt: 1 real data point (A&K/"An Khang" — the same property;
A&K's own sheet self-references this Vietnamese name), not scaled by any ratio since no real
data ties pool-salt cost to pool area/volume across more than one property.
"""
import os
import csv
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reference_projects  # noqa: E402

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_A_star_schema', 'Fact_OPEX.csv')

# ============================================================================================
# Hand-verified real figures — see module docstring for exactly how/why these were read (not
# blindly scanned). Every number here traces to one specific real cell in one specific real file.

AK_TOWER_NFA_M2 = 64_124.0  # master_comparables.py's HAND_VERIFIED_COMPARABLES — same figure, not re-derived

# ============================================================================================
# Energy tariffs — the PRICE half of "consumption x tariff" (change
# cost-energy-from-consumption-and-tariff). A tariff is an INPUT, not a constant frozen inside a
# cost figure: to update one, change its value and `as_of` here and re-run this script.
#
# Sourced from the method catalogue (data/master_list_verified/Costing_Method_Catalogue.csv,
# extracted from the AI Guideline form and PM-signed), which records the guideline's rate for each
# energy code with its legal citation. The A&K Tower / Parking Building source workbooks are not in
# this repository (see the change's design D6), so A&K's CONSUMPTION is derived as
# recorded-monthly-cost / tariff — exact by construction, and neutral to every current figure.
ENERGY_TARIFFS = {
    'Electricity': dict(
        unit_price=2_226, quantity_unit='kWh/month', as_of='2025-05-09',
        citation='QD 1279/QD-BCT ngay 09/05/2025 — dien duoi 6kV, don vi hanh chinh su nghiep (2.226 d/kWh)',
        note='Current. Also equals A&K Tower\'s own implied rate (its real 163-row kWh equipment model / cost), '
             'so the derived consumption reconciles exactly.'),
    'Water': dict(
        unit_price=19_786, quantity_unit='m3/month', as_of='2026 (AI Guideline built-up example)',
        citation='SAWACO household-water tariff, built up: base + VAT 5% + PBVMT 30% + VAT-on-PBVMT 8% '
                 '(AI Guideline cites 19,786 VND/m3)',
        note='A&K Tower\'s own m3 and bill rate are not in this repository. A&K\'s consumption below is DERIVED '
             '(recorded cost / this 2026 tariff) — an implied figure, and a lower bound if A&K\'s real ~2020 rate '
             'was below 19,786 VND/m3.'),
    'Diesel (Generator Fuel)': dict(
        unit_price=19_260, quantity_unit='litre/month', as_of='~2020 (A&K Tower budget)',
        citation='DO 0.005S Vung 1 listed price recorded in A&K Tower\'s D4. Chi Phi Dau sheet; the guideline '
                 'says use the DO 0.005S Vung 1 listed price on the budget date',
        note='~2020 rate, STALE for a 2027 budget — the current DO 0.005S Vung 1 listed price should replace it. '
             'Usage basis is per-m2 NFA (design D1); diesel is driven by generator test/backup hours, which do '
             'not obviously scale with floor area — a known limitation, not occupancy-scaled.'),
}

# Parking Building's own source sheet records real consumption AND its own blended rate directly —
# a different building type, kept for reference, never blended into the residential ratio.
PARKING_ENERGY_QUANTITIES = {
    'Electricity': dict(quantity=62_622, quantity_unit='kWh/month', unit_price=3_751, as_of='~2020'),
    'Water': dict(quantity=3_300, quantity_unit='m3/month', unit_price=29_000, as_of='~2020'),
    'Diesel (Generator Fuel)': dict(quantity=523, quantity_unit='litre/month', unit_price=22_000, as_of='~2020'),
}

OPEX_FACTS = [
    dict(project='A&K Tower', category='Electricity', monthly_vnd=136_937_719.17 + 125_272_421.49,
         source='D3a + D3b sheets, "Tổng tiền điện dự kiến Tháp A/B" rows (M162/M158) — Tower A '
                '136,937,719.17 + Tower B 125,272,421.49. Real 163-row equipment load calc '
                '(kWh math: capacity x hours x usage factor x rate=2,226 VND/kWh), independently '
                'verified by reading the underlying FORMULAS, not just cached values.'),
    dict(project='A&K Tower', category='Water', monthly_vnd=30_058_500,
         source='D2. Nước Công Cộng sheet, "Tổng" row — real, itemized by tower (public water, '
                'garden watering, floor washing, pool top-up, 10% loss/leak contingency).'),
    dict(project='A&K Tower', category='Diesel (Generator Fuel)', monthly_vnd=round(71_897_580 / 12),
         source='D4. Chi Phí Dầu sheet, "Tổng" row — 71,897,580 VND is ANNUAL (testing ~12h/year + '
                'backup ~10h/year at 19,260 VND/liter), converted to a monthly-equivalent here for '
                'consistency with the other categories.'),
    dict(project='A&K Tower', category='Pool Salt', monthly_vnd=6_657_000,
         source='D2. Chi phí Muối cho Hồ bơi sheet, "Phương án 2" (Vietnamese-sourced salt, '
                '6,000-8,000 VND/kg) row — real, for a real 634 m³ two-pool total. "Phương án 1" '
                '(imported Jordan salt, 76,080,000/month) also real, not used here — Phương án 2 is '
                'the more standard/representative option, not the premium one.'),
    dict(project='A&K Tower', category='Repairs & Maintenance (materials only)', monthly_vnd=round(33_165_000 / 12),
         source='"A2.1 Thiết lập chi tiết" sheet, row 287 (code ER, "Repairs and Maintenance/ Sửa '
                'chữa & bảo dưỡng") — 33,165,000 VND/year, spare-parts/repair MATERIALS only. '
                'Deliberately narrow: the row\'s own real cell note explains why — "maintenance '
                'CONTRACT costs (e.g. elevator/electrical-system service contracts) use the separate '
                'maintenance fund [quỹ bảo trì — Vietnam\'s legally mandated one-time 2% fund '
                'collected at handover], so they are NOT estimated in the operating fund used to '
                'calculate the management fee," citing Housing Law 2023 Article 150 and Construction '
                'Law Article 3 explicitly. This is why elevator/lighting/system maintenance contracts '
                'don\'t appear anywhere in this tool\'s recurring budget — they legally shouldn\'t.'),
    dict(project='A&K Tower', category='Administrative Expense (office overhead)', monthly_vnd=5_615_438.60,
         source='"A2.1 Thiết lập chi tiết" sheet, row 114 (code EM item 2, "Administrative Expense / '
                'Chi phí quản lý văn phòng của VPBQL") — 67,385,263.16 VND/year. Real, itemized in the '
                'row\'s own cell note: phone/internet, stationery, PRINTER INK, photocopier rental, '
                'postage, drinking water, office maintenance, night-shift-staff supplies (instant '
                'noodles/tea/coffee), business license tax. The general office-overhead bucket that '
                'covers document/invoice printing specifically — doesn\'t fit Staff/Service/Capex/'
                'utility categories, easy to overlook entirely.'),
    # Parking Building — real, but a DIFFERENT building type (parking structure, not residential).
    # Kept for reference; NOT blended into estimate_opex.py's per-NFA ratio (no comparable NFA
    # basis — a parking building's utility profile isn't scaled by residential floor area the same
    # way).
    dict(project='Parking Building', category='Electricity', monthly_vnd=234_895_122,
         source='"Summary Chi phí Điện, Nước, Dầu" sheet — real, labeled monthly average '
                '(62,622 kWh/month @ ~3,751 VND/kWh blended rate). Real, but excludes office-floor '
                'and EV-charging-station electricity per the sheet\'s own note.'),
    dict(project='Parking Building', category='Water', monthly_vnd=95_700_000,
         source='"Summary Chi phí Điện, Nước, Dầu" sheet — real (3,300 m3/month @ 29,000 VND/m3). '
                'Excludes the 22 Shophouses\' own private water usage per the sheet\'s own note.'),
    dict(project='Parking Building', category='Diesel (Generator Fuel)', monthly_vnd=11_506_000,
         source='"Summary Chi phí Điện, Nước, Dầu" sheet — real, labeled monthly average '
                '(523 liters/month @ 22,000 VND/liter).'),
]

# Explicitly NOT extracted, and why — stated so this isn't mistaken for an oversight:
NOT_EXTRACTED = [
    ('Fiato Airport F Zone G2', 'Electricity/Water/Diesel',
     'Identical to A&K Tower\'s numbers to the exact decimal — a copied template, not independent '
     'real data for this property. Would double-count if treated as a second sample.'),
    ('Fiato Airport F Zone MF Pre/Y1/Y2', 'Electricity/Water/Diesel',
     'Same file family as Fiato G2 — not independently checked, but the G2 duplication finding '
     'makes it very unlikely to be independent either.'),
    ('Green Skyline', 'Electricity/Water',
     'Not a direct real-consumption sheet — a comparative estimate against a different reference '
     'building (Estella Heights) by floor-area/unit-count ratio. A real methodology, but not a '
     'number to lift as this property\'s own verified consumption without redoing that comparison.'),
    ('Lumi Prestige & Elite, Lumi Signature', 'Electricity/Water/Diesel',
     'No such sheets exist in either file — only a Garbage Collection sheet.'),
    ('11D Thi Sách', 'all OPEX categories', 'No OPEX-like sheets found anywhere in this file.'),
    ('All 8 files', 'Garbage Collection',
     'Sheets exist ("B3. Thu gom rác") but not yet read for a real total — same "Garbage collection: '
     'NOT FOUND, do not fabricate" gap Fact_MasterRateCard.csv already documents for this category.'),
    ('All 8 files + Fact_MasterRateCard.csv (all domains) + Fact_Capex_Rescanned.csv (1,329 rows)',
     'Access Card / Access Control System',
     'Searched explicitly — sheet names, Capex line items, Service/Staff domain rows — for "thẻ" '
     '(card), "kiểm soát ra vào" (access control), "access card". Genuinely not found anywhere in '
     'this dataset. Not fabricated; could be a one-time developer-provided item, a separate '
     'resident-paid deposit, or just not itemized in these particular files.'),
]


def _safe_print(text):
    """Windows console (cp1252) can't render Vietnamese diacritics — never let a summary print
    crash a run that already wrote its real output successfully."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))


def _split_row(row):
    """Return (quantity, unit, unit_price, price_as_of) for a row, or four blanks.

    Energy categories are split into consumption x tariff: A&K Tower rows use the catalogue tariff
    with consumption derived as cost / tariff; Parking Building rows use their own recorded
    consumption and blended rate. Every other category has no split and gets blanks — its
    MonthlyVND stays the only figure.
    """
    cat, project, monthly = row['category'], row['project'], row['monthly_vnd']
    if project == 'Parking Building' and cat in PARKING_ENERGY_QUANTITIES:
        p = PARKING_ENERGY_QUANTITIES[cat]
        return p['quantity'], p['quantity_unit'], p['unit_price'], p['as_of']
    if cat in ENERGY_TARIFFS:
        t = ENERGY_TARIFFS[cat]
        # The STORED quantity — a fixed figure the estimator reads and multiplies by the tariff
        # (so changing the tariff moves the budget). Derived once as recorded-cost / tariff because
        # the A&K source workbook is not in this repo; written at full float precision so
        # quantity x tariff reproduces the recorded cost exactly (design D6).
        quantity = repr(round(monthly) / t['unit_price'])
        return quantity, t['quantity_unit'], t['unit_price'], t['as_of']
    return '', '', '', ''


def _source_with_tariff(row):
    """For an A&K energy row, append the tariff's citation to the cost provenance so the CSV `Source`
    column carries both halves. Other rows are unchanged."""
    if row['project'] == 'A&K Tower' and row['category'] in ENERGY_TARIFFS:
        t = ENERGY_TARIFFS[row['category']]
        return (f"{row['source']}  TARIFF: {t['unit_price']:,} VND/{t['quantity_unit'].split('/')[0]} "
                f"(as of {t['as_of']}) — {t['citation']}. {t['note']}")
    return row['source']


def main():
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fields = ['Project', 'Category', 'MonthlyVND', 'Quantity', 'Unit', 'UnitPrice', 'PriceAsOf', 'Source', 'RefKey']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in OPEX_FACTS:
            quantity, unit, unit_price, price_as_of = _split_row(row)
            w.writerow(dict(Project=row['project'], Category=row['category'],
                             MonthlyVND=round(row['monthly_vnd']),
                             Quantity=quantity, Unit=unit, UnitPrice=unit_price, PriceAsOf=price_as_of,
                             Source=_source_with_tariff(row),
                             RefKey=reference_projects.key_for_name(row['project']) or ''))
    _safe_print(f'Wrote {len(OPEX_FACTS)} real OPEX facts to {OUT_CSV}')
    _safe_print('Energy tariffs (the price half — edit ENERGY_TARIFFS to update):')
    for cat, t in ENERGY_TARIFFS.items():
        _safe_print(f'  - {cat}: {t["unit_price"]:,} VND/{t["quantity_unit"].split("/")[0]}  (as of {t["as_of"]})')
    _safe_print(f'Explicitly NOT extracted ({len(NOT_EXTRACTED)} entries, see module docstring for why):')
    for project, cats, why in NOT_EXTRACTED:
        _safe_print(f'  - {project} / {cats}: {why}')


if __name__ == '__main__':
    main()
