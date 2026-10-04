# RETIRED 2026-10-04 (backlog A7): paths point at a folder that does not exist; do not run. See legacy/README.md.
import os
import sqlite3
import csv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
DB_PATH = os.path.join(OUTPUT_DIR, 'CellScan.sqlite')


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Sheet-level summary CSV
    cur.execute("""
        SELECT file_name, project_code, sheet_name, max_row, max_col,
               input_cells, calculated_cells, error_cells, total_nonempty,
               formula_ratio, same_sheet_formulas, cross_sheet_formulas, external_link_formulas
        FROM sheet_summary
        ORDER BY file_name, sheet_name
    """)
    rows = cur.fetchall()
    cols = ['FileName', 'ProjectCode', 'SheetName', 'MaxRow', 'MaxCol', 'InputCells',
            'CalculatedCells', 'ErrorCells', 'TotalNonEmpty', 'FormulaRatio',
            'SameSheetFormulas', 'CrossSheetFormulas', 'ExternalLinkFormulas']
    with open(os.path.join(OUTPUT_DIR, 'CellScan_SheetSummary.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)

    # 2) Error listing CSV
    cur.execute("""
        SELECT file_name, project_code, sheet_name, cell_ref, formula, error_type, error_reason
        FROM cell_scan
        WHERE classification='ERROR'
        ORDER BY file_name, sheet_name, row, col
    """)
    err_rows = cur.fetchall()
    with open(os.path.join(OUTPUT_DIR, 'CellScan_Errors.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['FileName', 'ProjectCode', 'SheetName', 'CellRef', 'Formula', 'ErrorType', 'ErrorReason'])
        w.writerows(err_rows)

    # 3) Text report
    lines = []
    lines.append('CELL-LEVEL SCAN REPORT -- 8 real budget_planning project files')
    lines.append('=' * 70)
    lines.append('')

    cur.execute("SELECT COUNT(*) FROM cell_scan")
    total = cur.fetchone()[0]
    lines.append(f'Total non-empty cells scanned: {total:,}')
    lines.append('')

    cur.execute("SELECT classification, COUNT(*) FROM cell_scan GROUP BY classification ORDER BY 2 DESC")
    lines.append('By classification:')
    for cls, n in cur.fetchall():
        lines.append(f'  {cls:12s} {n:>10,}  ({n/total*100:5.1f}%)')
    lines.append('')

    cur.execute("""
        SELECT link_type, COUNT(*) FROM cell_scan WHERE classification='CALCULATED'
        GROUP BY link_type ORDER BY 2 DESC
    """)
    lines.append('CALCULATED cells by link type:')
    for lt, n in cur.fetchall():
        lines.append(f'  {lt:15s} {n:>10,}')
    lines.append('')

    cur.execute("""
        SELECT error_type, COUNT(*) FROM cell_scan WHERE classification='ERROR'
        GROUP BY error_type ORDER BY 2 DESC
    """)
    lines.append('ERROR cells by type:')
    for et, n in cur.fetchall():
        lines.append(f'  {et:15s} {n:>10,}')
    lines.append('')

    lines.append('Per-file totals:')
    cur.execute("""
        SELECT file_name,
               SUM(input_cells), SUM(calculated_cells), SUM(error_cells), SUM(total_nonempty)
        FROM sheet_summary GROUP BY file_name ORDER BY file_name
    """)
    for fn, ic, cc, ec, tot in cur.fetchall():
        err_pct = (ec / tot * 100) if tot else 0
        lines.append(f'  {fn}')
        lines.append(f'      input={ic:,}  calculated={cc:,}  error={ec:,}  total={tot:,}  error_rate={err_pct:.2f}%')
    lines.append('')

    lines.append('Sheets with the highest error counts (top 25):')
    cur.execute("""
        SELECT file_name, sheet_name, error_cells, total_nonempty
        FROM sheet_summary WHERE error_cells > 0
        ORDER BY error_cells DESC LIMIT 25
    """)
    for fn, sn, ec, tot in cur.fetchall():
        lines.append(f'  {ec:>6,}  {fn} | {sn}  (of {tot:,} cells)')
    lines.append('')

    with open(os.path.join(OUTPUT_DIR, 'CellScan_Report.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print('\n'.join(lines))
    conn.close()


if __name__ == '__main__':
    main()
