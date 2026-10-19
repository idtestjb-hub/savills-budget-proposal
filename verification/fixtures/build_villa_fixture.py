"""Build Sample_Villa_Input.xlsx: the standard sample, described as a low-rise villa project with no parking bays.

Change support-villa-only-and-no-parking, task 1.2. Every figure below is INVENTED; no real project's area or unit count
is in it. It starts from Sample_Project_Input.xlsx (left untouched):

- the Product Mix holds only a Villas row (no Apartment NFA);
- 0 car and 0 motorbike parking bays;
- no towers, 3 floors.

The project gets its own name, so its outputs never share a temp file name with the standard sample.

Run from Budget_Agent/source_code:  python verification/fixtures/build_villa_fixture.py
"""
import os
import sys

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, SOURCE)

from generate_project_budget import PRODUCT_ROWS   # noqa: E402
from input_labels import SheetLabels               # noqa: E402

SRC = os.path.join(HERE, 'Sample_Project_Input.xlsx')
OUT = os.path.join(HERE, 'Sample_Villa_Input.xlsx')
NAME = 'ZZ Villa Garden (TEST DATA - NOT A REAL PROJECT)'

VILLAS = (52_000, 38_000, 240)                     # GFA m², NFA m², units
FACTS = {'Car Parking Slots': 0, 'Moto Parking Slots': 0, 'Tower Count': 0, 'Floor Count': 3}


def build(out=OUT):
    lock = os.path.join(os.path.dirname(out), '~$' + os.path.basename(out))
    if os.path.exists(lock):
        raise RuntimeError(f'{os.path.basename(out)} is open in Excel ({lock} exists). Close it first.')
    wb = openpyxl.load_workbook(SRC)
    pi = wb['Project Info']
    L = SheetLabels(pi)
    pi.cell(row=L.row_of('Project Name'), column=2, value=NAME)
    for product in PRODUCT_ROWS:
        if not L.has(product):
            continue
        row = L.row_of(product)
        for col, value in zip((2, 3, 4), VILLAS if product == 'Villas' else (0, 0, 0)):
            pi.cell(row=row, column=col, value=value)
    for label, value in FACTS.items():
        pi.cell(row=L.row_of(label), column=2, value=value)
    wb.save(out)
    from generate_project_output import _strip_onedrive_zip_artifacts
    _strip_onedrive_zip_artifacts(out)
    return out


if __name__ == '__main__':
    print('Wrote', build())
