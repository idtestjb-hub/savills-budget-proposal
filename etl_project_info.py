import os
import pandas as pd
from common_utils_v2 import find_sheet_loose, norm

def extract_project_info(wb, project_code: str, project_name: str, filepath: str, issues: list):
    """
    Extract key attributes from '0. Info', 'Master Info', or 'Info (*)' sheets.
    Produces Fact_ProjectInfo rows.
    """
    rows = []
    
    # Try finding the info sheet
    info_sheet = None
    for cand in ['0. Info', 'Master Info', 'Info (']:
        found = find_sheet_loose(wb, cand)
        if found:
            info_sheet = found
            break
            
    if not info_sheet:
        issues.append(f"[INFO][{filepath}] Could not find Info sheet.")
        return pd.DataFrame(columns=['ProjectCode', 'ProjectName', 'AttributeName', 'AttributeValue', 'Unit', 'SourceSheet'])
        
    ws = wb[info_sheet]
    
    # Scan first 60 rows for key-value pairs (String in col 0/1/2, Number in subsequent cols)
    for row in ws.iter_rows(min_row=1, max_row=60, values_only=True):
        # We expect up to 10 columns
        vals = list(row[:10])
        
        text_vals = [v for v in vals if isinstance(v, str) and str(v).strip()]
        num_vals = [v for v in vals if isinstance(v, (int, float))]
        
        if len(text_vals) >= 1 and num_vals:
            attr_name = norm(text_vals[0]).strip()
            # Ignore long sentences or irrelevant text
            if len(attr_name) > 100 or 'project' in attr_name.lower():
                continue
                
            attr_val = num_vals[0]
            unit = None
            if len(text_vals) > 1:
                # Find the unit which is usually a short string
                for t in text_vals[1:]:
                    if len(str(t).strip()) <= 15:
                        unit = norm(t).strip()
                        break
            
            rows.append({
                'ProjectCode': project_code,
                'ProjectName': project_name,
                'AttributeName': attr_name,
                'AttributeValue': attr_val,
                'Unit': unit,
                'SourceSheet': info_sheet
            })
            
    df = pd.DataFrame(rows).drop_duplicates()
    return df

def generate_dim_project(fact_info_df: pd.DataFrame, base_projects: list) -> pd.DataFrame:
    """
    Generate Dim_Project by aggregating info from base projects and Fact_ProjectInfo.
    base_projects is a list of dicts: {'ProjectCode': c, 'ProjectName': n, 'SourceFile': f, 'ProjectKey': k}
    """
    dim_rows = []
    
    for bp in base_projects:
        code = bp['ProjectCode']
        proj_fact = fact_info_df[fact_info_df['ProjectCode'] == code]
        
        # Helper to extract specific metric
        def get_metric(keywords):
            for k in keywords:
                match = proj_fact[proj_fact['AttributeName'].str.lower().str.contains(k.lower(), na=False)]
                if not match.empty:
                    return match.iloc[0]['AttributeValue']
            return None
            
        dim_row = {
            'ProjectKey': bp['ProjectKey'],
            'ProjectCode': code,
            'ProjectName': bp['ProjectName'],
            'SourceFile': bp['SourceFile'],
            'LandArea_m2': get_metric(['Diện tích đất', 'Khuôn viên', 'Land Area']),
            'GFA_m2': get_metric(['Diện tích xây dựng', 'GFA', 'Gross Floor Area']),
            'NFA_m2': get_metric(['Diện tích thu phí', 'NFA', 'Net Floor Area']),
            'TotalFloors': get_metric(['Tầng nổi', 'Total Floor', 'Số tầng']),
            'TotalApartments': get_metric(['Số căn hộ', 'Apartment', 'Tổng số căn']),
            'TotalVillas': get_metric(['Số biệt thự', 'Villa']),
            'CarParkingSlots': get_metric(['Đậu ô tô', 'Car Parking']),
            'MotoParkingSlots': get_metric(['Đậu xe máy', 'Moto']),
        }
        dim_rows.append(dim_row)
        
    return pd.DataFrame(dim_rows)
