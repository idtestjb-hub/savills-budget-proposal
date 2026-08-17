import pandas as pd
from common_utils_v2 import find_sheet_loose, norm, get_budget_type, split_en_vn


def _is_budget_sheet(sn: str) -> bool:
    """Check if a sheet name looks like a budget data sheet."""
    s = sn.lower().strip()
    # Format A: 2a/2b/2c.Budget-MF or Budget-Pre (Lumi, Green Skyline, Parking...)
    if any(s.startswith(p) for p in ['2a.budget', '2b.budget', '2c.budget', '0.budget']):
        return True
    # Format B: B2.Chi tiết dự toán ... or just B2.Chi tiết...
    if s.startswith('b2.chi ti') or s.startswith('b2. chi ti'):
        return True
    # Format C: 2.2 Common area Fund
    if '2.2 common area fund' in s:
        return True
    # Legacy: plain "B2.Chi tiết dự toán ngân sách"
    if 'b2.' in s and ('chi ti' in s or 'du toan' in s or 'dự toán' in s or 'ngân sách' in s):
        return True
    return False


def _find_header_and_month_row(ws):
    """
    Find the header row and the row containing datetime month values.
    Returns (header_row_idx, month_row_idx, month_cols)
    where month_cols = list of (col_index, date_string)
    
    Two formats exist:
    - Format A (Lumi/GS): months are dates in a ROW above the text headers
      e.g. Row 8 has datetime values, Row 10 has "Frequency", "Unit Price", etc.
    - Format B (Fiato/11D): months are datetime in the same header row
    """
    month_row_idx = -1
    month_cols = []
    header_row_idx = -1

    # Scan first 20 rows
    for r in range(1, min(ws.max_row, 25)):
        row_dates = []
        for c in range(1, min(ws.max_column, 60) + 1):
            v = ws.cell(r, c).value
            if hasattr(v, 'year') or (isinstance(v, str) and '-01 00:00' in v):
                try:
                    ts = pd.Timestamp(v)
                    row_dates.append((c, ts.date().isoformat()))
                except Exception:
                    pass

        if len(row_dates) >= 3:
            # Found a row with multiple month dates
            month_row_idx = r
            month_cols = row_dates

        # Look for header row: has text keywords for items / cost
        for c in range(1, min(ws.max_column, 20) + 1):
            v = ws.cell(r, c).value
            if not v:
                continue
            vs = norm(str(v)).lower()
            if any(kw in vs for kw in ['unit price', 'đơn giá', 'total price', 'tổng', 'frequency', 'number of times', 'hạng mục', 'item', 'code', 'mã']):
                header_row_idx = r
                break

        if header_row_idx != -1 and month_row_idx != -1:
            break

    return header_row_idx, month_row_idx, month_cols


def _map_columns_format_a(ws, header_row_idx):
    """
    Map columns for Format A (Lumi/GS style).
    Col structure: Use(2), Frequency(3), NumTimes(5), UnitPrice(6), TotalPrice(8)
    Months are in a different row (already found).
    """
    col_map = {}
    for c in range(1, min(ws.max_column, 60) + 1):
        v = ws.cell(header_row_idx, c).value
        if not v:
            continue
        vs = norm(str(v)).lower().replace('\n', ' ')

        if 'use' in vs or 'sử dụng' in vs:
            col_map['Use'] = c
        elif 'frequency' in vs or 'tần suất' in vs:
            col_map['Frequency'] = c
        elif 'number of times' in vs or 'số lần' in vs:
            col_map['NumTimes'] = c
        elif ('unit price' in vs or 'đơn giá' in vs or 'price' in vs) and 'UnitPrice' not in col_map:
            col_map['UnitPrice'] = c
        elif ('total' in vs or 'tổng' in vs) and 'TotalPrice' not in col_map:
            col_map['TotalPrice'] = c
        elif 'remark' in vs or 'ghi chú' in vs or 'note' in vs:
            col_map['Remarks'] = c
        elif ('tham khao' in vs or 'tham khảo' in vs or 'ref' in vs or 'báo cáo' in vs):
            col_map['ItemRef'] = c

    return col_map


def _get_item_name_format_a(ws, r, col_map):
    """
    For Format A, the 'item name' is actually in the ItemRef column (col 6 typically),
    which contains the budget item description / reference project name.
    Try col_map['ItemRef'] first, fall back to col 4 or 5.
    """
    candidates = ['ItemRef', 'UnitPrice']  # UnitPrice col often has item desc in some files
    for key in candidates:
        if key in col_map:
            v = ws.cell(r, col_map[key]).value
            if v and str(v).strip() and not isinstance(v, (int, float)):
                return str(v).strip()

    # fallback: scan cols 4-8 for any non-numeric non-empty text
    for c in range(4, min(10, ws.max_column + 1)):
        v = ws.cell(r, c).value
        if v and isinstance(v, str) and len(v.strip()) > 2:
            return v.strip()
    return None


