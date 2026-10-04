# RETIRED 2026-10-04 (backlog A7): paths point at a folder that does not exist; do not run. See legacy/README.md.
"""
Fresh cell-level scan of the 8 real budget_planning project files.

For every non-empty cell in every sheet, classifies it as:
  INPUT       - a literal value (number/text/date/bool), not a formula
  CALCULATED  - a formula that evaluated cleanly (same-sheet / cross-sheet / external-link)
  ERROR       - a formula (or literal) whose cached value is an Excel error code, with a
                heuristic explanation of what that error code generally means

Writes everything to a SQLite database (queryable, indexed) plus two human-readable
CSV summaries: one row per sheet (counts + formula ratio), and one row per error cell.
"""
import os
import re
import glob
import sqlite3
import time
import warnings

import openpyxl
from common_utils_v2 import repair_workbook, norm, project_code_from_filename

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INPUT_DIR = os.path.join(BASE_DIR, 'input', 'budget_planning')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
DB_PATH = os.path.join(OUTPUT_DIR, 'CellScan.sqlite')

EXCLUDE_SUBSTR = ['__repaired', '__profile', 'MasterData_', 'Budget_Workbook_Map_Export',
                  'Sheet_Index_Master', 'Budget_PowerBI_Model', 'A&K SAMPLE DATA',
                  'A&K GENERATED FROM DIM-FACT']

ERROR_CODES = {'#REF!', '#VALUE!', '#DIV/0!', '#N/A', '#NAME?', '#NULL!', '#NUM!', '#SPILL!',
               '#CALC!', '#GETTING_DATA', '#UNKNOWN!', '#BLOCKED!', '#CONNECT!', '#FIELD!'}

ERROR_REASONS = {
    '#REF!': 'Formula references a cell/range that no longer exists (rows, columns or a whole '
              'sheet were likely deleted/restructured after this formula was first copied).',
    '#DIV/0!': 'Formula divides by zero or by a blank cell acting as zero -- usually an unfilled '
               'input feeding the denominator.',
    '#VALUE!': 'A formula operand is text or blank where a number was expected -- often a merged '
              'label cell, a header row, or an empty input cell used in arithmetic.',
    '#N/A': 'A lookup function (VLOOKUP/MATCH/INDEX/HLOOKUP) found no matching key in its search range.',
    '#NAME?': 'The formula uses a function or defined name Excel does not recognize -- a deleted '
             'named range, a typo, or a newer function referenced without its required prefix.',
    '#NULL!': 'The formula uses an invalid range intersection (two ranges joined by a space that '
             'do not actually overlap).',
    '#NUM!': 'The formula produced an invalid numeric result (e.g. a negative number inside SQRT, '
            'or an iterative calculation that failed to converge).',
    '#SPILL!': 'A dynamic-array formula cannot spill into the cells below/right because they are '
              'already occupied by other content.',
    '#CALC!': 'A dynamic-array formula returned an empty array or an unsupported calculation.',
    '#GETTING_DATA': 'Formula is waiting on an external/real-time data source that is unavailable offline.',
}


def classify_value_type(v):
    if v is None:
        return 'EMPTY'
    if isinstance(v, bool):
        return 'BOOL'
    if isinstance(v, (int, float)):
        return 'NUMBER'
    if hasattr(v, 'year') and hasattr(v, 'month'):
        return 'DATE'
    if isinstance(v, str) and v.strip().upper() in ERROR_CODES:
        return 'ERROR'
    return 'TEXT'


LINK_EXTERNAL_RE = re.compile(r"\[\d+\]")
LINK_SHEET_RE = re.compile(r"!")


def classify_link_type(formula: str) -> str:
    if LINK_EXTERNAL_RE.search(formula):
        return 'external-link'
    if LINK_SHEET_RE.search(formula):
        return 'cross-sheet'
    return 'same-sheet'


def error_reason_for(error_code: str, formula: str) -> str:
    base = ERROR_REASONS.get(error_code, 'Unrecognized/rare error code.')
    if error_code == '#REF!' and formula and '[' in formula and ']' in formula:
        return base + ' This particular formula also links to an external workbook, which is a common source of #REF! when that file is unavailable or was renamed.'
    return base


def get_source_files():
    files = []
    for p in sorted(glob.glob(os.path.join(INPUT_DIR, '*.xlsx'))):
        name = os.path.basename(p)
        if any(x in name for x in EXCLUDE_SUBSTR):
            continue
        files.append(p)
    return files


