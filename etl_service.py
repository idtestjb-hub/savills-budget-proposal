import pandas as pd
from common_utils_v2 import find_sheet_loose, norm

def extract_service(wb, project_code: str, filepath: str, issues: list):
    """
    Extract data from B4 (Security) and B5 (Cleaning) sheets.
    Generates Fact_ServiceCost.
    """
    rows = []
    with open('service_debug_3.txt', 'a', encoding='utf-8') as f:
        f.write(f'Extracting for {project_code}\n')
        
    sheets_to_process = [
        ('Security', ['b4', 'bảo vệ', 'security']),
        ('Cleaning', ['b5', 'vệ sinh', 'cleaning', 'landscape', 'cây xanh', 'pest control'])
    ]
    
    for service_type, keywords in sheets_to_process:
        target_sns = []
        for sn in wb.sheetnames:
            sn_lower = sn.lower()
            # Must avoid "B4. DT Quảng cáo" since it's revenue, not service cost.
            if 'quảng cáo' in sn_lower or 'adv' in sn_lower:
                continue
            # Broad substring matching
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
                    
                    if ('vi tri' in val_str or 'position' in val_str or 'vị trí' in val_str) and 'PositionName' not in temp_map: temp_map['PositionName'] = c
                    elif ('so gio' in val_str or 'số giờ' in val_str or 'hours' in val_str) and 'WorkHoursPerDay' not in temp_map: temp_map['WorkHoursPerDay'] = c
                    elif ('so luong' in val_str or 'số lượng' in val_str or 'quantity' in val_str or 'qty' in val_str or 'number' in val_str) and 'Quantity' not in temp_map: temp_map['Quantity'] = c
                    elif ('don gia' in val_str or 'đơn giá' in val_str or 'unit price' in val_str or 'price' in val_str) and 'UnitPrice' not in temp_map: temp_map['UnitPrice'] = c
                    elif ('tong chi phi' in val_str or 'tổng chi phí' in val_str or 'total cost' in val_str or 'thanh tien' in val_str) and 'TotalAmount' not in temp_map: temp_map['TotalAmount'] = c
                    elif ('ghi chu' in val_str or 'ghi chú' in val_str or 'remark' in val_str or 'note' in val_str) and 'Remarks' not in temp_map: temp_map['Remarks'] = c
                
                if 'PositionName' in temp_map and ('Quantity' in temp_map or 'TotalAmount' in temp_map or 'UnitPrice' in temp_map):
                    header_row_idx = r
                    col_map = temp_map
                    break
                    
            if header_row_idx == -1 or 'PositionName' not in col_map:
                issues.append(f"[SERVICE][{filepath}] Could not find header row in {sn}.")
                continue
                
            # Extract rows
            for r in range(header_row_idx + 1, ws.max_row + 1):
                pos_name = str(ws.cell(r, col_map['PositionName']).value or '').strip()
                if not pos_name or pos_name.upper() in ['TOTAL', 'TỔNG CỘNG', 'NONE']:
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
                        'ServiceType': service_type,
                        'PositionName': pos_name,
                        'WorkHoursPerDay': safe_float('WorkHoursPerDay'),
                        'Quantity': qty,
                        'UnitPrice': safe_float('UnitPrice'),
                        'TotalAmount': ta,
                        'Remarks': safe_str('Remarks')
                    })
                
    return pd.DataFrame(rows)

from common_utils_v2 import split_en_vn

def generate_dim_service_type(fact_df: pd.DataFrame) -> pd.DataFrame:
    if fact_df.empty:
        return pd.DataFrame(columns=['ServiceKey', 'ServiceCode', 'ServiceName_EN', 'ServiceName_VN', 'ServiceType'])
        
    unique = fact_df[['ServiceType', 'PositionName']].drop_duplicates().reset_index(drop=True)
    unique.insert(0, 'ServiceKey', range(1, len(unique) + 1))
    
    # Generate structured Code
    unique['ServiceCode'] = unique.apply(lambda r: f"SVC-{'SEC' if r['ServiceType']=='Security' else 'CLN'}-{r['ServiceKey']:03d}", axis=1)
    
    unique.rename(columns={'PositionName': 'ServiceName'}, inplace=True)
    
    # Split ServiceName into EN and VN
    split_res = unique['ServiceName'].apply(split_en_vn)
    unique['ServiceName_EN'] = [x[0] for x in split_res]
    unique['ServiceName_VN'] = [x[1] for x in split_res]
    return unique[['ServiceKey', 'ServiceCode', 'ServiceName', 'ServiceName_EN', 'ServiceName_VN', 'ServiceType']]
