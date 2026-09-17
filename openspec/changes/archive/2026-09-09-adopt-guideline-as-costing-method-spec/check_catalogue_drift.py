"""D6 drift check — does every catalogued code still exist in the current standard template?

Run:  python openspec/changes/adopt-guideline-as-costing-method-spec/check_catalogue_drift.py

Not wired into the pipeline or verify.py. A standalone check to run when Savills revises the
template: it holds Costing_Method_Catalogue.csv against the budget-line codes of
'2. Budget-Management Fund' + '3. Budget-Sinking Fund' in the standard form
(docs/AI Guideline - 2027 Resi Budget Form (IT team) .xlsx). Exit 0 = no drift.
"""
import csv, io, os, sys, warnings
warnings.simplefilter("ignore")
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))  # -> Budget_Agent
sys.path.insert(0, os.path.join(ROOT, "source_code"))
from common_utils_v2 import repair_workbook, find_sheet_loose  # noqa: E402

GUIDE = os.path.join(ROOT, "..", "docs", "AI Guideline - 2027 Resi Budget Form (IT team) .xlsx")
CATALOGUE = os.path.join(ROOT, "data", "master_list_verified", "Costing_Method_Catalogue.csv")


def _code_col(ws):
    """The column whose header cell (rows 1-12) reads 'CODE' — Y on the mgmt sheet, Z on sinking."""
    for row in ws.iter_rows(min_row=1, max_row=12):
        for cell in row:
            if cell.value and str(cell.value).strip().upper().startswith("CODE"):
                return cell.column
    return 25


def template_codes():
    wb = openpyxl.load_workbook(repair_workbook(GUIDE), data_only=True)
    codes = set()
    for sheet in ("2. Budget-Management Fund", "3. Budget-Sinking Fund"):
        ws = wb[find_sheet_loose(wb, sheet)]
        col = _code_col(ws)
        for row in ws.iter_rows(min_row=11):
            v = ws.cell(row=row[0].row, column=col).value
            if v and str(v).strip() and str(v).strip() not in ("CODE", "Mã"):
                codes.add(str(v).strip())
    return codes


def catalogue_codes():
    with open(CATALOGUE, encoding="utf-8-sig") as f:
        body = "".join(line for line in f if not line.startswith("#"))
    return [r["code"] for r in csv.DictReader(io.StringIO(body))]


def main():
    tmpl = template_codes()
    cat = catalogue_codes()
    orphans = [c for c in cat if c not in tmpl]
    print(f"template codes (mgmt + sinking): {len(tmpl)}")
    print(f"catalogue rows                 : {len(cat)}")
    if orphans:
        print("DRIFT — catalogued codes no longer in the template:")
        for c in orphans:
            print(f"  {c}")
        return 1
    print("no drift — every catalogued code is present in the standard template")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
