"""
Answers a real gap flagged when the Capex sheet shipped: Qty is blank by design (no quantity was
ever derived from real data — see generate_project_output.py's build_capex_sheet docstring), so
Subtotal = Qty * UnitPrice is correctly 0 until a PM fills it in. This script investigates whether
a real quantity CAN be derived instead of left blank, from two different real sources, and reports
both honestly rather than picking one silently.

STUDY 1 — the old 8 real project files (data/generation_A_star_schema/Fact_Capex.csv)
  This is the ONLY place actual observed Capex quantities exist in this project — 738 real
  line-item rows (laptops, CCTV, PCCC gear, ...) pulled from each project's own "B7. Chi phí Trang
  thiết bị MO" sheet. Deduplicated to the real distinct projects (Fact_Capex/Dim_Project carry
  "__repaired" duplicate rows), joined to VERIFIED TotalNFA from generation_B_verified/
  Dim_Property_v2_verified.csv (Generation A's own Dim_Project scale columns are known-buggy —
  several projects share an identical placeholder GFA/NFA value, see docstring note below).
  Result: Qty per 1,000 m² TotalNFA, by Capex category. Small N (up to 6 projects have both
  capex data and clean NFA) but every number traces to a real observed quantity.

STUDY 2 — the new ~150-project Master List (data/master_list_verified/)
  Has NO capex data at all — it was never asked about equipment. What it has that the old 8 files
  don't is a much larger, more reliable population of real Headcount (92 properties) and other
  scale drivers. Study 2 is therefore necessarily a two-hop estimate, presented as such: (1) the
  Qty-per-Headcount ratio, anchored to the ONE project overlapping both datasets with a real
  headcount (Green Skyline, n=1 — stated plainly, not disguised as a bigger sample), applied to
  (2) a NEW prospect's headcount, itself estimated from the Master List's own real headcount-per-
  1,000m² distribution (already computed in derive_staffing_benchmarks.py) when the prospect
  doesn't have a real headcount yet. Every number's provenance is kept visible in the output so a
  reader can see exactly how thin the n=1 anchor is, rather than a single blended "confidence".

Neither study is wired into generate_project_output.py's Capex sheet yet — this is the research
step, matching the pattern for every other derived number this session (Comparison sheet reality
checks, staffing benchmarks): compute it, show the real sample sizes, let it be reviewed before it
starts feeding a number a PM would trust.
"""
import os
import csv
import statistics

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GEN_A = os.path.join(BUDGET_AGENT, 'data', 'generation_A_star_schema')
GEN_B = os.path.join(BUDGET_AGENT, 'data', 'generation_B_verified')
MASTER_LIST = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified')
OUT_XLSX = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified', 'Capex_Qty_Estimation_Study.xlsx')

# Real project name -> verified TotalNFA (m2), from generation_B_verified/Dim_Property_v2_verified.csv,
# read 2026-08-12 this session. Deliberately NOT read from Generation A's Dim_Project.csv: that
# table's GFA_m2/NFA_m2 columns are broken for several projects (11D Thi Sach, A&K Tower, and both
# Fiato rows all show the identical placeholder NFA_m2=59865.9 -- a parsing fallback, not a real
# per-project number) and TotalApartments actually holds an NFA-shaped value, not a unit count.
VERIFIED_NFA = {
    '11d thi sách': 16783.14,
    'a&k tower': 64124,
    'lumi prestige': 134117.4,
    'lumi signature': 195269.5,
    'green skyline': 99252.45,
    'fiato airport - f zone g2': 35836.27,
    # Fiato 605 (MF Pre/Y1/Y2) has no TotalNFA in the verified table -- ApartmentNFA only, excluded
    # from the NFA-ratio study rather than substituting a different figure for a different metric.
}
# Green Skyline's real headcount, from data/master_list_verified/Dim_Property_Residential.csv --
# the ONLY one of the old 8 projects that also appears in the new Master List with a real headcount.
GREEN_SKYLINE_HEADCOUNT = 21


def match_verified_nfa(project_name):
    name_low = project_name.lower()
    for key, nfa in VERIFIED_NFA.items():
        if key in name_low:
            return nfa
    return None


def load_generation_a():
    with open(os.path.join(GEN_A, 'Dim_Equipment.csv'), encoding='utf-8-sig') as f:
        equipment = {r['EquipmentKey']: r for r in csv.DictReader(f)}
    with open(os.path.join(GEN_A, 'Dim_Project.csv'), encoding='utf-8-sig') as f:
        projects = {r['ProjectKey']: r for r in csv.DictReader(f)}
    with open(os.path.join(GEN_A, 'Fact_Capex.csv'), encoding='utf-8-sig') as f:
        capex = list(csv.DictReader(f))
    return equipment, projects, capex


