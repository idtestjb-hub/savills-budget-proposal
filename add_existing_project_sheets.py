"""Add the Existing-project fields to an input workbook that is already filled in.

Change carry-forward-staffing, task 2.2. build_project_input_form.py refuses to overwrite a filled
Project_Budget_Input.xlsx (that refusal protects live input). A project that was filled before the
change still needs the new fields, so this script writes them into a DATED COPY beside the file and
never touches the original:

    python add_existing_project_sheets.py                       # the live reports/ input
    python add_existing_project_sheets.py path/to/input.xlsx    # any other input workbook

The copy is <name>_EXISTING_<yyyymmdd_HHMM>.xlsx. It gets the three Project Info fields (appended
below the last used row), the 'Prior-Year Roster' sheet and the two reason columns on Staffing
Demand, and the 'Prior-Year Utilities' sheet (change carry-forward-common-utilities), with exactly the
labels a fresh form carries. A form that already has the staffing sheet gets only the utilities
sheet. Review the copy, then replace the original with it yourself when you are ready.
"""
import datetime
import hashlib
import os
import sys

import openpyxl

import build_project_input_form as bpf
import existing_staffing as es
import existing_utilities as eu


def _sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def add_to_copy(src, now=None):
    """Write the dated copy and return its path. The original's bytes are checked unchanged."""
    if not os.path.exists(src):
        raise FileNotFoundError(src)
    folder, name = os.path.split(os.path.abspath(src))
    lock = os.path.join(folder, '~$' + name)
    if os.path.exists(lock):
        raise RuntimeError(f'{name} is open in Excel ({lock} exists). Close it, then run this again.')
    stamp = (now or datetime.datetime.now()).strftime('%Y%m%d_%H%M')
    stem, ext = os.path.splitext(name)
    dst = os.path.join(folder, f'{stem}_EXISTING_{stamp}{ext}')
    if os.path.exists(dst):
        raise FileExistsError(f'{dst} already exists; nothing was written.')
    before = _sha256(src)

    wb = openpyxl.load_workbook(src)
    has_roster, has_utilities = es.ROSTER_SHEET in wb.sheetnames, eu.SHEET in wb.sheetnames
    if has_roster and has_utilities:
        raise RuntimeError(f"{name} already has the '{es.ROSTER_SHEET}' and '{eu.SHEET}' sheets; nothing to add.")
    if not has_roster:
        pi = wb['Project Info']
        last = max((r for r in range(1, (pi.max_row or 1) + 1)
                    if pi.cell(row=r, column=1).value not in (None, '')), default=1)
        bpf.add_existing_project_fields(pi, last + 2)
        bpf.add_prior_year_roster_sheet(wb)
        sd = wb['Staffing Demand']
        last_demand = max(5, max((r for r in range(5, (sd.max_row or 5) + 1)
                                  if sd.cell(row=r, column=1).value not in (None, '')), default=5))
        bpf.add_demand_reason_columns(sd, 5, max(last_demand, 4 + 20))
    if not has_utilities:
        # Change carry-forward-common-utilities: a form that already carries the staffing sheet gets
        # only the utilities sheet.
        bpf.add_prior_year_utilities_sheet(wb)
    wb.save(dst)

    # The copy is written into the synced library: same OneDrive clean-up as every generator.
    from generate_project_output import _strip_onedrive_zip_artifacts
    _strip_onedrive_zip_artifacts(dst)
    if _sha256(src) != before:
        raise RuntimeError(f'{name} changed while the copy was written. Restore it from version history.')
    return dst


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(bpf.OUT_DIR, 'Project_Budget_Input.xlsx')
    try:
        out = add_to_copy(target)
    except (FileNotFoundError, FileExistsError, RuntimeError) as exc:
        print('STOPPED:', exc)
        sys.exit(1)
    print('Original left unchanged:', target)
    print('Copy with the Existing-project fields:', out)
