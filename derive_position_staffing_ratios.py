"""
Derives REAL per-position staffing ratios — how many of each in-house role a residential property
actually employs per 1,000 m² of NFA — and writes them to
data/master_list_verified/Fact_StaffingRatio_ByPosition.csv.

WHY THIS EXISTS. derive_staffing_benchmarks.py already derives a whole-building ratio (headcount per
1,000 m² GFA) from Dim_Property_Residential.csv, but a budget needs to know *which* roles make up that
headcount, not just the total. Until now the in-house roles on the intake form's Staffing Demand sheet
(Property Manager, Chief Engineer, Technician, Customer Service …) carried a fixed seeded default of 1
because nothing tied their headcount to property scale — so a 20,000 m² building and a 120,000 m²
building were both offered one technician.

THE JOIN THAT MAKES IT POSSIBLE. reports/Project_Detail_Lists.xlsx, sheet "Staff Positions by
Project", holds one row per (project, position) with a real Headcount, for 88 operating properties —
extracted from each project's own file. Matching those project names against
Dim_Property_Residential.csv (which carries a real NFA per property) gives a population with BOTH a
per-position headcount and a property size on the same row. That is the population this script
measures.

WHAT IT DOES NOT DO. It does not decide which ratios are safe to use — it reports every role family it
can measure, with its own sample size, and lets the caller apply a threshold. Roles measured on a
handful of properties are reported with that n rather than silently dropped or silently trusted.

Label variance is the main hazard in the source: real projects name the same job many ways
("Technician", "Technician 1", "Kỹ thuật viên 3", "Nhân viên kỹ thuật 7", "Technician 1 / Kỹ thuật
viên 1"), and each is one row with its own headcount. Rows are therefore folded into role FAMILIES by
keyword before any ratio is computed, and the per-project headcounts within a family are summed.
"""
import csv
import os
import statistics

import openpyxl

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
POSITIONS_XLSX = os.path.join(BUDGET_AGENT, 'reports', 'Project_Detail_Lists.xlsx')
PROPERTIES_CSV = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified',
                              'Dim_Property_Residential.csv')
OUT_CSV = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified',
                       'Fact_StaffingRatio_ByPosition.csv')

# Role families, and the keywords that identify them in the source's free-text position names.
# Vietnamese and English variants of one job belong to one family. Order matters: the first family
# whose keyword appears wins, so more specific families must precede more general ones (an
# "Assistant to Chief Engineer" must not be counted as a Chief Engineer).
ROLE_FAMILIES = [
    ('Assistant Chief Engineer', ['trợ lý kỹ sư trưởng', 'assistant to ce', 'assistant to chief engineer',
                                  'trợ lý kst']),
    ('Assistant Property Manager', ['trợ lý quản lý tòa nhà', 'trợ lý trưởng ban', 'assistant to pm',
                                    'assistant to property manager', 'assistant of property manager']),
    ('Chief Engineer', ['kỹ sư trưởng', 'chief engineer']),
    ('Property Manager', ['quản lý tòa nhà', 'property manager', 'trưởng ban quản lý',
                          'giám đốc quản lý']),
    ('Operations Manager', ['quản lý vận hành', 'operations manager', 'giám đốc vận hành']),
    ('Technical Supervisor', ['giám sát kỹ thuật', 'technical supervisor', 'tổ trưởng kỹ thuật']),
    ('Shift Leader', ['trưởng ca', 'shift leader']),
    ('Technician', ['kỹ thuật viên', 'nhân viên kỹ thuật', 'technician']),
    ('Customer Service Supervisor', ['giám sát chăm sóc khách hàng', 'customer service supervisor',
                                     'trưởng nhóm chăm sóc', 'quản lý bộ phận cskh',
                                     'customer service leader', 'customer service teamleader',
                                     'customer service manager']),
    ('Customer Service', ['chăm sóc khách hàng', 'customer service', 'customer services',
                          'customer service officer']),
    ('Reception', ['lễ tân', 'reception', 'tiền sảnh']),
    ('Amenities Attendant', ['nhân viên tiện ích', 'amenities attendant', 'amenities attendant',
                             'đội trưởng đội tiện ích', 'facilities - attendant']),
    ('Pool Attendant', ['hồ bơi', 'pool attendant', 'pool/ gym attendant', 'gym - pool attendant']),
    ('Building Executive', ['giám sát chất lượng dịch vụ', 'building executive', 'giám sát dịch vụ',
                            'giám sát vận hành']),
    ('Accountant', ['kế toán', 'accountant']),
    ('Cashier', ['thủ quỹ', 'cashier', 'thu ngân']),
    ('Admin', ['hành chính', 'admin', 'thư ký']),
    ('Procurement', ['thu mua', 'procurement', 'purchasing']),
]