def init_db(path):
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE cell_scan (
            file_name TEXT,
            project_code TEXT,
            sheet_name TEXT,
            row INTEGER,
            col INTEGER,
            cell_ref TEXT,
            classification TEXT,
            value_type TEXT,
            cached_value_text TEXT,
            cached_value_num REAL,
            formula TEXT,
            link_type TEXT,
            error_type TEXT,
            error_reason TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE sheet_summary (
            file_name TEXT,
            project_code TEXT,
            sheet_name TEXT,
            max_row INTEGER,
            max_col INTEGER,
            input_cells INTEGER,
            calculated_cells INTEGER,
            error_cells INTEGER,
            total_nonempty INTEGER,
            formula_ratio REAL,
            same_sheet_formulas INTEGER,
            cross_sheet_formulas INTEGER,
            external_link_formulas INTEGER
        )
    """)
    conn.commit()
    return conn


def col_letter(col_idx):
    from openpyxl.utils import get_column_letter
    return get_column_letter(col_idx)


def scan_file(conn, source_path, file_idx, total_files):
    file_name = os.path.basename(source_path)
    project_code = project_code_from_filename(source_path, file_idx)
    t0 = time.time()
    print(f'[{file_idx}/{total_files}] {file_name} -- repairing/loading...', flush=True)

    repaired = repair_workbook(source_path)
    wb_formulas = openpyxl.load_workbook(repaired, data_only=False, read_only=True)
    wb_values = openpyxl.load_workbook(repaired, data_only=True, read_only=True)

    cur = conn.cursor()
    insert_buf = []

    for sheet_name in wb_formulas.sheetnames:
        if sheet_name not in wb_values.sheetnames:
            continue
        ws_f = wb_formulas[sheet_name]
        ws_v = wb_values[sheet_name]

        input_cells = calc_cells = error_cells = 0
        same_sheet = cross_sheet = external_link = 0

        rows_f = ws_f.iter_rows()
        rows_v = ws_v.iter_rows()
        row_no = 0
        for row_f, row_v in zip(rows_f, rows_v):
            row_no += 1
            for c_f, c_v in zip(row_f, row_v):
                raw = c_f.value
                cached = c_v.value
                if raw is None and cached is None:
                    continue
                col_no = c_f.column
                ref = c_f.coordinate

                is_formula = isinstance(raw, str) and raw.startswith('=')
                value_type = classify_value_type(cached)

                if value_type == 'ERROR':
                    classification = 'ERROR'
                    error_type = str(cached).strip()
                    formula_text = raw if is_formula else None
                    reason = error_reason_for(error_type, formula_text or '')
                    link_type = classify_link_type(formula_text) if formula_text else 'n/a'
                    error_cells += 1
                    cached_num = None
                    cached_text = str(cached)
                elif is_formula:
                    classification = 'CALCULATED'
                    error_type = None
                    reason = None
                    formula_text = raw
                    link_type = classify_link_type(formula_text)
                    if link_type == 'same-sheet':
                        same_sheet += 1
                    elif link_type == 'cross-sheet':
                        cross_sheet += 1
                    else:
                        external_link += 1
                    calc_cells += 1
                    cached_num = cached if isinstance(cached, (int, float)) and not isinstance(cached, bool) else None
                    cached_text = None if cached_num is not None else (str(cached) if cached is not None else None)
                else:
                    classification = 'INPUT'
                    error_type = None
                    reason = None
                    formula_text = None
                    link_type = 'n/a'
                    input_cells += 1
                    cached_num = raw if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None
                    cached_text = None if cached_num is not None else (str(raw) if raw is not None else None)

                insert_buf.append((
                    file_name, project_code, sheet_name, row_no, col_no, ref,
                    classification, value_type, cached_text, cached_num,
                    formula_text, link_type, error_type, reason,
                ))

            if len(insert_buf) >= 20000:
                cur.executemany(
                    "INSERT INTO cell_scan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", insert_buf)
                insert_buf.clear()

        total_nonempty = input_cells + calc_cells + error_cells
        formula_ratio = round((calc_cells + error_cells) / total_nonempty, 4) if total_nonempty else 0.0
        cur.execute(
            "INSERT INTO sheet_summary VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (file_name, project_code, sheet_name, ws_f.max_row or 0, ws_f.max_column or 0,
             input_cells, calc_cells, error_cells, total_nonempty, formula_ratio,
             same_sheet, cross_sheet, external_link)
        )

    if insert_buf:
        cur.executemany("INSERT INTO cell_scan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", insert_buf)
    conn.commit()
    print(f'  done in {time.time()-t0:.1f}s', flush=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = get_source_files()
    print(f'Found {len(files)} source project files to scan.')
    conn = init_db(DB_PATH)
    for i, fp in enumerate(files, start=1):
        scan_file(conn, fp, i, len(files))

    conn.execute("CREATE INDEX idx_cell_class ON cell_scan(classification)")
    conn.execute("CREATE INDEX idx_cell_error ON cell_scan(error_type)")
    conn.execute("CREATE INDEX idx_cell_file_sheet ON cell_scan(file_name, sheet_name)")
    conn.commit()

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM cell_scan")
    total = cur.fetchone()[0]
    cur.execute("SELECT classification, COUNT(*) FROM cell_scan GROUP BY classification")
    by_class = cur.fetchall()
    cur.execute("SELECT error_type, COUNT(*) FROM cell_scan WHERE classification='ERROR' GROUP BY error_type ORDER BY 2 DESC")
    by_error = cur.fetchall()

    print()
    print('=== SCAN COMPLETE ===')
    print('Total cells scanned:', total)
    for cls, n in by_class:
        print(f'  {cls}: {n}')
    print('Error breakdown:')
    for et, n in by_error:
        print(f'  {et}: {n}')

    conn.close()


if __name__ == '__main__':
    main()
