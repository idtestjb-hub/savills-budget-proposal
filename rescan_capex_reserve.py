"""
Extracts the ongoing Capex reserve rate that real Savills projects actually used.

WHY. generate_project_output.py carried CAPEX_RESERVE_RATE = 0.10 with a comment admitting it was
"a commonly cited property-management rule of thumb, NOT this project's own real reserve policy,
which isn't in the source data." The policy IS in the source data — it just had to be measured.

Reads EN1-EN3 (New capital expenditure for MO / ME / Common area) from each real project budget's
year sheets, and records Year-1 Capex against the later year's, with the later year's length so the
short-year cases stay interpretable.

WHAT THIS IS NOT. There is no formula in the source budgets to copy: the later-year cell is
'=$F$219', a plain reference to a manually entered column. Every rate here is an IMPLIED RATIO
between two independently typed numbers, not a rule the budgets apply. The output records that.

Also note EXENSIVE LOGIC.xlsx states the reserve as "khoang 0.1% chi phi dau tu trang thiet bi ban
dau" — about 0.1% of initial equipment investment. No real project is remotely near that; 0.1%
would imply a thousand-year replacement cycle. The measured range contradicts the written spec, and
correcting that document is Savills' call, not this pipeline's.

Run:  python rescan_capex_reserve.py
"""
import csv
import datetime
import glob
import os
import re
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))          # Budget_Agent/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SOURCE_DIR = os.path.join(PROJECT_ROOT, 'input', 'budget_planning')
OUT_CSV = os.path.join(BASE, 'data', 'generation_A_star_schema', 'Fact_CapexReserve.csv')

EN_CODES = ('EN1', 'EN2', 'EN3')

# Sheet-name fragments that identify a Budget-MF sheet and how long its year is.
YEAR1_HINTS = ('12 months (year 1)', '12 months (year 01)')
LATER_HINTS = ('year 2', 'year 02', 'year 3', 'year 03', 'ổn định', 'on dinh')


def _months_in(sheet_name):
    """Read the year length out of the sheet's own name: '09 months (year 3)' -> 9."""
    m = re.search(r'(\d{1,2})\s*months', sheet_name, re.I)
    if m:
        return int(m.group(1))
    return 12          # a 'stabilised' sheet with no month count is a full year


def _en_total(ws):
    """Sum EN1-EN3 on one Budget-MF sheet. Column H is the annual total; F is the reference column
    a later-year sheet points at with '=$F$219'."""
    total_h = total_f = 0.0
    found = 0
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 600)):
        for cell in row[21:33]:            # the code column sits around V-AH
            v = cell.value
            if isinstance(v, str) and v.strip() in EN_CODES:
                h = ws.cell(row=cell.row, column=8).value
                f = ws.cell(row=cell.row, column=6).value
                if isinstance(h, (int, float)):
                    total_h += h
                if isinstance(f, (int, float)):
                    total_f += f
                found += 1
                break
    return (total_h, total_f, found)


def scan():
    rows = []
    files = [f for f in glob.glob(os.path.join(SOURCE_DIR, '*.xlsx')) if 'repaired' in f]
    if not files:
        raise FileNotFoundError(
            f'No repaired project workbooks found in {SOURCE_DIR}. The raw files carry invalid XML '
            f'(a #N/A in print titles) and must be repaired before openpyxl can open them — see '
            f'common_utils_v2.repair_workbook().')
    import openpyxl
    today = datetime.date.today().isoformat()
    for path in sorted(files):
        name = os.path.basename(path)
        try:
            wb = openpyxl.load_workbook(path, data_only=True)
        except Exception:
            continue
        mf = [s for s in wb.sheetnames if 'Budget-MF' in s]
        year1 = next((s for s in mf if any(h in s.lower() for h in YEAR1_HINTS)), None)
        if not year1:
            wb.close()
            continue
        y1_h, _y1_f, y1_found = _en_total(wb[year1])
        if not y1_h or y1_found < 3:
            wb.close()
            continue
        for sheet in mf:
            if sheet == year1 or not any(h in sheet.lower() for h in LATER_HINTS):
                continue
            h, f, found = _en_total(wb[sheet])
            later = h or f            # a later-year sheet may cache 0 and hold the figure in F
            if not later or found < 3:
                continue
            months = _months_in(sheet)
            ratio = later / y1_h
            # A later year at ~100% of Year 1 is a FULL REPEAT — the project bought equipment over
            # two years — not a reserve contribution. Green Skyline does exactly this in Year 2
            # (1.03 = Year 1 + 3% inflation) and only drops to the reserve in Year 3. Averaging a
            # repeat year into the rate would roughly triple it, so the two are classified apart:
            # repeat years tell us the DROP YEAR, reserve years tell us the RATE.
            kind = 'full-repeat' if ratio > 0.5 else 'reserve'
            rows.append({
                'ObservationType': kind,
                'Project': name.replace('__repaired.xlsx', ''),
                'Year1Sheet': year1,
                'LaterSheet': sheet,
                'LaterMonths': months,
                'Year1Capex': round(y1_h, 2),
                'LaterCapex': round(later, 2),
                'ImpliedRateLiteral': round(later / y1_h, 6),
                'ImpliedRateAnnualised': round((later / y1_h) * (12.0 / months), 6),
                'SourceFile': name,
                'ExtractedOn': today,
            })
        wb.close()
    return rows


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    rows = scan()
    if not rows:
        raise SystemExit('No Capex reserve observations found — nothing written.')
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f'Wrote {len(rows)} observation(s) -> {OUT_CSV}\n')
    print(f'{"PROJECT":38} {"TYPE":>12} {"MO":>4} {"YEAR1":>16} {"LATER":>16} {"ANNUAL":>8}')
    for r in rows:
        print(f'{r["Project"][:38]:38} {r["ObservationType"]:>12} {r["LaterMonths"]:>4} '
              f'{r["Year1Capex"]:>16,.0f} {r["LaterCapex"]:>16,.0f} {r["ImpliedRateAnnualised"]:>8.4f}')
    res = [r for r in rows if r['ObservationType'] == 'reserve']
    rep = [r for r in rows if r['ObservationType'] == 'full-repeat']
    lit = [r['ImpliedRateLiteral'] for r in res]
    ann = [r['ImpliedRateAnnualised'] for r in res]
    print(f'\n  RESERVE observations  n={len(res)}')
    print(f'    literal    mean {sum(lit)/len(lit):.4f}   range {min(lit):.4f} - {max(lit):.4f}')
    print(f'    annualised mean {sum(ann)/len(ann):.4f}   range {min(ann):.4f} - {max(ann):.4f}')
    print(f'\n  FULL-REPEAT years  n={len(rep)}   {[r["Project"][:30] for r in rep]}')
    print('    A repeat year means the project bought equipment across two years. It sets the DROP')
    print('    YEAR, not the rate, and is excluded from the mean above.')
    print('\n  EXENSIVE LOGIC.xlsx states ~0.1% (0.0010). No observation is near it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