def _family(position_name):
    text = str(position_name or '').lower()
    for family, keywords in ROLE_FAMILIES:
        if any(k in text for k in keywords):
            return family
    return None


def _property_nfa():
    """{normalised property name: NFA in m²} for every property carrying a usable NFA."""
    out = {}
    with open(PROPERTIES_CSV, encoding='utf-8-sig') as fh:
        for row in csv.DictReader(fh):
            name = str(row.get('Name') or '').strip().lower()
            try:
                nfa = float(row.get('NFA_m2'))
            except (TypeError, ValueError):
                continue
            if name and nfa > 0:
                out[name] = nfa
    return out


def _headcount_by_project_and_family(nfa_by_name):
    """{family: {property name: total headcount}} over properties that also have an NFA."""
    ws = openpyxl.load_workbook(POSITIONS_XLSX, data_only=True)['Staff Positions by Project']
    out = {}
    for row in range(5, ws.max_row + 1):
        name = ws.cell(row=row, column=2).value
        position = ws.cell(row=row, column=3).value
        headcount = ws.cell(row=row, column=4).value
        if not (name and position) or not isinstance(headcount, (int, float)):
            continue
        key = str(name).strip().lower()
        if key not in nfa_by_name:
            continue
        family = _family(position)
        if family:
            out.setdefault(family, {}).setdefault(key, 0.0)
            out[family][key] += float(headcount)
    return out


def derive():
    """[{Role, N_Properties, MedianHeadcount, ...}] one row per measurable role family."""
    nfa_by_name = _property_nfa()
    by_family = _headcount_by_project_and_family(nfa_by_name)

    results = []
    for family, _ in ROLE_FAMILIES:
        per_property = by_family.get(family)
        if not per_property:
            continue
        headcounts = sorted(per_property.values())
        ratios = sorted(hc / nfa_by_name[name] * 1000.0 for name, hc in per_property.items())
        results.append({
            'Role': family,
            'N_Properties': len(per_property),
            'MedianHeadcount': round(statistics.median(headcounts), 2),
            'MedianPer1000m2NFA': round(statistics.median(ratios), 4),
            'MeanPer1000m2NFA': round(statistics.fmean(ratios), 4),
            'P25Per1000m2NFA': round(ratios[len(ratios) // 4], 4),
            'P75Per1000m2NFA': round(ratios[(3 * len(ratios)) // 4], 4),
            'MinHeadcount': round(headcounts[0], 2),
            'MaxHeadcount': round(headcounts[-1], 2),
        })
    return results, len(nfa_by_name), len({n for f in by_family.values() for n in f})


def main():
    results, n_props_with_nfa, n_matched = derive()
    header = ['Role', 'N_Properties', 'MedianHeadcount', 'MedianPer1000m2NFA', 'MeanPer1000m2NFA',
              'P25Per1000m2NFA', 'P75Per1000m2NFA', 'MinHeadcount', 'MaxHeadcount']
    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as fh:
        fh.write(f'# Per-position staffing ratios derived by derive_position_staffing_ratios.py\n')
        fh.write(f'# Source: reports/Project_Detail_Lists.xlsx "Staff Positions by Project" (real\n')
        fh.write(f'#   headcount per project per position) joined by property name to\n')
        fh.write(f'#   Dim_Property_Residential.csv (real NFA). {n_matched} properties carry both.\n')
        fh.write(f'# Ratios are headcount per 1,000 m2 of NFA. Median is the figure to use - this\n')
        fh.write(f'#   population is skewed and the mean runs well above it on several roles.\n')
        fh.write(f'# N_Properties is per ROLE and varies: a role is not present at every property.\n')
        fh.write(f'#   Check it before trusting a ratio; some roles here are measured on a handful.\n')
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f'Properties with a usable NFA: {n_props_with_nfa}')
    print(f'Properties matched to a headcount list: {n_matched}')
    print()
    print(f'{"Role":30}{"n":>4}{"med hc":>9}{"per 1,000 m2 NFA":>19}{"P25-P75":>18}')
    print('-' * 80)
    for row in results:
        band = f'{row["P25Per1000m2NFA"]:.3f}-{row["P75Per1000m2NFA"]:.3f}'
        print(f'  {row["Role"]:28}{row["N_Properties"]:>4}{row["MedianHeadcount"]:>9.1f}'
              f'{row["MedianPer1000m2NFA"]:>19.4f}{band:>18}')
    print()
    print('Written:', OUT_CSV)


if __name__ == '__main__':
    main()
