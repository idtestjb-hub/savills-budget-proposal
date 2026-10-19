"""Savills' own management fee, EMH1 (change apply-head-of-pm-decisions-2026-10, group 7, design D9c).

Two bases, read from Project Info by label, never by cell address:
- FIXED_LABEL, a monthly fee the PM enters excluding VAT (Head of PM decision B1-a): x 12, spread evenly, with
  each budget month's VAT added (none when the financial model is KHOÁN);
- PCT_LABEL, a % of the full annual management fee (residents plus the developer's top-up for units not yet
  handed over, at 100% occupancy), spread evenly. No VAT is added: the fee it is a share of already includes it.
Both filled stops the run; both blank leaves EMH1 at 0 with ZERO_REASON_VI.

Every text here names the inputs by label. The figures are worked out by the callers (the fund sheet writer
passes the VAT factors and the full fee), so this module holds only the wording and the arithmetic per month.
"""

FIXED_LABEL = 'Fixed Monthly Fee'
PCT_LABEL = '% of Collected Management Fee'
NOT_ENTERED_VI = 'chưa nhập'

FIXED, PERCENT = 'fixed', 'percent'


def _field_vi(label):
    return f"ô '{label}' trên Project Info"


def basis(project):
    """FIXED, PERCENT or None (neither entered). read_input has already stopped a run with both."""
    if project.get('savills_fee_fixed_monthly'):
        return FIXED
    if project.get('savills_fee_pct'):
        return PERCENT
    return None


def both_filled_message():
    return (f"Project Info '{FIXED_LABEL}' and '{PCT_LABEL}' are BOTH filled in. Savills' management fee (EMH1) "
            f"takes one basis: clear whichever does not apply.")


# The reason EMH1 carries at 0; '2.2 Common area Fund' copies it.
ZERO_REASON_VI = (
    f"dự án này chưa có điều khoản hợp đồng phí quản lý của Savills: {_field_vi(FIXED_LABEL)} và "
    f"ô '{PCT_LABEL}' đều trống. Khi có hợp đồng, PM nhập một trong hai ô (phí cố định hàng tháng chưa gồm VAT, "
    f"hoặc tỷ lệ % trên phí quản lý) rồi chạy lại. Cho đến lúc đó, thặng dư/thâm hụt mà bản giao nộp này thể "
    f"hiện CHƯA bao gồm phí quản lý của chính Savills — không phải con số lợi nhuận thực tế.")


def fixed_line(fee_monthly, vat_factors, vat_text):
    """(twelve monthly amounts, remark) for a fixed fee entered excluding VAT. vat_factors are (1 + that month's
    VAT), 1.0 each under KHOÁN; vat_text says which VAT was added in which months, or that none was."""
    months = [fee_monthly * v for v in vat_factors]
    annual_excl = fee_monthly * 12
    remark = (f"= Phí cố định hàng tháng PM nhập tại {_field_vi(FIXED_LABEL)}: {fee_monthly:,.0f} VND/tháng "
              f"(chưa gồm VAT) x 12 = {annual_excl:,.0f} VND/năm chưa VAT, {vat_text} = {sum(months):,.0f} VND/năm.")
    return months, remark


def percent_line(pct, full_fee_annual):
    """(twelve monthly amounts, remark) for a % of the full annual management fee; no VAT added."""
    annual = full_fee_annual * pct
    remark = (f"= Tỷ lệ phí PM nhập tại {_field_vi(PCT_LABEL)}: {pct:.1%} x phí quản lý đầy đủ cả năm khi lấp "
              f"đầy 100% (phần cư dân đóng cộng phần chủ đầu tư đóng cho căn chưa bàn giao, dòng RM và RM.0A) "
              f"{full_fee_annual:,.0f} VND = {annual:,.0f} VND/năm. Không cộng thêm VAT: phí quản lý làm cơ sở đã "
              f"gồm VAT.")
    return [annual / 12] * 12, remark


def summary_clause_vi(project, annual):
    """The fee sentence of the '1. Summary' EMH narrative, naming the basis actually used."""
    b = basis(project)
    if b == FIXED:
        return (f"Phí quản lý cố định của Savills (phí tháng PM nhập, chưa gồm VAT, cộng VAT theo tháng) dự ước "
                f"{annual:,.0f} VND/năm")
    if b == PERCENT:
        return (f"Phí quản lý của Savills tính theo tỷ lệ {project['savills_fee_pct']:.1%} trên phí quản lý đầy đủ "
                f"cả năm, dự ước {annual:,.0f} VND/năm")
    return "Phí quản lý của Savills chưa dự ước — chờ điều khoản hợp đồng"


def analysis_rows(project, full_fee_annual_ref):
    """The rows the analysis's 'Savills Fee Position' shows beside the profit it computes (Head of PM decision
    B1-b): [(label, value, number format)]. full_fee_annual_ref is the analysis cell holding the full annual
    management fee at 100% occupancy, so a % fee stays a live formula. Display only: nothing sums these."""
    b = basis(project)
    if b == FIXED:
        fee = project['savills_fee_fixed_monthly']
        return [("Basis entered on Project Info", f"'{FIXED_LABEL}' (VND per month, excl. VAT)", None),
                ("Entered value", fee, 'money'),
                ("Entered fee per year, excl. VAT (VND) — the deliverable adds each month's VAT", fee * 12, 'money')]
    if b == PERCENT:
        pct = project['savills_fee_pct']
        return [("Basis entered on Project Info", f"'{PCT_LABEL}' (of the full management fee)", None),
                ("Entered value", pct, '0.0%'),
                ("Entered fee per year (VND) = % x Management Fee Revenue at 100% fill", f'={pct}*{full_fee_annual_ref}',
                 'money')]
    return [("Basis entered on Project Info", NOT_ENTERED_VI, None),
            ("Entered value", NOT_ENTERED_VI, None),
            ("Entered fee per year (VND)", NOT_ENTERED_VI, None)]
