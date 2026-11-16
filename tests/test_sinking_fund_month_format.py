"""Sheet 3 month cells survive a save and reload (change add-sinking-fund, found in the browser check of task 6.3):
the template's I:T carry the month format 'mmm', so a warranty that ends mid-year (a Schedule line) must write its
amounts with a number format, or they come back as dates / #VALUE!. TEST DATA: invented project figures."""
import datetime

import openpyxl

import budget_period
import generate_project_budget as gpb


def test_mid_year_warranty_months_stay_numbers(tmp_path):
    wb = openpyxl.load_workbook(gpb.TEMPLATE_PATH)
    project = dict(total_nfa=40_000, total_lifts=6, warranty_months=6, budget_period=budget_period.default())
    results = gpb.fill_sinking_fund_sheet(wb, project)
    schedule = [c for c, r in results.items() if r.status == 'priced' and not r.even]
    assert schedule, 'a 6-month warranty must give Schedule lines'
    path = tmp_path / 'deliverable.xlsx'
    wb.save(path)
    wb.close()
    ws = openpyxl.load_workbook(path)[gpb.SF_SHEET]
    rows = gpb.sf_leaf_rows(ws)
    for code in schedule:
        r = rows[code]
        cells = [ws.cell(row=r, column=gpb.SF_MONTH_FIRST_COL + k) for k in range(12)]
        assert all(isinstance(c.value, (int, float)) and not isinstance(c.value, datetime.datetime)
                   for c in cells), (code, [c.value for c in cells])
        assert [c.value for c in cells] == results[code].months
        assert ws.cell(row=r, column=gpb.SF_FREQ_COL).value == 'Schedule'
