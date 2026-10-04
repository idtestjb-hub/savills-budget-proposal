# RETIRED 2026-10-04 (backlog A7): paths point at a folder that does not exist; do not run. See legacy/README.md.
import os
import sys
import glob
import pandas as pd
import openpyxl
from datetime import datetime
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from common_utils_v2 import repair_workbook, project_code_from_filename, log_issues
from etl_project_info import extract_project_info, generate_dim_project
from etl_budget import extract_budget, generate_dim_budget_category
from etl_staff import extract_staff, generate_dim_position
from etl_service import extract_service, generate_dim_service_type
from etl_capex import extract_capex, generate_dim_equipment

INPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'input', 'budget_planning'))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output_v2'))

def main():
    os.makedirs(os.path.join(OUTPUT_DIR, 'MasterData'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, 'Transactions'), exist_ok=True)
    files = sorted(glob.glob(os.path.join(INPUT_DIR, '*.xlsx')))
    
    if not files:
        print(f"No Excel files found in {INPUT_DIR}")
        return

    all_issues = []
    base_projects = []
    
    # Collect raw facts
    raw_fact_info = []
    raw_fact_budget = []
    raw_fact_staff = []
    raw_fact_service = []
    raw_fact_capex = []

    print(f"Starting ETL V2 on {len(files)} files...")

    for i, filepath in enumerate(files, 1):
        filename = os.path.basename(filepath)
        print(f"[{i}/{len(files)}] Processing {filename}...")
        
        # 1. Repair and Load
        safe_path = repair_workbook(filepath)
        if safe_path != filepath:
            all_issues.append(f"[SYSTEM][{filename}] XML repaired.")
            
        try:
            wb = openpyxl.load_workbook(safe_path, data_only=True)
        except Exception as e:
            all_issues.append(f"[SYSTEM][{filename}] Failed to load workbook: {str(e)}")
            continue

        # 2. Base Project Identity
        pcode = project_code_from_filename(filepath, i)
        
        # Extract project name from cover/info or fallback to filename
        pname = os.path.splitext(filename)[0]
        from common_utils_v2 import find_sheet_loose
        cover = find_sheet_loose(wb, 'Cover')
        if cover:
            for r in wb[cover].iter_rows(min_row=1, max_row=15, values_only=True):
                for v in r:
                    if isinstance(v, str) and 'LUMI' in str(v).upper():
                        pname = str(v).strip()
                        break
        
        base_projects.append({
            'ProjectKey': i,
            'ProjectCode': pcode,
            'ProjectName': pname,
            'SourceFile': filename
        })
        
        # 3. Extract Data
        # Project Info
        df_info = extract_project_info(wb, pcode, pname, filename, all_issues)
        if not df_info.empty: raw_fact_info.append(df_info)
        
        # Budget
        df_budget = extract_budget(wb, pcode, filename, all_issues)
        if not df_budget.empty: raw_fact_budget.append(df_budget)
            
        # Staff
        df_staff = extract_staff(wb, pcode, filename, all_issues)
        if not df_staff.empty: raw_fact_staff.append(df_staff)
            
        # Service
        df_service = extract_service(wb, pcode, filename, all_issues)
        if not df_service.empty: raw_fact_service.append(df_service)
            
        # Capex
        df_capex = extract_capex(wb, pcode, filename, all_issues)
        if not df_capex.empty: raw_fact_capex.append(df_capex)
            
        wb.close()

    # Concatenate all raw facts
    df_raw_info = pd.concat(raw_fact_info, ignore_index=True) if raw_fact_info else pd.DataFrame()
    df_raw_budget = pd.concat(raw_fact_budget, ignore_index=True) if raw_fact_budget else pd.DataFrame()
    df_raw_staff = pd.concat(raw_fact_staff, ignore_index=True) if raw_fact_staff else pd.DataFrame()
    df_raw_service = pd.concat(raw_fact_service, ignore_index=True) if raw_fact_service else pd.DataFrame()
    df_raw_capex = pd.concat(raw_fact_capex, ignore_index=True) if raw_fact_capex else pd.DataFrame()

    print("\n--- Generating Dimensions ---")
    dim_project = generate_dim_project(df_raw_info, base_projects)
    dim_budget_cat = generate_dim_budget_category(df_raw_budget)
    dim_position = generate_dim_position(df_raw_staff)
    dim_service = generate_dim_service_type(df_raw_service)
    dim_equip = generate_dim_equipment(df_raw_capex)

    # Simple Dim_Date (from budget months)
    dim_date = pd.DataFrame(columns=['DateKey', 'Year', 'Month', 'DateString'])
    if not df_raw_budget.empty and 'MonthDate' in df_raw_budget.columns:
        dates = df_raw_budget['MonthDate'].dropna().unique()
        date_rows = []
        for d in dates:
            dt = pd.to_datetime(d)
            date_rows.append({
                'DateKey': int(dt.strftime('%Y%m%d')),
                'Year': dt.year,
                'Month': dt.month,
                'DateString': dt.strftime('%Y-%m-%d')
            })
        if date_rows:
            dim_date = pd.DataFrame(date_rows).sort_values('DateKey').reset_index(drop=True)

    print("--- Linking Facts to Dimensions ---")
    
    # 1. Fact_BudgetMonthly
    if not df_raw_budget.empty:
        fact_budget = df_raw_budget.merge(dim_project[['ProjectCode', 'ProjectKey']], on='ProjectCode', how='left')
        # Merge by BudgetItemName (new schema has no BudgetCode)
        fact_budget = fact_budget.merge(dim_budget_cat[['BudgetItemName', 'BudgetCategoryKey']], on='BudgetItemName', how='left')

        # Link DateKey safely
        if not dim_date.empty:
            date_map = dict(zip(dim_date['DateString'], dim_date['DateKey']))
            fact_budget['DateKey'] = fact_budget['MonthDate'].map(date_map)
        else:
            fact_budget['DateKey'] = None

        fact_budget.insert(0, 'FactKey', range(1, len(fact_budget) + 1))
        cols = ['FactKey', 'ProjectKey', 'BudgetCategoryKey', 'DateKey', 'MonthlyAmount',
                'UnitPrice', 'YearlyTotal', 'Frequency', 'NumTimes', 'Remarks', 'SourceSheet', 'SourceRow']
        fact_budget = fact_budget[[c for c in cols if c in fact_budget.columns]]
        fact_budget.to_csv(os.path.join(OUTPUT_DIR, 'Transactions', 'Fact_BudgetMonthly.csv'), index=False, encoding='utf-8-sig')
        print(f"  -> Fact_BudgetMonthly: {len(fact_budget)} rows")

    # 2. Fact_StaffCost
    if not df_raw_staff.empty:
        fact_staff = df_raw_staff.merge(dim_project[['ProjectCode', 'ProjectKey']], on='ProjectCode', how='left')
        fact_staff = fact_staff.merge(dim_position[['PositionName', 'PositionKey']], on='PositionName', how='left')
        fact_staff.insert(0, 'FactKey', range(1, len(fact_staff) + 1))
        cols = ['FactKey', 'ProjectKey', 'PositionKey', 'GrossSalary', 'SI_HI_Company', 'SI_HI_Employee', 
                'Unemployment', 'Month13', 'PIT', 'NetSalary', 'TotalCost', 'AdminFeeRate', 'AdminFeeAmount', 'SourceSheet']
        fact_staff = fact_staff[[c for c in cols if c in fact_staff.columns]]
        fact_staff.to_csv(os.path.join(OUTPUT_DIR, 'Transactions', 'Fact_StaffCost.csv'), index=False, encoding='utf-8-sig')

    # 3. Fact_ServiceCost
    if not df_raw_service.empty:
        fact_svc = df_raw_service.merge(dim_project[['ProjectCode', 'ProjectKey']], on='ProjectCode', how='left')
        # rename PositionName back to ServiceName for matching
        fact_svc.rename(columns={'PositionName': 'ServiceName'}, inplace=True)
        fact_svc = fact_svc.merge(dim_service[['ServiceName', 'ServiceType', 'ServiceKey']], on=['ServiceName', 'ServiceType'], how='left')
        fact_svc.insert(0, 'FactKey', range(1, len(fact_svc) + 1))
        cols = ['FactKey', 'ProjectKey', 'ServiceKey', 'WorkHoursPerDay', 'Quantity', 'UnitPrice', 'TotalAmount', 'Remarks', 'SourceSheet']
        fact_svc = fact_svc[[c for c in cols if c in fact_svc.columns]]
        fact_svc.to_csv(os.path.join(OUTPUT_DIR, 'Transactions', 'Fact_ServiceCost.csv'), index=False, encoding='utf-8-sig')

    # 4. Fact_Capex
    if not df_raw_capex.empty:
        fact_cap = df_raw_capex.merge(dim_project[['ProjectCode', 'ProjectKey']], on='ProjectCode', how='left')
        fact_cap = fact_cap.merge(dim_equip[['ItemName', 'CapexCategory', 'Unit', 'EquipmentKey']], on=['ItemName', 'CapexCategory', 'Unit'], how='left')
        fact_cap.insert(0, 'FactKey', range(1, len(fact_cap) + 1))
        cols = ['FactKey', 'ProjectKey', 'EquipmentKey', 'Quantity', 'UnitPrice', 'TotalAmount', 'Remarks', 'SourceSheet']
        fact_cap = fact_cap[[c for c in cols if c in fact_cap.columns]]
        fact_cap.to_csv(os.path.join(OUTPUT_DIR, 'Transactions', 'Fact_Capex.csv'), index=False, encoding='utf-8-sig')

    # Drop original name columns from dimensions before saving
    if 'BudgetItemName' in dim_budget_cat.columns: dim_budget_cat.drop(columns=['BudgetItemName'], inplace=True)
    if 'PositionName' in dim_position.columns: dim_position.drop(columns=['PositionName'], inplace=True)
    if 'ServiceName' in dim_service.columns: dim_service.drop(columns=['ServiceName'], inplace=True)
    if 'ItemName' in dim_equip.columns: dim_equip.drop(columns=['ItemName'], inplace=True)

    # Save Dimensions to MasterData
    dim_project.to_csv(os.path.join(OUTPUT_DIR, 'MasterData', 'Dim_Project.csv'), index=False, encoding='utf-8-sig')
    dim_budget_cat.to_csv(os.path.join(OUTPUT_DIR, 'MasterData', 'Dim_BudgetCategory.csv'), index=False, encoding='utf-8-sig')
    dim_position.to_csv(os.path.join(OUTPUT_DIR, 'MasterData', 'Dim_Position.csv'), index=False, encoding='utf-8-sig')
    dim_service.to_csv(os.path.join(OUTPUT_DIR, 'MasterData', 'Dim_ServiceType.csv'), index=False, encoding='utf-8-sig')
    dim_equip.to_csv(os.path.join(OUTPUT_DIR, 'MasterData', 'Dim_Equipment.csv'), index=False, encoding='utf-8-sig')
    dim_date.to_csv(os.path.join(OUTPUT_DIR, 'MasterData', 'Dim_Date.csv'), index=False, encoding='utf-8-sig')

    # Save Issues
    log_issues(all_issues, OUTPUT_DIR)
    
    print("\n--- SUMMARY ---")
    print(f"Projects: {len(dim_project)}")
    print(f"Budget Categories: {len(dim_budget_cat)}")
    print(f"Positions: {len(dim_position)}")
    print(f"Services: {len(dim_service)}")
    print(f"Equipment: {len(dim_equip)}")
    print(f"Date periods: {len(dim_date)}")
    print("--------------------")
    print(f"Fact Budget records: {len(df_raw_budget)}")
    print(f"Fact Staff records: {len(df_raw_staff)}")
    print(f"Fact Service records: {len(df_raw_service)}")
    print(f"Fact Capex records: {len(df_raw_capex)}")
    print(f"\nETL completed successfully. Outputs saved to {OUTPUT_DIR}")
    print(f"Logged {len(all_issues)} parsing issues.")

if __name__ == '__main__':
    main()
