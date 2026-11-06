"""
Estimates OPEX/Utilities (Electricity, Water, Diesel/Generator Fuel, Pool Salt, Repairs &
Maintenance) for a NEW project from data/generation_A_star_schema/Fact_OPEX.csv — real
per-project monthly costs, rescanned directly from source (see rescan_opex_from_source.py for
exactly how/why, including a real broken-formula false alarm, a real cross-file duplication
caught, and why elevator/system maintenance CONTRACTS are deliberately excluded — Vietnamese law
funds those from a separate one-time fund, not the ongoing management fee this models).

Methodology, and its real limits stated plainly, same standard as estimate_capex_qty.py:
  Electricity/Water/Diesel: **consumption × tariff** (change cost-energy-from-consumption-and-tariff,
  the method Savills' costing spec states). USAGE per m² NFA per month (kWh / m³ / litre) is the median of
  the hand-checked real projects in Ref_UtilityUsage.csv after an IQR fence (utility_usage.py, change
  widen-utility-and-capex-sources); with fewer than utility_usage.MIN_PROJECTS projects it falls back to the
  utilities base project (n=1) and says so. The TARIFF is the dated public price of each budget month
  (Ref_UtilityTariffs.csv: EVN for electricity, before VAT; SAWACO water and the listed diesel price, with
  VAT). figure = usage_ratio × this project's NFA × tariff.
  Repairs & Maintenance / Administrative Expense: still a plain per-m² TotalNFA cost ratio, derived
  from the utilities base project ALONE (n=1) — no consumption/tariff split applies to them.
  In every case the parking reference is real too but a different building type — a parking structure's
  utility profile doesn't scale with residential floor area the same way, so it's shown for
  reference, never blended into the ratio. Repairs & Maintenance here is deliberately narrow —
  materials/spare-parts only, NOT maintenance contracts (elevator, MSB electrical panel, etc.),
  which are legally funded from a separate one-time fund in Vietnam, not the recurring
  management-fee budget.

  Pool Salt: NOT a ratio at all — computed by the method Savills' own costing spec states for it
  (EXENSIVE LOGIC.xlsx, code ESM4), from the project's total pool water VOLUME. See POOL_SALT_*
  below. When the project's volume is unknown the base project's flat figure is used as an explicit,
  labelled fallback, exactly as it was before this method was implemented.
"""
import os
import csv

import reference_projects
import utility_usage
import utility_tariffs as ut

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OPEX_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_A_star_schema', 'Fact_OPEX.csv')

# The utilities base (the one residential project whose real monthly costs and quantities give the per-m² usage
# ratios, n=1) and the parking reference (shown beside it, never blended) are the registry rows carrying the roles
# utilities_base and parking_base; their NFA comes from the registry too (change reference-projects-by-key).
_SKIPPED_REPORTED = set()


def _base():
    return reference_projects.one_by_role(reference_projects.ROLE_UTILITIES_BASE)


def _parking():
    rows = reference_projects.by_role(reference_projects.ROLE_PARKING_BASE)
    return rows[0] if rows else None

RATIO_CATEGORIES = ['Electricity', 'Water', 'Diesel (Generator Fuel)', 'Repairs & Maintenance (materials only)',
                     'Administrative Expense (office overhead)']

# The three the costing spec prices as consumption × tariff (change
# cost-energy-from-consumption-and-tariff). Their Fact_OPEX.csv rows carry Quantity/Unit/UnitPrice/
# PriceAsOf; the other two ratio categories do not and stay plain cost ratios.
ENERGY_CATEGORIES = ['Electricity', 'Water', 'Diesel (Generator Fuel)']

# A tariff older than this is flagged "stale" on the generated budget. The pipeline targets the
# 2027 cycle; a rate that predates the budget year is one a reader should double-check.
_TARIFF_STALE_BEFORE_YEAR = 2027

