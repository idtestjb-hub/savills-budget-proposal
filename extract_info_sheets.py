"""
Extracts the canonical property-scale "Info" sheet from a real project budget file.

Every real project file has one of these under a different name/format ('Info ', '0. Info',
'Info (X)') but the SAME underlying shape: land/building scale block -> per-product-type table
(GFA/NFA/Units + fee rate) -> parking table. This is what confirmed the ground-truth intake
schema in 05_Project_Intake_Template.md.

Unlike etl_project_info.py (generic key-value scraper, good for automated bulk extraction),
this module targets the SPECIFIC known layout precisely -- use it when you need verified,
structured values (GFA/NFA/Units per product type, parking ownership split), not just a loose
key-value dump. Good candidate to reconcile with etl_project_info.py once the 150-project
extraction pass needs to run unattended.

Reusable for: scaling Dim_Property beyond the 8 verified rows already in
output/copilot_studio_package/data/Dim_Property_v2_verified.csv.
"""
import os
import glob
import openpyxl

from common_utils_v2 import repair_workbook, norm

# Canonical Info-sheet candidates, in priority order (prefer the richer '0. Info' /
# English-labeled format when both exist -- it carries unit prices, the Vietnamese 'Info '
# format usually doesn't).
INFO_SHEET_CANDIDATES = ['0. Info', 'Info ', 'Info (']


def find_info_sheet(wb):
    """Return the sheet name of the canonical Info sheet, or None."""
    names = wb.sheetnames
    for cand in INFO_SHEET_CANDIDATES:
        for sn in names:
            if norm(sn).strip().lower().startswith(norm(cand).strip().lower()):
                return sn
    return None


def dump_info_sheet(filepath: str, max_row: int = 40):
    """
    Print every non-empty row of a project file's canonical Info sheet.
    Use this first, by hand, before writing a parser for a new/unfamiliar project file --
    the layout is consistent in spirit but column offsets drift slightly between files
    (see the caveat in 05_Project_Intake_Template.md about "construction footprint").
    """
    repaired = repair_workbook(filepath)
    wb = openpyxl.load_workbook(repaired, data_only=True)
    sheet = find_info_sheet(wb)
    if not sheet:
        print(f'NO INFO SHEET FOUND in {os.path.basename(filepath)}')
        return
    ws = wb[sheet]
    print(f'=== {os.path.basename(filepath)} | {sheet!r} | dims={ws.dimensions} ===')
    for row in ws.iter_rows(min_row=1, max_row=max_row, values_only=True):
        vals = [v for v in row if v is not None]
        if vals:
            print(vals[:12])


if __name__ == '__main__':
    # Quick manual spot-check across the budget_planning folder.
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    files = glob.glob(os.path.join(base, 'input', 'budget_planning', '*.xlsx'))
    files = [f for f in files if '__' not in os.path.basename(f) and 'MasterData' not in f
             and 'Budget_Workbook' not in f and 'Sheet_Index' not in f and 'PowerBI' not in f]
    for f in files:
        dump_info_sheet(f)
        print()
