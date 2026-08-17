import pandas as pd
from common_utils_v2 import find_sheet_loose, norm, get_dept_abbr

def extract_staff(wb, project_code: str, filepath: str, issues: list):
    """
    Extract data from 'B3. Chi phí nhân sự'.
    Generates Fact_StaffCost.
    """
    rows = []
    
    target_sns = []
    for sn in wb.sheetnames:
        sn_lower = sn.lower()
        if 'b3. chi phí' in sn_lower or 'b3.chi phí' in sn_lower or 'staff cost' in sn_lower or 'ca đêm' in sn_lower or 'lịch lễ tân' in sn_lower or 'roster' in sn_lower or 'sc ' in sn_lower or 'night shift' in sn_lower:
            target_sns.append(sn)
            
    if not target_sns:
        sn = find_sheet_loose(wb, 'B3')
        if sn: target_sns.append(sn)

    if not target_sns:
        issues.append(f"[STAFF][{filepath}] Could not find any staff sheets.")
        return pd.DataFrame()
        
    for sn in target_sns:
        ws = wb[sn]
        
        # 1. Find the header row (contains 'Position' or 'Vị trí')
        header_row_idx = -1
        for r in range(1, min(ws.max_row, 30)):
            for c in range(1, min(ws.max_column, 20) + 1):
                val_str = str(ws.cell(r, c).value).lower()
                if 'position' in val_str or 'vị trí' in val_str:
                    header_row_idx = r
                    break
            if header_row_idx != -1:
                break
                
        if header_row_idx == -1:
            issues.append(f"[STAFF][{filepath}] Could not find header row in {sn}.")
            continue

        # 2. Map columns
        col_map = {}
        for c in range(1, min(ws.max_column, 40) + 1):
            val = ws.cell(header_row_idx, c).value
            if not val: continue
            val_str = norm(str(val)).strip().lower()
            
            if 'vi tri' in val_str or 'vị trí' in val_str or 'position' in val_str:
                if 'PositionName' not in col_map: col_map['PositionName'] = c
            elif 'name' in val_str or 'code' in val_str or 'ky hieu' in val_str: 
                if 'PositionCode' not in col_map: col_map['PositionCode'] = c
            elif 'luong' in val_str or 'lương' in val_str or 'gross' in val_str:
                if 'de nghi' in val_str or 'đề nghị' in val_str: col_map['GrossSalary_Proposed'] = c
                elif 'GrossSalary' not in col_map: col_map['GrossSalary'] = c
            elif 'bhxh' in val_str and ('bhs' in val_str or '20' in val_str or '21' in val_str): col_map['SI_HI_Company'] = c
            elif 'bhxh' in val_str and ('bhs' in val_str or '9' in val_str or '10' in val_str): col_map['SI_HI_Employee'] = c
            elif 'bhtn' in val_str and '1%' in val_str: col_map['Unemployment'] = c
            elif 'thang 13' in val_str or 'tháng 13' in val_str or '13th' in val_str: col_map['Month13'] = c
            elif 'thue tncn' in val_str or 'thuế tncn' in val_str or 'pit' in val_str: col_map['PIT'] = c
            elif 'thuc lanh' in val_str or 'thực lãnh' in val_str or 'net' in val_str: col_map['NetSalary'] = c
            elif 'tong chi phi' in val_str or 'tổng chi phí' in val_str or 'total cost' in val_str: col_map['TotalCost'] = c
            elif 'admin fee' in val_str or 'phi quan ly' in val_str or 'phí quản lý' in val_str:
                # check if percentage or amount by row values later, just store index
                if '%' in val_str or 'rate' in val_str or 'ty le' in val_str or 'tỷ lệ' in val_str: col_map['AdminFeeRate'] = c
                else: col_map['AdminFee'] = c

        if 'PositionName' not in col_map:
            issues.append(f"[STAFF][{filepath}] Missing PositionName column in {sn}.")
            continue

        # 3. Extract rows
        for r in range(header_row_idx + 1, ws.max_row + 1):
            pos_name = str(ws.cell(r, col_map['PositionName']).value or '').strip()
            
            # Skip empty or summary rows
            if not pos_name or pos_name.upper() in ['TOTAL', 'TỔNG CỘNG', 'TỔNG', 'NONE']:
                continue
                
            def safe_float(c_key):
                if c_key in col_map:
                    v = ws.cell(r, col_map[c_key]).value
                    if isinstance(v, (int, float)): return float(v)
                    if isinstance(v, str):
                        try: return float(v.replace(',','').strip())
                        except: pass
                return 0.0
                
            def safe_str(c_key):
                if c_key in col_map:
                    v = ws.cell(r, col_map[c_key]).value
                    if v: return norm(str(v)).strip()
                return None
                
            gross = safe_float('GrossSalary_Proposed') or safe_float('GrossSalary')
            total_cost = safe_float('TotalCost')
            
            # We assume 1 headcount per row if salary or cost is defined
            if gross > 0 or total_cost > 0:
                rows.append({
                    'ProjectCode': project_code,
                    'SourceSheet': sn,
                    'PositionName': pos_name,
                    'PositionCode': safe_str('PositionCode') or 'GEN',
                    'GrossSalary': gross,
                    'SI_HI_Company': safe_float('SI_HI_Company'),
                    'SI_HI_Employee': safe_float('SI_HI_Employee'),
                    'Unemployment': safe_float('Unemployment'),
                    'Month13': safe_float('Month13'),
                    'PIT': safe_float('PIT'),
                    'NetSalary': safe_float('NetSalary'),
                    'TotalCost': total_cost,
                    'AdminFeeRate': safe_float('AdminFeeRate'),
                    'AdminFeeAmount': safe_float('AdminFee')
                })
                
    return pd.DataFrame(rows)

from common_utils_v2 import split_en_vn

def generate_dim_position(fact_df: pd.DataFrame) -> pd.DataFrame:
    """Generate Dim_Position from unique PositionNames."""
    if fact_df.empty:
        return pd.DataFrame(columns=['PositionKey', 'PositionCode', 'PositionName_EN', 'PositionName_VN', 'DeptAbbr'])
        
    unique = fact_df[['PositionName']].drop_duplicates().reset_index(drop=True)
    unique['DeptAbbr'] = unique['PositionName'].apply(get_dept_abbr)
    
    unique = unique.sort_values(['DeptAbbr', 'PositionName']).reset_index(drop=True)
    
    # Generate structured Position Code
    unique['Seq'] = unique.groupby('DeptAbbr').cumcount() + 1
    unique['PositionCode'] = unique.apply(lambda r: f"POS-{r['DeptAbbr']}-{r['Seq']:03d}", axis=1)
    
    unique.insert(0, 'PositionKey', range(1, len(unique) + 1))
    
    # Split PositionName into EN and VN
    split_res = unique['PositionName'].apply(split_en_vn)
    unique['PositionName_EN'] = [x[0] for x in split_res]
    unique['PositionName_VN'] = [x[1] for x in split_res]
    return unique[['PositionKey', 'PositionCode', 'PositionName', 'PositionName_EN', 'PositionName_VN', 'DeptAbbr']]