# ESM4 — pool chemicals. input/logic/EXENSIVE LOGIC.xlsx states the whole method for this code:
# salt-electrolysis pools are held at >=4,000 ppm and consume 1-4 kg of salt per m3 of water per
# month at 6,000d/kg. Its worked example — "ho boi nguoi lon 320m3, ho boi tre em 120m3 thi tong
# the tich nuoc ho boi khoang 440m3" — makes the driver total water VOLUME summed over every pool,
# not surface area. The range is 4x wide because consumption depends on bather load, backwash
# frequency and rainfall dilution, none of which this pipeline captures; the midpoint is used and
# the range is reported on every figure so nobody mistakes it for a precise number.
#
# Why this replaced a flat figure: 440 m3 x 2.5 kg x 6,000 x 12 = 79,200,000, against the
# 79,884,000 that the utilities base project actually budgeted — 0.9% apart. The flat "real reference" was itself
# this formula, evaluated once, for somebody else's pool. Reusing it for a project with a
# different pool was reusing the base project's volume, not its evidence.
POOL_SALT_KG_PER_M3_MONTH = 2.5           # midpoint of the spec's stated 1-4 kg/m3/month
POOL_SALT_KG_RANGE = (1, 4)               # the stated range, reported alongside every figure
POOL_SALT_PRICE_PER_KG = 6_000            # stated unit price, VND/kg
POOL_SALT_PPM = 4_000                     # stated salinity the consumption figure assumes