def dedupe_project_keys(projects):
    """Fact_Capex has one row set per ProjectKey, and Dim_Project has a '__repaired' duplicate
    ProjectKey for most real files -- same source file, same real capex, counted twice if not
    deduped. Keeps the non-'__repaired' key per distinct real project name."""
    seen = {}
    for key, p in projects.items():
        name = p['ProjectName'].replace('__repaired', '').strip()
        is_repaired = '__repaired' in p['ProjectName'] or '__repaired' in p['SourceFile']
        if name not in seen or (seen[name][1] and not is_repaired):
            seen[name] = (key, is_repaired)
    return {name: key for name, (key, _) in seen.items()}


def study_1_nfa_ratio():
    equipment, projects, capex = load_generation_a()
    name_to_key = dedupe_project_keys(projects)

    # category totals per deduped project
    cat_qty_by_project = {}  # {project_name: {category: qty}}
    for name, key in name_to_key.items():
        nfa = match_verified_nfa(name)
        if nfa is None:
            continue
        totals = {}
        for row in capex:
            if row['ProjectKey'] != key:
                continue
            eq = equipment.get(row['EquipmentKey'])
            if not eq:
                continue
            item_name = eq['ItemName']
            # "Dự phòng phí" (contingency fee) rows hold a VND amount in the Quantity column and a
            # percentage (e.g. 0.03) in UnitPrice -- not a real item count. One such row (183,848,000
            # "units") is enough to blow a whole category's average up by 6 orders of magnitude if
            # not excluded; this is a genuine schema mismatch in the source ETL, not a real outlier.
            if 'dự phòng' in item_name.lower() or 'contingency' in item_name.lower():
                continue
            cat = eq['CapexCategory']
            try:
                qty = float(row['Quantity'])
            except (ValueError, TypeError):
                continue
            totals[cat] = totals.get(cat, 0) + qty
        if totals:
            cat_qty_by_project[name] = (nfa, totals)

    print(f"Study 1: {len(cat_qty_by_project)} of the old 8 projects have both real Capex line "
          f"items and a verified NFA: {list(cat_qty_by_project.keys())}")

    all_categories = sorted({c for _, totals in cat_qty_by_project.values() for c in totals})
    ratio_rows = []
    for cat in all_categories:
        per_1000 = []
        for name, (nfa, totals) in cat_qty_by_project.items():
            if cat in totals:
                per_1000.append(totals[cat] / (nfa / 1000))
        if per_1000:
            ratio_rows.append(dict(
                CapexCategory=cat, N=len(per_1000),
                Mean_QtyPer1000sqmNFA=statistics.mean(per_1000),
                Median_QtyPer1000sqmNFA=statistics.median(per_1000),
                Min=min(per_1000), Max=max(per_1000),
            ))
    return cat_qty_by_project, ratio_rows


def study_2_headcount_proxy(cat_qty_by_project):
    gs_key = next((n for n in cat_qty_by_project if 'green skyline' in n.lower()), None)
    if not gs_key:
        print("Study 2: Green Skyline not found in Study 1's project set -- cannot anchor a headcount ratio.")
        return []
    nfa, totals = cat_qty_by_project[gs_key]
    print(f"Study 2: anchoring on Green Skyline (the ONLY old-8 project with a real headcount in "
          f"the new Master List) -- headcount={GREEN_SKYLINE_HEADCOUNT}, n=1. Every ratio below is "
          f"a single real data point, not a population statistic.")

    ratio_rows = []
    for cat, qty in sorted(totals.items()):
        ratio_rows.append(dict(
            CapexCategory=cat, QtyAtGreenSkyline=qty,
            QtyPerHeadcount_n1=round(qty / GREEN_SKYLINE_HEADCOUNT, 3),
        ))
    return ratio_rows


