"""
Estimates OPEX/Utilities (Electricity, Water, Diesel/Generator Fuel, Pool Salt, Repairs &
Maintenance) for a NEW project from data/generation_A_star_schema/Fact_OPEX.csv — real
per-project monthly costs, rescanned directly from source (see rescan_opex_from_source.py for
exactly how/why, including a real broken-formula false alarm, a real cross-file duplication
caught, and why elevator/system maintenance CONTRACTS are deliberately excluded — Vietnamese law
funds those from a separate one-time fund, not the ongoing management fee this models).

Methodology, and its real limits stated plainly, same standard as estimate_capex_qty.py:
  Electricity/Water/Diesel: **consumption × tariff** (change cost-energy-from-consumption-and-tariff,
  the method Savills' costing spec states). A&K Tower's real monthly cost gives a per-m² USAGE
  ratio (kWh / m³ / litre per m² NFA per month, n=1); the TARIFF is a separate, dated input read
  from Fact_OPEX.csv's UnitPrice column. figure = usage_ratio × this project's NFA × tariff × 12.
  The tariff no longer sits frozen inside a cost-per-m² number, so updating it moves the budget;
  a stale tariff is visible on the output instead of silent. Usage stays n=1 and stays labelled —
  this change fixed the price half, not the sample size.
  Repairs & Maintenance / Administrative Expense: still a plain per-m² TotalNFA cost ratio, derived
  from A&K Tower ALONE (n=1) — no consumption/tariff split applies to them.
  In every case Parking Building is real too but a different building type — a parking structure's
  utility profile doesn't scale with residential floor area the same way, so it's shown for
  reference, never blended into the ratio. Repairs & Maintenance here is deliberately narrow —
  materials/spare-parts only, NOT maintenance contracts (elevator, MSB electrical panel, etc.),
  which are legally funded from a separate one-time fund in Vietnam, not the recurring
  management-fee budget.

  Pool Salt: NOT a ratio at all — computed by the method Savills' own costing spec states for it
  (EXENSIVE LOGIC.xlsx, code ESM4), from the project's total pool water VOLUME. See POOL_SALT_*
  below. When the project's volume is unknown the A&K flat figure is used as an explicit,
  labelled fallback, exactly as it was before this method was implemented.
"""
import os
import csv

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OPEX_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_A_star_schema', 'Fact_OPEX.csv')

AK_TOWER_NFA_M2 = 64_124.0  # same figure as master_comparables.py's HAND_VERIFIED_COMPARABLES

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
# 79,884,000 that A&K Tower actually budgeted — 0.9% apart. The flat "real reference" was itself
# this formula, evaluated once, for somebody else's pool. Reusing it for a project with a
# different pool was reusing A&K's volume, not A&K's evidence.
POOL_SALT_KG_PER_M3_MONTH = 2.5           # midpoint of the spec's stated 1-4 kg/m3/month
POOL_SALT_KG_RANGE = (1, 4)               # the stated range, reported alongside every figure
POOL_SALT_PRICE_PER_KG = 6_000            # stated unit price, VND/kg
POOL_SALT_PPM = 4_000                     # stated salinity the consumption figure assumes


