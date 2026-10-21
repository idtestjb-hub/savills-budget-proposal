"""ESI1 risk asset insurance from the insured asset value (change price-asset-insurance-from-asset-value, rules decided
2026-10-19).

Rule source: openspec/changes/price-asset-insurance-from-asset-value/specs/asset-insurance-pricing/spec.md. Invented
values only, except the worked example the spec quotes (a value and a discounted rate, no project named).
"""
import re

import openpyxl
import pytest

import build_project_input_form as bpf
import generate_project_budget as g


class Recorder:
    """Stands in for fill_management_fund_sheet()'s write_vat_monthly: records what ESI1 asked it to write."""
    def __init__(self):
        self.calls = []

    def __call__(self, key, annual_excl, remark, kind=None):
        self.calls.append(dict(key=key, annual_excl=annual_excl, remark=remark, kind=kind))
        return annual_excl


def write(value=None, rate=None):
    ws = openpyxl.Workbook().active
    rec = Recorder()
    g._write_asset_insurance(ws, {'esi1': g._resolve_esi1(value, rate)}, rec)
    return ws.cell(row=g.MGMT_FUND_ROWS['asset_insurance'], column=g._REMARKS_COL).value, rec.calls


# ---------------------------------------------------------------- inputs
def test_blank_fields():
    assert g._resolve_esi1(None, None) == dict(value=None, rate=0.0005, rate_is_default=True)


def test_entered_rate_is_used():
    assert g._resolve_esi1(1e10, 0.000375) == dict(value=1e10, rate=0.000375, rate_is_default=False)


@pytest.mark.parametrize('value, rate, field', [
    (-1, None, g.ESI1_VALUE_LABEL), ('abc', None, g.ESI1_VALUE_LABEL),
    (1e10, 0, g.ESI1_RATE_LABEL), (1e10, -0.0005, g.ESI1_RATE_LABEL), (1e10, 0.05, g.ESI1_RATE_LABEL)])
def test_bad_values_stop_the_run(value, rate, field):
    with pytest.raises(ValueError, match=re.escape(field)):
        g._resolve_esi1(value, rate)


# ---------------------------------------------------------------- pricing
def test_default_rate():
    _, calls = write(10_000_000_000)
    assert len(calls) == 1 and calls[0]['key'] == 'asset_insurance' and calls[0]['annual_excl'] == 5_000_000
    assert calls[0]['kind'] == g.utility_tariffs.VAT_INSURANCE
    assert '0,05%/năm' in calls[0]['remark'] and 'mặc định' in calls[0]['remark']


def test_discounted_rate():
    _, calls = write(6_707_011_785_586, 0.000375)
    assert calls[0]['annual_excl'] == 2_515_129_420
    assert '0,0375%/năm' in calls[0]['remark'] and 'do PM nhập' in calls[0]['remark']


def test_blank_value_stays_zero_and_names_the_field():
    remark, calls = write(None)
    assert not calls and g.ESI1_VALUE_LABEL in remark and g._ZERO_REASONS['ESI1']


def test_zero_value_says_the_pm_entered_zero():
    remark, calls = write(0)
    assert not calls and 'bằng 0' in remark


# ---------------------------------------------------------------- the form
@pytest.fixture
def built_form(tmp_path, monkeypatch):
    reports = tmp_path / 'reports'
    reports.mkdir()
    monkeypatch.setattr(bpf, 'OUT_DIR', str(reports))
    monkeypatch.setattr(bpf, 'FINAL_OUT', str(reports / 'Project_Budget_Input.xlsx'))
    monkeypatch.setattr(bpf, 'OUT', str(tmp_path / 'scratch.xlsx'))
    bpf.main()
    return str(reports / 'Project_Budget_Input.xlsx')


def test_builder_writes_both_fields_and_the_reader_reads_them(built_form):
    wb = openpyxl.load_workbook(built_form)
    pi = wb['Project Info']
    rows = {pi.cell(row=r, column=1).value: r for r in range(1, pi.max_row + 1)}
    value_row, rate_row = rows[g.ESI1_VALUE_LABEL], rows[g.ESI1_RATE_LABEL]
    assert rate_row == value_row + 1 and value_row > rows['Thu hộ chi hộ: Nursery / Nhà trẻ']   # below every section
    pi.cell(row=value_row, column=2).value, pi.cell(row=rate_row, column=2).value = 20_000_000_000, 0.0004
    wb.save(built_form)
    proj = g.read_input(built_form)[0]
    assert proj['esi1'] == dict(value=20_000_000_000, rate=0.0004, rate_is_default=False)
