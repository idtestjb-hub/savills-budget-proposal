"""
Processes data/master_list_verified/Dim_Property_Residential.csv (the transformed 2026 Master
List — see transform_master_list.py) to derive REAL staffing benchmarks: how headcount actually
scales with property size across the 63 residential properties that have both a real headcount
and a real GFA on the same row.

This is the analysis the rest of the session has been missing a dataset for. Every staffing
ratio used so far (build_project_input_form.py's "Security: Staff per Gate", "m² per Cleaner",
etc.) was an editable PM assumption because the old data had property scale and staff headcount
as two disjoint populations with no shared key. This Master List has both on the same row, so this
script computes the real distribution instead of assuming one.

What it reports, and why each piece matters:
  - Headcount per 1,000 m² GFA — population mean/median/p25/p75, so a PM sees the real spread,
    not a single misleadingly-precise number.
  - The SAME ratio broken out by size bucket — bigger properties should show a lower ratio if
    there are real economies of scale; this is checked, not assumed.
  - Pearson correlation between Headcount and each of GFA/TowerCount/GateCount/ElevatorCount/
    TotalUnits/CarParkingSlots, each with its own real sample size n (GateCount and ElevatorCount
    are often free text in the source and only pairwise-complete rows can be used, so n varies a
    lot by column and is reported explicitly rather than implied to be the full 63).
  - Real monthly cost per headcount (StaffCost / Headcount) — same population, same stats.

This does NOT yet feed back into build_project_input_form.py's ratio defaults or
master_comparables.py's comparable list — it's the analysis step first, so the numbers can be
reviewed before anything downstream starts trusting them.
"""
import os

import numpy as np
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INPUT_CSV = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified', 'Dim_Property_Residential.csv')
OUT_DIR = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified')
OUT_CSV = os.path.join(OUT_DIR, 'Fact_StaffingBenchmark_Derived.csv')
OUT_XLSX = os.path.join(OUT_DIR, 'Staffing_Benchmark_Analysis.xlsx')

SIZE_BUCKETS = [(0, 30000, '<30k m²'), (30000, 80000, '30k-80k m²'),
                (80000, 150000, '80k-150k m²'), (150000, float('inf'), '>150k m²')]
CORRELATION_FIELDS = ['GFA_m2', 'TowerCount', 'GateCount', 'ElevatorCount', 'TotalUnits', 'CarParkingSlots']


def size_bucket(gfa):
    for lo, hi, label in SIZE_BUCKETS:
        if lo <= gfa < hi:
            return label
    return 'unknown'


def quantile_row(label, series):
    s = series.dropna()
    return dict(Metric=label, N=len(s), Mean=s.mean(), Median=s.median(),
                P25=s.quantile(0.25), P75=s.quantile(0.75), Min=s.min(), Max=s.max())


def main():
    df = pd.read_csv(INPUT_CSV)

    staff_pop = df[df['GFA_m2'].notna() & df['Headcount'].notna() & (df['GFA_m2'] > 0)].copy()
    staff_pop['HeadcountPer1000sqm'] = staff_pop['Headcount'] / (staff_pop['GFA_m2'] / 1000)
    staff_pop['SizeBucket'] = staff_pop['GFA_m2'].apply(size_bucket)

    cost_pop = df[df['StaffCost'].notna() & df['Headcount'].notna() & (df['Headcount'] > 0)].copy()
    cost_pop['CostPerHeadcount_calc'] = cost_pop['StaffCost'] / cost_pop['Headcount']

    print(f'Population with GFA + Headcount both real: {len(staff_pop)} of {len(df)} residential properties')
    print(f'Population with StaffCost + Headcount both real: {len(cost_pop)} of {len(df)} residential properties')

    overview_rows = [
        quantile_row('Headcount per 1,000 m² GFA', staff_pop['HeadcountPer1000sqm']),
        quantile_row('Monthly Staff Cost per Headcount (VND)', cost_pop['CostPerHeadcount_calc']),
    ]
    overview_df = pd.DataFrame(overview_rows)

    bucket_rows = []
    for _, _, label in SIZE_BUCKETS:
        sub = staff_pop[staff_pop['SizeBucket'] == label]['HeadcountPer1000sqm']
        if len(sub) == 0:
            continue
        bucket_rows.append(dict(SizeBucket=label, N=len(sub), Mean_HeadcountPer1000sqm=sub.mean(),
                                 Median_HeadcountPer1000sqm=sub.median(), Min=sub.min(), Max=sub.max()))
    bucket_df = pd.DataFrame(bucket_rows)

    corr_rows = []
    for field in CORRELATION_FIELDS:
        pair = df[['Headcount', field]].dropna()
        pair = pair[pair[field] != 0] if field != 'Headcount' else pair
        n = len(pair)
        r = pair['Headcount'].corr(pair[field]) if n >= 3 else float('nan')
        corr_rows.append(dict(Field=field, N=n, PearsonR_with_Headcount=r))
    corr_df = pd.DataFrame(corr_rows)

    print('\n=== Overview ===')
    print(overview_df.to_string(index=False))
    print('\n=== By size bucket ===')
    print(bucket_df.to_string(index=False))
    print('\n=== Correlation with Headcount (real n per field) ===')
    print(corr_df.to_string(index=False))

    os.makedirs(OUT_DIR, exist_ok=True)
    overview_df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
    print(f'\nSaved: {OUT_CSV}')

    write_excel(overview_df, bucket_df, corr_df, staff_pop, cost_pop)


HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)
SUBTITLE_FONT = Font(italic=True, color="595959")
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')


def write_df_sheet(ws, df, start_row=1, number_cols=None):
    number_cols = number_cols or []
    for c, col in enumerate(df.columns, start=1):
        cell = ws.cell(row=start_row, column=c, value=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    for r, (_, row) in enumerate(df.iterrows(), start=start_row + 1):
        for c, col in enumerate(df.columns, start=1):
            v = row[col]
            if isinstance(v, float) and np.isnan(v):
                v = None
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER
            if col in number_cols and v is not None:
                cell.number_format = '#,##0.0'
    for c in range(1, len(df.columns) + 1):
        ws.column_dimensions[ws.cell(row=start_row, column=c).column_letter].width = 20


def write_excel(overview_df, bucket_df, corr_df, staff_pop, cost_pop):
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = 'Overview'
    ws1['A1'] = 'Staffing Benchmarks — Derived from 2026 Master List (real data, not assumed)'
    ws1['A1'].font = TITLE_FONT
    ws1.merge_cells('A1:G1')
    ws1['A2'] = ('Population: residential properties with both a real GFA and a real Headcount on the same row. '
                 'N is reported per metric because coverage differs by field — see derive_staffing_benchmarks.py docstring.')
    ws1['A2'].font = SUBTITLE_FONT
    ws1['A2'].alignment = Alignment(wrap_text=True)
    ws1.merge_cells('A2:G2')
    ws1.row_dimensions[2].height = 28
    write_df_sheet(ws1, overview_df, start_row=4, number_cols=['Mean', 'Median', 'P25', 'P75', 'Min', 'Max'])

    ws2 = wb.create_sheet('By Size Bucket')
    ws2['A1'] = 'Headcount per 1,000 m² GFA, by property size — checks for economies of scale'
    ws2['A1'].font = TITLE_FONT
    ws2.merge_cells('A1:F1')
    write_df_sheet(ws2, bucket_df, start_row=3,
                    number_cols=['Mean_HeadcountPer1000sqm', 'Median_HeadcountPer1000sqm', 'Min', 'Max'])

    ws3 = wb.create_sheet('Correlations')
    ws3['A1'] = 'Pearson correlation with Headcount — real sample size per field, not assumed uniform'
    ws3['A1'].font = TITLE_FONT
    ws3.merge_cells('A1:C1')
    write_df_sheet(ws3, corr_df, start_row=3, number_cols=['PearsonR_with_Headcount'])

    ws4 = wb.create_sheet('Source Rows (GFA+Headcount)')
    cols = ['Name', 'GFA_m2', 'Headcount', 'HeadcountPer1000sqm', 'SizeBucket', 'TowerCount', 'GateCount', 'SourceRow']
    write_df_sheet(ws4, staff_pop[cols].sort_values('GFA_m2'), start_row=1,
                    number_cols=['GFA_m2', 'Headcount', 'HeadcountPer1000sqm'])

    import tempfile, shutil
    local_out = os.path.join(tempfile.gettempdir(), 'Staffing_Benchmark_Analysis.xlsx')
    wb.save(local_out)
    print('Saved locally:', local_out)
    try:
        shutil.copyfile(local_out, OUT_XLSX)
        print('Copied into place:', OUT_XLSX)
    except PermissionError as e:
        print('Could not copy into place yet (still locked):', e)
        print('Local copy remains valid at:', local_out)


if __name__ == '__main__':
    main()
