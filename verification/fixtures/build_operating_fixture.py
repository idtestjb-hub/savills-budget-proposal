"""Build Sample_Operating_Input.xlsx: the standard sample, described as a project already in operation.

Change use-operating-project-actuals, task 7.1 (spec budget-workflow-verification, "Verification exercises
the operating-project path"). Every figure below is INVENTED; no real project's rate, parking revenue or
utility bill is in it. It starts from Sample_Project_Input.xlsx (left untouched) and adds the new labels
by hand, the way RUNNING.md tells a PM to add them to an existing form (design D7):

- 'Stable Operation?' = Yes (P3);
- an actual rate on two products: Apartment excl. VAT (so the VAT-basis note is exercised) and Nursery
  incl. VAT; Shophouse is left to its comparables (P1);
- recorded car and motorbike parking revenue (P2);
- collect-on-behalf amounts for two products, with one amount entered at 0 (P4).

The project gets its own name, so its outputs never share a temp file name with the standard sample.

Run from Budget_Agent/source_code:  python verification/fixtures/build_operating_fixture.py
"""
import os
import sys

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, SOURCE)

import operating_inputs as oi                      # noqa: E402
from input_labels import SheetLabels               # noqa: E402

SRC = os.path.join(HERE, 'Sample_Project_Input.xlsx')
OUT = os.path.join(HERE, 'Sample_Operating_Input.xlsx')
NAME = 'ZZ Operating Tower (TEST DATA - NOT A REAL PROJECT)'

# Invented figures (VND). Rates per m² per month; the others per month.
RATES = {'Apartment': (16_500, oi.VAT_EXCL), 'Nursery / Nhà trẻ': (12_000, oi.VAT_INCL)}
PARKING = {oi.PARKING_CAR_LABEL: 52_000_000, oi.PARKING_MOTO_LABEL: 61_000_000}
COB = {'Apartment': (310_000_000, 455_000_000), 'Shophouse': (0, 27_500_000)}     # (water, electricity)


def build(out=OUT):
    lock = os.path.join(os.path.dirname(out), '~$' + os.path.basename(out))
    if os.path.exists(lock):
        raise RuntimeError(f'{os.path.basename(out)} is open in Excel ({lock} exists). Close it first.')
    wb = openpyxl.load_workbook(SRC)
    pi = wb['Project Info']
    L = SheetLabels(pi)
    pi.cell(row=L.row_of('Project Name'), column=2, value=NAME)

    # P1: the two rate columns beside the Product Mix header, found again by header when read.
    header = L.row_of(oi.PRODUCT_HEADER)
    rate_col = max(5, (pi.max_column or 4) + 1)    # past any used column; the reader finds it by header
    pi.cell(row=header, column=rate_col, value=oi.RATE_HEADER)
    pi.cell(row=header, column=rate_col + 1, value=oi.VAT_HEADER)
    for product, (rate, vat) in RATES.items():
        row = L.row_of(product)
        pi.cell(row=row, column=rate_col, value=rate)
        pi.cell(row=row, column=rate_col + 1, value=vat)

    # P3, P2 and P4, appended below the last used row.
    r = max(row for row in range(1, (pi.max_row or 1) + 1) if pi.cell(row=row, column=1).value) + 2
    pi.cell(row=r, column=1, value=oi.SECTION_TITLE)
    pi.cell(row=r + 1, column=1, value=oi.STABLE_LABEL)
    pi.cell(row=r + 1, column=2, value='Yes')
    for i, (label, value) in enumerate(PARKING.items(), start=2):
        pi.cell(row=r + i, column=1, value=label)
        pi.cell(row=r + i, column=2, value=value)
    top = r + 5
    pi.cell(row=top, column=1, value=oi.COB_SECTION)
    for c, h in enumerate((oi.COB_HEADER, oi.COB_WATER_HEADER, oi.COB_ELEC_HEADER), start=1):
        pi.cell(row=top + 1, column=c, value=h)
    for i, (product, (water, elec)) in enumerate(COB.items(), start=top + 2):
        pi.cell(row=i, column=1, value=oi.COB_ROW_PREFIX + product)
        pi.cell(row=i, column=2, value=water)
        pi.cell(row=i, column=3, value=elec)
    wb.save(out)
    from generate_project_output import _strip_onedrive_zip_artifacts
    _strip_onedrive_zip_artifacts(out)
    return out


if __name__ == '__main__':
    print('Wrote', build())
