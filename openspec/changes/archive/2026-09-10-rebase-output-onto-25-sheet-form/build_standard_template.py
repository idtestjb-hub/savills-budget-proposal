"""One-time builder (design.md D1) — produces the blank standard budget template.

Run:  python openspec/changes/rebase-output-onto-25-sheet-form/build_standard_template.py

Not wired into the pipeline. Re-run when Savills revises the form.

Input : docs/AI Guideline - 2027 Resi Budget Form (IT team) .xlsx
Output: input/template/2027 Resi Budget Form (IT team).xlsx

Steps:
  - repair (strip the corrupt definedNames) and open with formulas intact
  - drop the `Master Info ( tính Staff cost)` sheet (external-workbook links + #REF!, design D3)
  - clear the `AI GUIDELINE` instruction cells and the B2.6 example working columns
  - clear the identifiable THẢO ĐIỀN GREEN project inputs on the three new sheets (formulas kept)
  - save
"""
import os, re, sys, shutil, tempfile, warnings, zipfile
warnings.simplefilter("ignore")
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))          # -> Budget_Agent
BASE = os.path.abspath(os.path.join(ROOT, ".."))                            # -> Project_Clone2_NewData
sys.path.insert(0, os.path.join(ROOT, "source_code"))
from common_utils_v2 import repair_workbook, find_sheet_loose  # noqa: E402

SRC = os.path.join(BASE, "docs", "AI Guideline - 2027 Resi Budget Form (IT team) .xlsx")
OUT = os.path.join(BASE, "input", "template", "2027 Resi Budget Form (IT team).xlsx")

DROP_SHEET = "Master Info ( tính Staff cost)"

# sheet-name query -> columns (1-based) to blank out entirely (instruction / example-working)
CLEAR_COLS = {
    "0. Info": [12],                       # L  AI GUIDELINE
    "1. Summary": [12],                    # L  AI GUIDELINE
    "2. Budget-Management Fund": [23],     # W  AI GUIDELINE
    "A2. Bảo vệ - Security": [22],         # V  advisory
    "A3. Vệ sinh - Cleaning": [25],        # Y  advisory
    "B2.6 Rác sinh hoạt (QD67)": [8],      # H  AI GUIDELINE (I/J/K left — an example working area
                                          #    that feeds nothing; the real output is column F)
}

# sheet-name query -> explicit cells/ranges whose NON-formula value is a THẢO ĐIỀN GREEN project input
CLEAR_INPUTS = {
    # G15 ships a placeholder note ("Link số theo mã vị trí..."), a text value that makes
    # `=ROUND((G15*H15)+G15,0)` and 47 downstream sums #VALUE! in a blank workbook. The pipeline
    # overwrites G15 with the computed PM salary; clearing it here keeps the blank template clean.
    "A1. Staff cost 08.2026 (VN)": ["G15"],
    "Tỷ lệ lấp đầy cư dân": (
        ["C1", "E3", "E6", "E7", "F6", "F7", "E18", "E19"]
        + [f"{c}6" for c in "GHIJKLMNOPQR"]
        + [f"{c}7" for c in "GHIJKLMNOPQR"]
        + [f"{c}20" for c in "GHIJKLM"]
    ),
    "Tiến độ lấp đầy bãi xe": (
        ["C1", "D6", "D7", "D9", "D10", "D11", "N9", "O9", "P9", "Q9"]
    ),
}


def strip_external_links(path):
    """Remove all xl/externalLinks/* parts and their references.

    The AI Guideline form ships 4 stale external-workbook links (other projects' local files, a
    personal Downloads path) that were only reachable from `Master Info`. With that sheet dropped
    nothing references them; left in, Excel refuses to open the file. Mirrors repair_workbook's
    definedNames surgery.
    """
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        n_dropped = 0
        for item in zin.namelist():
            if item.startswith("xl/externalLinks/"):
                n_dropped += 1
                continue
            data = zin.read(item)
            if item == "xl/workbook.xml":
                t = data.decode("utf-8")
                t = re.sub(r"<externalReferences>.*?</externalReferences>", "", t, flags=re.DOTALL)
                data = t.encode("utf-8")
            elif item == "xl/_rels/workbook.xml.rels":
                t = data.decode("utf-8")
                t = re.sub(r'<Relationship[^>]*externalLink[^>]*/>', "", t)
                data = t.encode("utf-8")
            elif item == "[Content_Types].xml":
                t = data.decode("utf-8")
                t = re.sub(r'<Override[^>]*externalLink[^>]*/>', "", t)
                data = t.encode("utf-8")
            zout.writestr(item, data)
    os.replace(tmp, path)
    print(f"stripped {n_dropped} externalLinks parts")


def main():
    loc = os.path.join(tempfile.gettempdir(), "bst_" + os.path.basename(SRC))
    shutil.copyfile(SRC, loc)
    wb = openpyxl.load_workbook(repair_workbook(loc), data_only=False)

    if DROP_SHEET in wb.sheetnames:
        del wb[DROP_SHEET]
        print(f"dropped sheet: {DROP_SHEET}")

    cleared_cells = 0
    for q, cols in CLEAR_COLS.items():
        ws = wb[find_sheet_loose(wb, q)]
        for row in ws.iter_rows():
            for c in row:
                if c.column in cols and c.value is not None:
                    c.value = None
                    cleared_cells += 1
    print(f"cleared {cleared_cells} instruction / example-working cells")

    inputs_cleared = kept_formula = 0
    for q, coords in CLEAR_INPUTS.items():
        ws = wb[find_sheet_loose(wb, q)]
        for coord in coords:
            cell = ws[coord]
            if isinstance(cell.value, str) and cell.value.startswith("="):
                kept_formula += 1
                continue
            if cell.value is not None:
                cell.value = None
                inputs_cleared += 1
    print(f"cleared {inputs_cleared} project-input cells on the new sheets ({kept_formula} formulas kept)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    strip_external_links(OUT)
    print(f"\nwrote {OUT}")

    check = openpyxl.load_workbook(OUT, read_only=True)
    print(f"sheets ({len(check.sheetnames)}):")
    for s in check.sheetnames:
        print(f"  {s}")


if __name__ == "__main__":
    main()