def extract_budget(wb, project_code: str, filepath: str, issues: list):
    """
    Extract budget data from all budget-related sheets.
    Handles two formats:
    - Format A: 2a/2b/2c.Budget-MF/Pre (Lumi, Green Skyline, Parking...)
    - Format B: B2.Chi tiết dự toán ngân sách (Fiato, 11D, A&K...)
    """
    rows = []

    target_sns = [sn for sn in wb.sheetnames if _is_budget_sheet(sn)]

    if not target_sns:
        issues.append(f"[BUDGET][{filepath}] Could not find any budget sheets.")
        return pd.DataFrame()

    for sn in target_sns:
        ws = wb[sn]
        header_row_idx, month_row_idx, month_cols = _find_header_and_month_row(ws)

        if header_row_idx == -1:
            issues.append(f"[BUDGET][{filepath}][{sn}] Could not locate header row.")
            continue

        col_map = _map_columns_format_a(ws, header_row_idx)

        # Determine first data row
        data_start = max(header_row_idx, month_row_idx if month_row_idx != -1 else 0) + 1

        if not month_cols:
            issues.append(f"[BUDGET][{filepath}][{sn}] No month columns found (no datetime in first 25 rows).")

        # --- Extract rows ---
        row_seq = 0
        for r in range(data_start, ws.max_row + 1):
            # Check "Use" column first - skip "Not Use" rows
            use_val = str(ws.cell(r, col_map.get('Use', 2)).value or '').strip().lower()
            if use_val == 'not use' or use_val == 'none':
                continue

            # Get Unit Price (the main cost figure when no monthly breakdown)
            def safe_float(c_key):
                if c_key in col_map:
                    v = ws.cell(r, col_map[c_key]).value
                    if isinstance(v, (int, float)):
                        return float(v)
                    if isinstance(v, str):
                        try:
                            return float(v.replace(',', '').strip())
                        except Exception:
                            pass
                return 0.0

            unit_price = safe_float('UnitPrice')
            total_price = safe_float('TotalPrice')
            num_times = safe_float('NumTimes') or 12.0
            frequency = str(ws.cell(r, col_map.get('Frequency', 3)).value or '').strip()
            remarks_v = ws.cell(r, col_map.get('Remarks', 0)).value if 'Remarks' in col_map else None
            remarks = norm(str(remarks_v)).strip() if remarks_v else None

            # Get item name - use ItemRef col or fallback
            item_name = _get_item_name_format_a(ws, r, col_map)

            # Skip rows with no item name and no financial data
            if not item_name and unit_price == 0 and total_price == 0:
                continue

            if item_name is None:
                item_name = f"{sn}_row{r}"

            row_seq += 1

            base_data = {
                'ProjectCode': project_code,
                'SourceSheet': sn,
                'SourceRow': r,
                'BudgetItemName': item_name,
                'Frequency': frequency,
                'NumTimes': num_times,
                'UnitPrice': unit_price,
                'YearlyTotal': total_price,
                'Remarks': remarks,
            }

            if not month_cols:
                if total_price != 0 or unit_price != 0:
                    row_data = base_data.copy()
                    row_data['MonthDate'] = None
                    row_data['MonthlyAmount'] = total_price / 12 if total_price else unit_price
                    rows.append(row_data)
            else:
                has_valid = False
                for m_col, m_date in month_cols:
                    m_val = ws.cell(r, m_col).value
                    if isinstance(m_val, (int, float)) and float(m_val) != 0:
                        row_data = base_data.copy()
                        row_data['MonthDate'] = m_date
                        row_data['MonthlyAmount'] = float(m_val)
                        rows.append(row_data)
                        has_valid = True

                if not has_valid and (total_price != 0 or unit_price != 0):
                    row_data = base_data.copy()
                    row_data['MonthDate'] = None
                    row_data['MonthlyAmount'] = total_price / 12 if total_price else unit_price
                    rows.append(row_data)

    return pd.DataFrame(rows)


def generate_dim_budget_category(fact_df: pd.DataFrame) -> pd.DataFrame:
    """Generate Dim_BudgetCategory from unique BudgetItemNames in Fact."""
    if fact_df.empty:
        return pd.DataFrame(columns=['BudgetCategoryKey', 'BudgetItemName_EN', 'BudgetItemName_VN'])

    unique = fact_df[['BudgetItemName']].drop_duplicates().reset_index(drop=True)
    unique = unique.sort_values('BudgetItemName').reset_index(drop=True)
    unique.insert(0, 'BudgetCategoryKey', range(1, len(unique) + 1))

    # Split BudgetItemName into EN and VN
    split_res = unique['BudgetItemName'].apply(split_en_vn)
    unique['BudgetItemName_EN'] = [x[0] for x in split_res]
    unique['BudgetItemName_VN'] = [x[1] for x in split_res]

    return unique[['BudgetCategoryKey', 'BudgetItemName', 'BudgetItemName_EN', 'BudgetItemName_VN']]