def _load_opex_facts():
    """{RefKey: {category: entry}}. Rows whose RefKey is blank or unknown are skipped and counted once in the run log
    (the file is keyed by RefKey since change reference-projects-by-key; the Project column is a label)."""
    facts = {}
    known = set(reference_projects.keys())
    skipped = 0
    with open(OPEX_CSV, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if 'RefKey' not in (reader.fieldnames or []):
            raise RuntimeError(f'{os.path.basename(OPEX_CSV)} has no RefKey column; run migrate_reference_keys.py.')
        for row in reader:
            key = (row.get('RefKey') or '').strip()
            if key not in known:
                skipped += 1
                continue
            entry = dict(monthly_vnd=float(row['MonthlyVND']), source=row['Source'])
            # Consumption/tariff columns — present only for the energy rows (added by the change
            # cost-energy-from-consumption-and-tariff). Absent or blank means "no split for this row".
            up = (row.get('UnitPrice') or '').strip()
            if up:
                entry.update(unit_price=float(up),
                             quantity=float(row['Quantity']) if (row.get('Quantity') or '').strip() else None,
                             quantity_unit=(row.get('Unit') or '').strip() or None,
                             price_as_of=(row.get('PriceAsOf') or '').strip() or None)
            facts.setdefault(key, {})[row['Category']] = entry
    if skipped and OPEX_CSV not in _SKIPPED_REPORTED:
        _SKIPPED_REPORTED.add(OPEX_CSV)
        print(f'Utilities: bỏ qua {skipped} dòng không có RefKey trong {os.path.basename(OPEX_CSV)}.')
    return facts


def _tariff_year(price_as_of):
    """First 4-digit run in a PriceAsOf string, or None. '2025-05-09' -> 2025, '~2020 (...)' -> 2020."""
    if not price_as_of:
        return None
    digits = ''
    for ch in price_as_of:
        if ch.isdigit():
            digits += ch
            if len(digits) == 4:
                return int(digits)
        else:
            digits = ''
    return None


def _dated_price(category, period_months, water_group, rows):
    """Electricity, water and diesel prices for each budget month, from Ref_UtilityTariffs.csv (change
    apply-head-of-pm-decisions-2026-10, group 2; electricity added by change widen-utility-and-capex-sources).
    Electricity is the EVN rate before VAT (the callers add each month's VAT, as before); water and diesel
    include VAT. Returns dict(prices, as_of, unit, provenance, ...)."""
    if category == 'Electricity':
        line = ut.LineTariff(ut.ELECTRICITY, category=ut.CAT_E_LT6, rows=rows)
        month_prices = [line.month(y, m) for y, m in period_months]
        base_rows = [mp.rows['base'] for mp in month_prices]
        return dict(prices=[mp.net() for mp in month_prices], unit='VND/kWh', as_of=base_rows[0]['effective_from'],
                    provenance=base_rows[0]['legal_basis'], group=ut.CAT_E_LT6,
                    provenance_by_month=[r['legal_basis'] for r in base_rows])
    if category == 'Water':
        cat, is_default = ut.water_group_category(water_group)
        line = ut.LineTariff(ut.WATER, category=cat, region=ut.HCMC, rows=rows)
        month_prices = [line.month(y, m) for y, m in period_months]
        base_row = month_prices[0].rows['base']
        return dict(prices=[mp.gross() for mp in month_prices], unit='VND/m3', as_of=base_row['effective_from'],
                    provenance=base_row['legal_basis'], group=cat, group_is_default=is_default,
                    vat_bvmt=[mp.wastewater_vat_pct for mp in month_prices], vat_water=month_prices[0].vat_pct,
                    wastewater_pct=month_prices[0].wastewater_pct)
    d_prices = [ut.diesel_price(y, m, rows=rows) for y, m in period_months]
    listed = d_prices[0].rows['listed_price']
    return dict(prices=[d.gross() for d in d_prices], unit='VND/l', as_of=listed['effective_from'],
                provenance=listed['legal_basis'], listed=d_prices[0].listed, listed_vat=d_prices[0].listed_vat_pct,
                vat_by_month=[d.vat_pct for d in d_prices])


def estimate_opex(total_nfa_m2, has_pool=False, pool_volume_m3=None, period_months=None, water_group=None,
                  tariff_rows=None):
    """Returns {category: {...}}.

    period_months: the twelve (year, month) of the budget period. When given, Water and Diesel are priced from
    the dated tariff file month by month (water by `water_group`, blank = business); `monthly_vnd_by_month`
    carries the twelve full-occupancy amounts and `monthly_vnd` their average. When None (older callers and
    tests) the Fact_OPEX.csv tariff is used as before.

    Electricity / Water / Diesel are priced as USAGE × TARIFF: a per-m² usage ratio from the utilities base project
    (n=1) times this project's NFA times the tariff (Fact_OPEX.csv's UnitPrice, a dated input). The
    entry carries `usage_per_m2`, `usage_unit`, `tariff`, `tariff_unit`, `tariff_as_of`,
    `tariff_stale`. The tariff cancels for any project run at the base project's own NFA and unchanged rate, so
    every current figure reproduces exactly; change a tariff and the figure moves with it.

    Repairs & Maintenance / Administrative Expense stay a plain base-project per-m² cost ratio (n=1).

    Pool Salt is included only if has_pool is True and is computed from pool_volume_m3 by the spec's
    ESM4 method; when the volume is unknown it falls back to the base project's flat figure and says so. Callers
    rendering Pool Salt should prefer its `method` key — it is not a ratio category."""
    facts = _load_opex_facts()
    base = _base()
    base_name, base_nfa = base['name'], base['nfa']
    if base['key'] not in facts:
        raise RuntimeError(f"{os.path.basename(OPEX_CSV)} has no rows for the utilities base {base['key']}.")
    ak = facts[base['key']]
    parking_row = _parking()
    parking = facts.get(parking_row['key'], {}) if parking_row else {}
    parking_name = parking_row['name'] if parking_row else 'the parking reference'

    result = {}
    for category in RATIO_CATEGORIES:
        ak_row = ak[category]
        ak_monthly = ak_row['monthly_vnd']
        cost_ratio_per_m2 = ak_monthly / base_nfa             # VND/m²/month — the pre-split ratio

        split = category in ENERGY_CATEGORIES and ak_row.get('unit_price') and ak_row.get('quantity')
        if split:
            tariff = ak_row['unit_price']
            q_unit = ak_row.get('quantity_unit') or 'unit/month'     # e.g. 'kWh/month'
            base_unit = q_unit.split('/')[0]                          # 'kWh'
            # The base's stored monthly quantity (fixed — NOT recomputed from cost each run, so changing
            # the tariff below actually moves the figure). Divided by the base's NFA for the per-m² ratio.
            base_usage_per_m2 = ak_row['quantity'] / base_nfa         # base_unit per m² per month
            bench = utility_usage.benchmark(category)
            usage_per_m2 = bench['median'] if bench['enough'] else base_usage_per_m2
            usage_n = bench['n'] if bench['enough'] else 1
            dated = (_dated_price(category, period_months, water_group, tariff_rows)
                     if period_months else None)
            ak_tariff = tariff                                        # the base's own price, behind its stored quantity
            if dated:
                tariff = dated['prices'][0]                           # shown price: the first budget month's
            estimated = usage_per_m2 * total_nfa_m2 * (sum(dated['prices']) / 12 if dated else tariff)
            cost_ratio_per_m2 = usage_per_m2 * tariff                 # effective VND/m²/month at this tariff
            as_of = dated['as_of'].isoformat() if dated else ak_row.get('price_as_of')
            year = _tariff_year(as_of)
            stale = year is not None and year < _TARIFF_STALE_BEFORE_YEAR
            project_qty_month = usage_per_m2 * total_nfa_m2
            cost_prov, _, tariff_prov = (ak_row.get('source') or '').partition('  TARIFF: ')
            if dated:
                tariff_prov = dated['provenance']
            if bench['enough']:
                usage_text = (f"USAGE (median of {usage_n} hand-checked projects, Ref_UtilityUsage.csv, IQR fence "
                              f"{utility_usage.IQR_FENCE:g}; dropped as outliers: "
                              f"{', '.join(p for p, _ in bench['dropped']) or 'none'}): {usage_per_m2:,.4f} {q_unit} "
                              f"per m²; × this project's {total_nfa_m2:,.0f} m² = {project_qty_month:,.0f} {q_unit}. "
                              f"Projects in the median (store project id: {q_unit} per m²): "
                              f"{', '.join(f'{p} {v:,.4f}' for p, v in bench['kept'])}.")
            else:
                usage_text = (f"USAGE (n=1, fallback: {bench['reason']}): {base_name}'s {ak_row['quantity']:,.0f} "
                              f"{q_unit} (= its real {ak_monthly:,.0f} VND/month ÷ {ak_tariff:,.0f} VND/{base_unit}, "
                              f"stored fixed) ÷ {base_nfa:,.0f} m² NFA = {usage_per_m2:,.4f} {q_unit} per m²; "
                              f"× this project's {total_nfa_m2:,.0f} m² = {project_qty_month:,.0f} {q_unit}. "
                              f"USAGE SOURCE: {cost_prov}")
            entry = dict(
                monthly_vnd=round(estimated),
                ratio_per_m2=round(cost_ratio_per_m2, 2),             # kept for existing readers
                n=usage_n,
                usage_basis='benchmark' if bench['enough'] else 'fallback',
                usage_projects=bench['kept'] if bench['enough'] else [],
                usage_dropped=bench['dropped'],
                usage_fallback_reason=None if bench['enough'] else bench['reason'],
                usage_per_m2=round(usage_per_m2, 6),
                usage_unit=q_unit,
                project_quantity_month=round(project_qty_month, 1),
                tariff=tariff,
                tariff_unit=f'VND/{base_unit}',
                tariff_as_of=as_of,
                tariff_stale=bool(stale),
                tariff_provenance=tariff_prov or None,
                usage_provenance=cost_prov or None,
                source=(
                    f"CONSUMPTION × TARIFF — the method Savills' costing spec states for {category}. "
                    f"{usage_text}  TARIFF: {tariff_prov}"),
                reference_only=None,
            )
            if dated:
                entry['monthly_vnd_by_month'] = [round(usage_per_m2 * total_nfa_m2 * p) for p in dated['prices']]
                entry['tariff_by_month'] = dated['prices']
                entry['dated'] = {k: v for k, v in dated.items() if k != 'prices'}
        else:
            entry = dict(
                monthly_vnd=round(cost_ratio_per_m2 * total_nfa_m2),
                ratio_per_m2=round(cost_ratio_per_m2, 2),
                n=1,
                source=(f"{base_name} real: {ak_monthly:,.0f} VND/month ÷ {base_nfa:,.0f} m² NFA = "
                        f"{cost_ratio_per_m2:,.2f} VND/m²/month (n=1 — the only residential property with "
                        f"real, independently-verified data for this category)."),
                reference_only=None,
            )

        if category in parking:
            pk = parking[category]
            ref = (f"{parking_name} real (different building type, not blended into the ratio above): "
                   f"{pk['monthly_vnd']:,.0f} VND/month")
            if pk.get('unit_price') and pk.get('quantity'):
                pu = (pk.get('quantity_unit') or '').split('/')[0]
                ref += (f" = {pk['quantity']:,.0f} {pk.get('quantity_unit')} × {pk['unit_price']:,.0f} "
                        f"VND/{pu} (its own blended rate).")
            else:
                ref += " flat."
            entry['reference_only'] = ref
        result[category] = entry

    if has_pool and 'Pool Salt' in ak:
        result['Pool Salt'] = _pool_salt(pool_volume_m3, ak['Pool Salt']['monthly_vnd'], base_name)
    return result


def _coerce_volume(value):
    """Pool Volume comes off a spreadsheet cell, so it can be a number, a string a user typed, or
    blank. Anything that is not a positive number means 'not known' — which selects the fallback
    rather than silently costing a zero-volume pool."""
    try:
        volume = float(value)
    except (TypeError, ValueError):
        return None
    return volume if volume > 0 else None


def _pool_salt(pool_volume_m3, ak_flat_monthly, base_name='dự án tham chiếu'):
    volume = _coerce_volume(pool_volume_m3)
    if volume is None:
        return dict(
            monthly_vnd=round(ak_flat_monthly), ratio_per_m2=None, n=1,
            # Vietnamese (change localize-line-level-remarks, 2026-09-15 — was English); internal
            # file citation ("the costing spec") dropped from client-facing text per the same
            # change's principle, kept only as this comment for engineering reference.
            method=(f"DỰ PHÒNG — chưa biết thể tích hồ bơi của dự án này, nên đây là số liệu cố định "
                    f"thực tế của {base_name} và KHÔNG thay đổi theo quy mô hồ bơi. Có phương pháp tính "
                    f"theo thể tích: nhập Thể tích hồ bơi (m³) tại Project Info để áp dụng. Số liệu cố "
                    f"định này tương ứng với một hồ bơi có thể tích khoảng "
                    f"{ak_flat_monthly / (POOL_SALT_KG_PER_M3_MONTH * POOL_SALT_PRICE_PER_KG):,.0f} m³."),
            source=(f"Số liệu thực tế của {base_name} (tham chiếu cố định, KHÔNG tính theo NFA): "
                    f"{ak_flat_monthly:,.0f} VND/tháng."),
            # The client deliverable's wording names no project (change apply-head-of-pm-decisions-2026-10, D13);
            # the analysis keeps `method` / `source`.
            method_client=(f"DỰ PHÒNG — chưa biết thể tích hồ bơi của dự án này, nên đây là số liệu cố định "
                           f"thực tế của một dự án tham chiếu và KHÔNG thay đổi theo quy mô hồ bơi. Có phương pháp "
                           f"tính theo thể tích: nhập Thể tích hồ bơi (m³) tại Project Info để áp dụng. Số liệu cố "
                           f"định này tương ứng với một hồ bơi có thể tích khoảng "
                           f"{ak_flat_monthly / (POOL_SALT_KG_PER_M3_MONTH * POOL_SALT_PRICE_PER_KG):,.0f} m³."),
            source_client=(f"Số liệu thực tế của dự án tham chiếu (tham chiếu cố định, KHÔNG tính theo NFA): "
                           f"{ak_flat_monthly:,.0f} VND/tháng."),
            reference_only=None, pool_volume_m3=None,
        )
    monthly = volume * POOL_SALT_KG_PER_M3_MONTH * POOL_SALT_PRICE_PER_KG
    low = volume * POOL_SALT_KG_RANGE[0] * POOL_SALT_PRICE_PER_KG
    high = volume * POOL_SALT_KG_RANGE[1] * POOL_SALT_PRICE_PER_KG
    return dict(
        monthly_vnd=round(monthly), ratio_per_m2=None, n='n/a (stated method, not a sample)',
        method=(f"= {volume:,.0f} m³ tổng thể tích nước hồ bơi x {POOL_SALT_KG_PER_M3_MONTH} kg "
                f"muối/m³/tháng x {POOL_SALT_PRICE_PER_KG:,} VND/kg = {monthly:,.0f} VND/tháng "
                f"({monthly * 12:,.0f} VND/năm)."),
        source=(f"Phương pháp và đơn giá theo đúng tiêu chuẩn định giá riêng của Savills cho hạng mục "
                f"này: hồ bơi điện phân muối duy trì ở mức {POOL_SALT_PPM:,} ppm tiêu thụ "
                f"{POOL_SALT_KG_RANGE[0]}-{POOL_SALT_KG_RANGE[1]} kg/m³/tháng với đơn giá "
                f"{POOL_SALT_PRICE_PER_KG:,} VND/kg. {POOL_SALT_KG_PER_M3_MONTH} kg là điểm giữa của "
                f"khoảng này, nên biên độ trung thực cho dự án này là {low * 12:,.0f} đến "
                f"{high * 12:,.0f} VND/năm — mức tiêu thụ thực tế phụ thuộc vào lượng người sử dụng, "
                f"tần suất xả rửa lọc và độ pha loãng do mưa, không có yếu tố nào trong số này được "
                f"thu thập làm đầu vào. Axit KHÔNG được tính vào đây: tiêu chuẩn nêu khoảng 60 "
                f"lít/năm cho hồ 440 m³ nhưng không có đơn giá. Để so sánh, số liệu cố định của {base_name} "
                f"mà phương pháp này thay thế là {ak_flat_monthly:,.0f} VND/tháng, theo hồ bơi "
                f"thực tế của dự án đó."),
        source_client=(f"Phương pháp và đơn giá theo đúng tiêu chuẩn định giá riêng của Savills cho hạng mục "
                       f"này: hồ bơi điện phân muối duy trì ở mức {POOL_SALT_PPM:,} ppm tiêu thụ "
                       f"{POOL_SALT_KG_RANGE[0]}-{POOL_SALT_KG_RANGE[1]} kg/m³/tháng với đơn giá "
                       f"{POOL_SALT_PRICE_PER_KG:,} VND/kg. {POOL_SALT_KG_PER_M3_MONTH} kg là điểm giữa của "
                       f"khoảng này, nên biên độ trung thực cho dự án này là {low * 12:,.0f} đến "
                       f"{high * 12:,.0f} VND/năm — mức tiêu thụ thực tế phụ thuộc vào lượng người sử dụng, "
                       f"tần suất xả rửa lọc và độ pha loãng do mưa, không có yếu tố nào trong số này được "
                       f"thu thập làm đầu vào. Axit KHÔNG được tính vào đây: tiêu chuẩn nêu khoảng 60 "
                       f"lít/năm cho hồ 440 m³ nhưng không có đơn giá. Để so sánh, số liệu cố định của dự án "
                       f"tham chiếu mà phương pháp này thay thế là {ak_flat_monthly:,.0f} VND/tháng."),
        reference_only=None,
        pool_volume_m3=volume,
    )