def _load_opex_facts():
    facts = {}
    with open(OPEX_CSV, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            entry = dict(monthly_vnd=float(row['MonthlyVND']), source=row['Source'])
            # Consumption/tariff columns — present only for the energy rows (added by the change
            # cost-energy-from-consumption-and-tariff). Absent or blank means "no split for this row".
            up = (row.get('UnitPrice') or '').strip()
            if up:
                entry.update(unit_price=float(up),
                             quantity=float(row['Quantity']) if (row.get('Quantity') or '').strip() else None,
                             quantity_unit=(row.get('Unit') or '').strip() or None,
                             price_as_of=(row.get('PriceAsOf') or '').strip() or None)
            facts.setdefault(row['Project'], {})[row['Category']] = entry
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


def estimate_opex(total_nfa_m2, has_pool=False, pool_volume_m3=None):
    """Returns {category: {...}}.

    Electricity / Water / Diesel are priced as USAGE × TARIFF: a per-m² usage ratio from A&K Tower
    (n=1) times this project's NFA times the tariff (Fact_OPEX.csv's UnitPrice, a dated input). The
    entry carries `usage_per_m2`, `usage_unit`, `tariff`, `tariff_unit`, `tariff_as_of`,
    `tariff_stale`. The tariff cancels for any project run at A&K's own NFA and unchanged rate, so
    every current figure reproduces exactly; change a tariff and the figure moves with it.

    Repairs & Maintenance / Administrative Expense stay a plain A&K per-m² cost ratio (n=1).

    Pool Salt is included only if has_pool is True and is computed from pool_volume_m3 by the spec's
    ESM4 method; when the volume is unknown it falls back to A&K's flat figure and says so. Callers
    rendering Pool Salt should prefer its `method` key — it is not a ratio category."""
    facts = _load_opex_facts()
    ak = facts['A&K Tower']
    parking = facts.get('Parking Building', {})

    result = {}
    for category in RATIO_CATEGORIES:
        ak_row = ak[category]
        ak_monthly = ak_row['monthly_vnd']
        cost_ratio_per_m2 = ak_monthly / AK_TOWER_NFA_M2      # VND/m²/month — the pre-split ratio

        split = category in ENERGY_CATEGORIES and ak_row.get('unit_price') and ak_row.get('quantity')
        if split:
            tariff = ak_row['unit_price']
            q_unit = ak_row.get('quantity_unit') or 'unit/month'     # e.g. 'kWh/month'
            base_unit = q_unit.split('/')[0]                          # 'kWh'
            # A&K's stored monthly quantity (fixed — NOT recomputed from cost each run, so changing
            # the tariff below actually moves the figure). Divided by A&K's NFA for the per-m² ratio.
            usage_per_m2 = ak_row['quantity'] / AK_TOWER_NFA_M2       # base_unit per m² per month
            estimated = usage_per_m2 * total_nfa_m2 * tariff
            cost_ratio_per_m2 = usage_per_m2 * tariff                 # effective VND/m²/month at this tariff
            as_of = ak_row.get('price_as_of')
            year = _tariff_year(as_of)
            stale = year is not None and year < _TARIFF_STALE_BEFORE_YEAR
            project_qty_month = usage_per_m2 * total_nfa_m2
            cost_prov, _, tariff_prov = (ak_row.get('source') or '').partition('  TARIFF: ')
            entry = dict(
                monthly_vnd=round(estimated),
                ratio_per_m2=round(cost_ratio_per_m2, 2),             # kept for existing readers
                n=1,
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
                    f"USAGE (n=1): A&K Tower's {ak_row['quantity']:,.0f} {q_unit} "
                    f"(= its real {ak_monthly:,.0f} VND/month ÷ {tariff:,.0f} VND/{base_unit}, stored fixed) "
                    f"÷ {AK_TOWER_NFA_M2:,.0f} m² NFA = {usage_per_m2:,.4f} {q_unit} per m²; "
                    f"× this project's {total_nfa_m2:,.0f} m² = {project_qty_month:,.0f} {q_unit}. "
                    f"This change split the price out; it did not widen the single-property usage basis. "
                    f"USAGE SOURCE: {cost_prov}  TARIFF: {tariff_prov}"),
                reference_only=None,
            )
        else:
            entry = dict(
                monthly_vnd=round(cost_ratio_per_m2 * total_nfa_m2),
                ratio_per_m2=round(cost_ratio_per_m2, 2),
                n=1,
                source=(f"A&K Tower real: {ak_monthly:,.0f} VND/month ÷ {AK_TOWER_NFA_M2:,.0f} m² NFA = "
                        f"{cost_ratio_per_m2:,.2f} VND/m²/month (n=1 — the only residential property with "
                        f"real, independently-verified data for this category)."),
                reference_only=None,
            )

        if category in parking:
            pk = parking[category]
            ref = (f"Parking Building real (different building type, not blended into the ratio above): "
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
        result['Pool Salt'] = _pool_salt(pool_volume_m3, ak['Pool Salt']['monthly_vnd'])
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


def _pool_salt(pool_volume_m3, ak_flat_monthly):
    volume = _coerce_volume(pool_volume_m3)
    if volume is None:
        return dict(
            monthly_vnd=round(ak_flat_monthly), ratio_per_m2=None, n=1,
            # Vietnamese (change localize-line-level-remarks, 2026-09-15 — was English); internal
            # file citation ("the costing spec") dropped from client-facing text per the same
            # change's principle, kept only as this comment for engineering reference.
            method=(f"DỰ PHÒNG — chưa biết thể tích hồ bơi của dự án này, nên đây là số liệu cố định "
                    f"thực tế của A&K Tower và KHÔNG thay đổi theo quy mô hồ bơi. Có phương pháp tính "
                    f"theo thể tích: nhập Thể tích hồ bơi (m³) tại Project Info để áp dụng. Số liệu cố "
                    f"định này tương ứng với một hồ bơi có thể tích khoảng "
                    f"{ak_flat_monthly / (POOL_SALT_KG_PER_M3_MONTH * POOL_SALT_PRICE_PER_KG):,.0f} m³."),
            source=(f"Số liệu thực tế của A&K Tower (tham chiếu cố định, KHÔNG tính theo NFA): "
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
                f"lít/năm cho hồ 440 m³ nhưng không có đơn giá. Để so sánh, số liệu cố định của A&K "
                f"Tower mà phương pháp này thay thế là {ak_flat_monthly:,.0f} VND/tháng, theo hồ bơi "
                f"thực tế của A&K."),
        reference_only=None,
        pool_volume_m3=volume,
    )
