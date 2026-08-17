import pandas as pd
from common_utils_v2 import find_sheet_loose, norm

def extract_capex(wb, project_code: str, filepath: str, issues: list):
    """
    Extract data from B7 (MO), B8 (M&E), and B9 (Public Area) sheets.
    Generates Fact_Capex.
    """
    rows = []
    
    sheets_to_process = [
        ('MO Equipment', ['b7', 'capex mo']),
        ('M&E Equipment', ['b8', 'capex m&e', 'ccdc m&e', 'capex me']),
        ('Public Area', ['b9', 'capex khu công cộng', 'capex kcc'])
    ]
    
    for category, keywords in sheets_to_process:
        target_sns = []
        for sn in wb.sheetnames:
            sn_lower = sn.lower()
            if any(k in sn_lower for k in keywords):
                target_sns.append(sn)
                
        for sn in target_sns:
            ws = wb[sn]
            
            # Find header
            header_row_idx = -1
            col_map = {}
            for r in range(1, min(ws.max_row, 30)):
                temp_map = {}
                for c in range(1, min(ws.max_column, 30) + 1):
                    val = ws.cell(r, c).value
                    if not val:
                        val = ws.cell(r + 1, c).value
                        if not val: continue
                        
                    val_str = norm(str(val)).strip().lower()
                    
                    if ('trang thiet bi' in val_str or 'trang thiết bị' in val_str or 'equipment' in val_str or 'item' in val_str) and 'ItemName' not in temp_map: temp_map['ItemName'] = c
                    elif ('don vi' in val_str or 'đơn vị' in val_str or 'unit' in val_str) and 'Unit' not in temp_map:
                        if 'price' not in val_str and 'gia' not in val_str and 'giá' not in val_str: temp_map['Unit'] = c
                    elif ('so luong' in val_str or 'số lượng' in val_str or 'quantity' in val_str or 'qty' in val_str) and 'Quantity' not in temp_map: temp_map['Quantity'] = c
                    elif ('don gia' in val_str or 'đơn giá' in val_str or 'unit price' in val_str or 'price' in val_str) and 'UnitPrice' not in temp_map: temp_map['UnitPrice'] = c
                    elif ('tong cong' in val_str or 'tổng cộng' in val_str or 'tong chi phi' in val_str or 'total' in val_str) and 'TotalAmount' not in temp_map: temp_map['TotalAmount'] = c
                    elif ('ghi chu' in val_str or 'ghi chú' in val_str or 'remark' in val_str or 'note' in val_str) and 'Remarks' not in temp_map: temp_map['Remarks'] = c
                
                if 'ItemName' in temp_map and ('Quantity' in temp_map or 'TotalAmount' in temp_map or 'UnitPrice' in temp_map):
                    header_row_idx = r
                    col_map = temp_map
                    break
                    
            if header_row_idx == -1 or 'ItemName' not in col_map:
                issues.append(f"[CAPEX][{filepath}] Could not find header row in {sn}.")
                continue
                
            # Extract rows
            for r in range(header_row_idx + 1, ws.max_row + 1):
                item_name = str(ws.cell(r, col_map['ItemName']).value or '').strip()
                
                # Skip empty, headers (usually roman numerals), or subtotals
                if not item_name or item_name.upper() in ['TOTAL', 'TỔNG CỘNG', 'NONE'] or len(item_name) <= 3:
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
                    
                qty = safe_float('Quantity')
                ta = safe_float('TotalAmount')
                if qty > 0 or ta > 0:
                    rows.append({
                        'ProjectCode': project_code,
                        'SourceSheet': sn,
                        'CapexCategory': category,
                        'ItemName': item_name,
                        'Unit': safe_str('Unit'),
                        'Quantity': qty,
                        'UnitPrice': safe_float('UnitPrice'),
                        'TotalAmount': ta,
                        'Remarks': safe_str('Remarks')
                    })
                
    return pd.DataFrame(rows)

from common_utils_v2 import split_en_vn

def generate_dim_equipment(fact_df: pd.DataFrame) -> pd.DataFrame:
    if fact_df.empty:
        return pd.DataFrame(columns=['EquipmentKey', 'EquipmentCode', 'ItemName_EN', 'ItemName_VN', 'CapexCategory', 'Unit'])
        
    unique = fact_df[['CapexCategory', 'ItemName', 'Unit']].drop_duplicates().reset_index(drop=True)
    unique.insert(0, 'EquipmentKey', range(1, len(unique) + 1))
    
    def get_code(cat):
        if 'MO' in cat: return 'MO'
        if 'M&E' in cat: return 'ME'
        return 'PUB'
        
    unique['EquipmentCode'] = unique.apply(lambda r: f"CPX-{get_code(r['CapexCategory'])}-{r['EquipmentKey']:04d}", axis=1)
    
    # Split ItemName into EN and VN
    split_res = unique['ItemName'].apply(split_en_vn)
    unique['ItemName_EN'] = [x[0] for x in split_res]
    unique['ItemName_VN'] = [x[1] for x in split_res]
    return unique[['EquipmentKey', 'EquipmentCode', 'ItemName', 'ItemName_EN', 'ItemName_VN', 'CapexCategory', 'Unit']]