def load_master_list_headcount_population():
    with open(os.path.join(MASTER_LIST, 'Dim_Property_Residential.csv'), encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    pop = [(float(r['GFA_m2']), float(r['Headcount'])) for r in rows if r['GFA_m2'] and r['Headcount']]
    return pop


def main():
    cat_qty_by_project, study1_rows = study_1_nfa_ratio()
    print("\n=== STUDY 1: Qty per 1,000 m² verified TotalNFA (old 8 files) ===")
    for r in study1_rows:
        print(f"  {r['CapexCategory']}: n={r['N']}, mean={r['Mean_QtyPer1000sqmNFA']:.2f}, "
              f"median={r['Median_QtyPer1000sqmNFA']:.2f}, range=[{r['Min']:.2f}, {r['Max']:.2f}]")

    study2_rows = study_2_headcount_proxy(cat_qty_by_project)
    print("\n=== STUDY 2: Qty per Headcount, anchored on Green Skyline (n=1) ===")
    for r in study2_rows:
        print(f"  {r['CapexCategory']}: {r['QtyAtGreenSkyline']:.0f} units at headcount="
              f"{GREEN_SKYLINE_HEADCOUNT} -> {r['QtyPerHeadcount_n1']} per headcount")

    pop = load_master_list_headcount_population()
    print(f"\nMaster List headcount-vs-GFA population available to apply Study 2's ratios against "
          f"for a NEW prospect that doesn't have a real headcount yet: n={len(pop)} real properties "
          f"(this is derive_staffing_benchmarks.py's population -- median headcount/1,000m² already "
          f"computed there by size bucket).")

    write_excel(study1_rows, study2_rows, cat_qty_by_project, pop)


def write_excel(study1_rows, study2_rows, cat_qty_by_project, pop):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    title_font = Font(bold=True, size=14)
    sub_font = Font(italic=True, color="595959")
    thin = Side(style='thin', color='BFBFBF')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal='center', vertical='center')
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)

    def write_table(ws, headers, rows, start_row, title=None, subtitle=None):
        r = start_row
        if title:
            ws.cell(row=r, column=1, value=title).font = title_font
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(headers))
            r += 1
        if subtitle:
            c = ws.cell(row=r, column=1, value=subtitle)
            c.font = sub_font
            c.alignment = left
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(headers))
            ws.row_dimensions[r].height = 30
            r += 1
        for c, h in enumerate(headers, start=1):
            cell = ws.cell(row=r, column=c, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center
            cell.border = border
        r += 1
        for row in rows:
            for c, h in enumerate(headers, start=1):
                cell = ws.cell(row=r, column=c, value=row.get(h))
                cell.border = border
                if isinstance(row.get(h), float):
                    cell.number_format = '0.00'
            r += 1
        return r + 1

    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = 'Study 1 - NFA ratio'
    write_table(
        ws1, ['CapexCategory', 'N', 'Mean_QtyPer1000sqmNFA', 'Median_QtyPer1000sqmNFA', 'Min', 'Max'],
        study1_rows, 1,
        title='Study 1 — Capex Qty per 1,000 m² verified TotalNFA (old 8 real project files)',
        subtitle='Ground truth: real observed quantities from each project\'s own "B7. Chi phí Trang thiết bị MO" sheet, '
                  'joined to VERIFIED TotalNFA (not Generation A\'s own broken Dim_Project scale columns). N = how many '
                  'of the old 8 projects actually have both a real capex line item in that category and a clean NFA.')
    for col, w in {'A': 26, 'B': 6, 'C': 22, 'D': 24, 'E': 10, 'F': 10}.items():
        ws1.column_dimensions[col].width = w

    ws2 = wb.create_sheet('Study 2 - Headcount proxy')
    write_table(
        ws2, ['CapexCategory', 'QtyAtGreenSkyline', 'QtyPerHeadcount_n1'],
        study2_rows, 1,
        title='Study 2 — Capex Qty per Headcount, anchored on Green Skyline (n=1)',
        subtitle='Green Skyline is the ONLY one of the old 8 projects with a real headcount in the new Master List (21 staff). '
                  'Every ratio here is a single real data point, stated as n=1 rather than disguised as a population statistic — '
                  'not a substitute for Study 1, a second lens to compare against it.')
    for col, w in {'A': 26, 'B': 20, 'C': 20}.items():
        ws2.column_dimensions[col].width = w

    ws3 = wb.create_sheet('Master List headcount pop')
    ws3['A1'] = 'The population Study 2\'s ratio would be applied against for a NEW prospect'
    ws3['A1'].font = title_font
    ws3.merge_cells('A1:C1')
    ws3['A2'] = (f'{len(pop)} real residential properties in the new Master List have both a real GFA and a real Headcount — '
                 'this is the SAME population derive_staffing_benchmarks.py already used to compute median headcount per '
                 '1,000 m² by size bucket. For a prospect with no headcount yet: estimate headcount from that distribution, '
                 'then apply Study 2\'s Qty-per-Headcount ratio. Two hops, both shown, neither hidden.')
    ws3['A2'].font = sub_font
    ws3['A2'].alignment = left
    ws3.merge_cells('A2:C2')
    ws3.row_dimensions[2].height = 44
    headers = ['GFA_m2', 'Headcount']
    r = 4
    for c, h in enumerate(headers, start=1):
        cell = ws3.cell(row=r, column=c, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border
    r += 1
    for gfa, hc in sorted(pop):
        ws3.cell(row=r, column=1, value=gfa).border = border
        ws3.cell(row=r, column=2, value=hc).border = border
        r += 1
    for col, w in {'A': 16, 'B': 14}.items():
        ws3.column_dimensions[col].width = w

    import tempfile, shutil
    local_out = os.path.join(tempfile.gettempdir(), 'Capex_Qty_Estimation_Study.xlsx')
    wb.save(local_out)
    print('\nSaved locally:', local_out)
    try:
        shutil.copyfile(local_out, OUT_XLSX)
        print('Copied into place:', OUT_XLSX)
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)


if __name__ == '__main__':
    main()
