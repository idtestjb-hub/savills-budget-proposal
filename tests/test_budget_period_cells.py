"""The budget period reaches every cell that shows it, sheet 3's budget year included: a Review whose budget year is
not the template's (prior 2025 -> budget 2026) used to show the template's 2027 in sheet 3's title and headers."""
import datetime
import os

import openpyxl
import pytest

import budget_period as bp
import generate_project_budget as g

pytestmark = pytest.mark.skipif(not os.path.exists(g.TEMPLATE_PATH), reason='standard form not available')


@pytest.mark.parametrize('start_year, start_month', [(2026, 1), (2025, 8), (2027, 1)])
def test_period_written_to_sheet_2_summary_and_sheet_3(start_year, start_month):
    wb = openpyxl.load_workbook(g.TEMPLATE_PATH)
    period = bp.BudgetPeriod(start_year, start_month)
    g._write_budget_period(wb, period)
    fund, sf = wb['2. Budget-Management Fund'], wb[g.SF_SHEET]
    assert fund['AL5'].value == period.budget_year
    assert sf['AG4'].value == period.budget_year
    first = datetime.datetime.combine(period.first_day, datetime.time())
    assert fund['AH6'].value == first and wb['1. Summary']['H4'].value == first
    # Sheet 3's period cells stay formulas on sheet 2, so its month columns follow the same period.
    assert sf['AC5'].value == "='2. Budget-Management Fund'!AH6"
    assert sf['AG5'].value == "='2. Budget-Management Fund'!AL6"


def test_workbook_without_sheet_3_is_left_alone():
    wb = openpyxl.load_workbook(g.TEMPLATE_PATH)
    del wb[g.SF_SHEET]
    g._write_budget_period(wb, bp.BudgetPeriod(2026, 1))
    assert wb['2. Budget-Management Fund']['AL5'].value == 2026
