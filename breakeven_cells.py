"""The parking break-even cells BK507 and BK511 on '2. Budget-Management Fund' (change
apply-head-of-pm-decisions-2026-10, group 7, Head of PM decision B10, design D9c).

The template's BK<break-even> is `=-BK<deficit>/BK<parking area>`, so it shows #DIV/0! whenever the project has
no parking area, and BK<change needed> = BK<break-even> + BK<current price> inherits the error. Nothing else
reads either cell. The writer keeps the template's own expression and guards it:
  BK<break-even>    = IF(N(BK<area>)=0,"N/A",<template expression>)
  BK<change needed> = IF(ISNUMBER(BK<break-even>),<template expression>,"N/A")
Both stay live formulas, so a parking area typed in later gives a number. The rows are found by their column-BG
labels; a label that is missing or appears twice, or a template expression of another shape, stops the run.
Only column BK is guarded (BJ, the apartment side, divides by the apartment area, which a priced run always has).
"""
import re

SHEET = '2. Budget-Management Fund'
BREAK_EVEN_LABEL = 'Gía dịch vụ quản lý cân bằng'        # the template's own spelling
CHANGE_LABEL = 'Gía dịch vụ quản lý cần tăng / giảm'
LABEL_COL = 59     # BG
BK_COL = 63        # BK
NOT_APPLICABLE = 'N/A'

_BREAK_EVEN = re.compile(r'^=-BK(\d+)/BK(\d+)$')
_CHANGE = re.compile(r'^=BK(\d+)\+BK(\d+)$')


def _norm(text):
    return ' '.join(str(text).split()).casefold()


def _find_row(ws, label):
    rows = [r for r in range(1, ws.max_row + 1)
            if isinstance(ws.cell(row=r, column=LABEL_COL).value, str)
            and _norm(ws.cell(row=r, column=LABEL_COL).value) == _norm(label)]
    if len(rows) != 1:
        raise ValueError(f"'{SHEET}' column BG should carry the label {label!r} exactly once, found it "
                         f"{len(rows)} time(s). The template changed: re-check the break-even cells (decision B10).")
    return rows[0]


def guard(ws):
    """Rewrite BK<break-even> and BK<change needed> as guarded formulas. Returns {cell: formula} written."""
    be_row, ch_row = _find_row(ws, BREAK_EVEN_LABEL), _find_row(ws, CHANGE_LABEL)
    be_cell, ch_cell = ws.cell(row=be_row, column=BK_COL), ws.cell(row=ch_row, column=BK_COL)
    be_raw = str(be_cell.value or '').replace(' ', '')
    ch_raw = str(ch_cell.value or '').replace(' ', '')
    m_be, m_ch = _BREAK_EVEN.match(be_raw), _CHANGE.match(ch_raw)
    if not m_be or not m_ch or int(m_ch.group(1)) != be_row:
        raise ValueError(f"'{SHEET}' BK{be_row} / BK{ch_row} are {be_cell.value!r} / {ch_cell.value!r}, not the "
                         f"template's =-BK<deficit>/BK<parking area> and =BK{be_row}+BK<current price>. The template "
                         f"changed: re-check the break-even cells (decision B10).")
    area_ref = f'BK{m_be.group(2)}'
    be_cell.value = f'=IF(N({area_ref})=0,"{NOT_APPLICABLE}",{be_raw[1:]})'
    ch_cell.value = f'=IF(ISNUMBER(BK{be_row}),{ch_raw[1:]},"{NOT_APPLICABLE}")'
    return {be_cell.coordinate: be_cell.value, ch_cell.coordinate: ch_cell.value}
