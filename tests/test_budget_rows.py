"""budget_rows.py: aggregate rows by formula and tie explanation (change read-aggregate-rows-by-formula).
Grids are invented; rows and columns are 0-based as in the readers, formulas use Excel's 1-based addresses."""
from openpyxl.worksheet.formula import ArrayFormula

import budget_rows as br

AK = 36                     # column AK, 0-based


def test_formula_text_reads_plain_and_array_formulas():
    assert br.formula_text('=SUBTOTAL(9,AK48:AK55)') == '=SUBTOTAL(9,AK48:AK55)'
    assert br.formula_text(ArrayFormula('AK47', '=SUM(AK48:AK50)')) == '=SUM(AK48:AK50)'
    assert br.formula_text(120.0) is None
    assert br.formula_text('Revenue') is None


def test_subtotal_and_sum_ranges_give_0_based_rows():
    assert br.aggregate_refs('=SUBTOTAL(9,AK48:AK50)', AK) == ('SUBTOTAL', [47, 48, 49])
    assert br.aggregate_refs('=subtotal(109, $AK$48:$AK$49)', AK) == ('SUBTOTAL', [47, 48])
    assert br.aggregate_refs('=SUM(AK37:AK38)', AK) == ('SUM', [36, 37])
    assert br.aggregate_refs('=SUM(AK40)', AK) == ('SUM', [39])
    assert br.aggregate_refs('=SUM(AK37,AK39:AK40)', AK) == ('SUM', [36, 38, 39])


def test_formulas_that_are_not_aggregates():
    assert br.aggregate_refs('=AK40*12', AK) is None
    assert br.aggregate_refs('=SUBTOTAL(1,AK48:AK55)', AK) is None            # an average, not a sum
    assert br.aggregate_refs('=SUM(AL48:AL55)', AK) is None                    # another column
    assert br.aggregate_refs("=SUM('Other'!AK48:AK55)", AK) is None            # another sheet
    assert br.aggregate_refs('=SUM(AK48:AK55)*1.1', AK) is None                # not one call
    assert br.aggregate_refs('=AK48+AK49', AK) is None                         # a +-chain: out of scope (design D2)


def _grid(cells):
    """{(row, col): value} -> get(r, c)."""
    return lambda r, c: cells.get((r, c))


def test_subtotal_spanning_a_sibling_code():
    # RO4 (row 46, Excel 47) = SUBTOTAL over Excel rows 48..55: RO4.A .. RO4.L and RO5
    codes = {46: 'RO4', 47: 'RO4.A', 48: 'RO4.T', 49: 'RO4.O', 50: 'RO4.M', 51: 'RO4.R', 52: 'RO4.S', 53: 'RO4.L',
             54: 'RO5'}
    f = _grid({(46, AK): '=SUBTOTAL(9,AK48:AK55)'})
    aggs = br.find_aggregates(f, candidates=codes, coded_rows=codes, col=AK)
    assert list(aggs) == [46]
    assert aggs[46]['kind'] == 'SUBTOTAL'
    assert aggs[46]['children'] == [47, 48, 49, 50, 51, 52, 53, 54]


def test_a_range_over_no_other_coded_row_is_not_an_aggregate():
    codes = {10: 'EMA1'}
    f = _grid({(10, AK): '=SUM(AK3:AK5)'})                                     # sums cells of non-coded rows
    assert br.find_aggregates(f, candidates=codes, coded_rows=codes, col=AK) == {}
    f = _grid({(10, AK): '=SUM(AK11)'})                                        # its own row only
    assert br.find_aggregates(f, candidates=codes, coded_rows=codes, col=AK) == {}


def _leaves(*rows_codes):
    return [{'row': r, 'code': c, 'section': s} for r, c, s in rows_codes]


def test_dropped_rows_formula_first_then_prefix_fallback():
    leaves = _leaves((46, 'RO4', 'R'), (47, 'RO4.A', 'R'), (54, 'RO5', 'R'),
                     (60, 'ERM', 'E'), (61, 'ERM.1', 'E'), (62, 'ERM.2', 'E'))
    kids = br.prefix_kids([lf['code'] for lf in leaves])
    # RO4 caches 0 (a filter hid its children): still dropped, by its formula
    vals = [0.0, 100.0, 50.0, 120.0, 70.0, 50.0]
    gone = br.dropped(vals, leaves, kids, aggregates={46: {'kind': 'SUBTOTAL', 'children': [47, 54]}})
    assert gone == {0, 3}                      # RO4 by formula, typed-in ERM because ERM.1 + ERM.2 = ERM


def test_prefix_fallback_keeps_a_parent_its_children_do_not_add_up_to():
    leaves = _leaves((60, 'ERM', 'E'), (61, 'ERM.1', 'E'))
    kids = br.prefix_kids(['ERM', 'ERM.1'])
    assert br.dropped([120.0, 70.0], leaves, kids, aggregates={}) == set()


def test_prefix_kids_rules_match_the_store():
    kids = br.prefix_kids(['RO2', 'RO2a', 'RO2b', 'RO21', 'EM1', 'EM12', 'ES1', 'ES1.A'])
    assert kids[0] == [1, 2]                   # RO2 -> RO2a, RO2b; RO21 is a sibling (digit after a code with a digit)
    assert kids[4] == []                       # EM1 -> not EM12
    assert kids[6] == [7]


SECTIONS = ('R', 'E')


def test_direct_tie():
    t = br.explain_tie(SECTIONS, items=[(13, 'R', 100.0), (20, 'E', 40.0)], doubles=[],
                       anchors={'R': 100.0, 'E': 40.0}, hidden=set(), filter_on=False)
    assert t['state'] == 'ok' and t['notes'] == [] and t['diffs'] == {'R': 0.0, 'E': 0.0}


def test_tie_after_a_double_count_by_a_sum_parent():
    # RO2 = SUM(...) = 1,820,000: SUBTOTAL in the R row counts it on top of its children
    items = [(36, 'R', 1_000_000.0), (37, 'R', 820_000.0), (40, 'R', 5_000_000.0), (60, 'E', 9.0)]
    t = br.explain_tie(SECTIONS, items=items, doubles=[(35, 'R', 'RO2', 1_820_000.0, 'SUM')],
                       anchors={'R': 8_640_000.0, 'E': 9.0}, hidden=set(), filter_on=False)
    assert t['state'] == 'ok_double_count'
    assert t['notes'] == ['lỗi file: RO2 dùng SUM, tổng của file cộng trùng 1,820,000 VND']
    assert t['diffs']['R'] == -1_820_000.0


def test_tie_after_a_filter():
    items = [(13, 'R', 100.0), (14, 'R', 200.0), (20, 'E', 40.0), (21, 'E', 60.0)]
    t = br.explain_tie(SECTIONS, items=items, doubles=[], anchors={'R': 0.0, 'E': 60.0},
                       hidden={13, 14, 20}, filter_on=True, n_hidden=699)
    assert t['state'] == 'ok_filter'
    assert t['notes'] == ['ô tổng bị bộ lọc che (699 dòng ẩn)']


def test_filter_and_sum_error_together_give_both_notes():
    items = [(13, 'R', 100.0), (14, 'R', 200.0), (31, 'R', 5.0), (32, 'R', 5.0), (20, 'E', 40.0)]
    t = br.explain_tie(SECTIONS, items=items, doubles=[(30, 'R', 'RO2', 10.0, 'SUM')], anchors={'R': 20.0, 'E': 40.0},
                       hidden={13, 14}, filter_on=True, n_hidden=2)
    assert t['state'] == 'ok_filter'
    assert t['notes'] == ['ô tổng bị bộ lọc che (2 dòng ẩn)', 'lỗi file: RO2 dùng SUM, tổng của file cộng trùng 10 VND']


def test_hidden_rows_without_a_filter_do_not_explain_a_gap():
    items = [(13, 'R', 100.0), (14, 'R', 200.0), (20, 'E', 40.0)]
    t = br.explain_tie(SECTIONS, items=items, doubles=[], anchors={'R': 100.0, 'E': 40.0},
                       hidden={14}, filter_on=False, n_hidden=1)
    assert t['state'] == 'mismatch'
    assert t['diffs']['R'] == 200.0


def test_a_gap_nothing_explains():
    t = br.explain_tie(SECTIONS, items=[(13, 'R', 100.0), (20, 'E', 45.0)], doubles=[(30, 'R', 'RO2', 7.0, 'SUM')],
                       anchors={'R': 100.0, 'E': 40.0}, hidden=set(), filter_on=True, n_hidden=0)
    assert t['state'] == 'mismatch'
    assert t['diffs'] == {'R': 0.0, 'E': 5.0}
    assert t['notes'] == ['E lệch 5 VND']


def test_missing_anchor():
    t = br.explain_tie(SECTIONS, items=[(13, 'R', 100.0)], doubles=[], anchors={'R': 100.0, 'E': None},
                       hidden=set(), filter_on=False)
    assert t['state'] == 'no_anchor'


def test_filter_on_rule():
    assert br.filter_on(auto_filter_ref='A10:BA700', n_hidden=0, n_rows=600)
    assert br.filter_on(auto_filter_ref=None, n_hidden=400, n_rows=600)
    assert not br.filter_on(auto_filter_ref=None, n_hidden=3, n_rows=600)


def test_sheet_layout_reads_hidden_rows_and_the_filter(tmp_path):
    import openpyxl
    p = str(tmp_path / 'layout.xlsx')
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Budget & Fund'
    for r in range(1, 6):
        ws.cell(row=r, column=1, value=r)
    ws.row_dimensions[2].hidden = True
    ws.row_dimensions[4].hidden = True
    ws.auto_filter.ref = 'A1:A5'
    other = wb.create_sheet('Plain')
    other['A1'] = 1
    wb.save(p)
    lay = br.sheet_layout(p, {'Budget & Fund', 'Plain'})
    assert lay['Budget & Fund'] == ({1, 3}, 'A1:A5')
    assert lay['Plain'] == (set(), None)


def test_a_parent_carrying_its_childs_figure_is_double_counted_by_the_file():
    # RO2 and RO2a both hold 1,820,000 (each sums its own months); the prefix rule drops RO2, the file's SUBTOTAL
    # counts both
    leaves = _leaves((33, 'RO2', 'R'), (34, 'RO2a', 'R'), (35, 'RO2b', 'R'), (40, 'RO11', 'R'))
    vals = [1_820_000.0, 1_820_000.0, 0.0, 39_900_000.0]
    kids = br.prefix_kids([lf['code'] for lf in leaves])
    gone = br.dropped(vals, leaves, kids, aggregates={})
    assert gone == {0}
    f = _grid({(33, AK): '=SUM(AO34:AZ34)'})
    doubles = br.double_counted(leaves, vals, gone, {}, f, AK)
    assert doubles == [(33, 'R', 'RO2', 1_820_000.0, 'parent')]
    items = [(lf['row'], lf['section'], vals[i]) for i, lf in enumerate(leaves) if i not in gone]
    t = br.explain_tie(('R',), items=items, doubles=doubles, anchors={'R': 43_540_000.0}, hidden=set(),
                       filter_on=False)
    assert t['state'] == 'ok_double_count'
    assert t['notes'] == ['lỗi file: RO2 trùng số với dòng con, tổng của file cộng trùng 1,820,000 VND']


def test_double_counted_skips_subtotal_cells():
    leaves = _leaves((46, 'RO4', 'R'), (47, 'RO4.A', 'R'), (60, 'RO7', 'R'), (61, 'RO7.A', 'R'))
    vals = [100.0, 100.0, 5.0, 5.0]
    aggs = {46: {'kind': 'SUBTOTAL', 'children': [47]}}
    f = _grid({(60, AK): '=SUBTOTAL(9,AK62:AK62)'})          # not an aggregate (no coded row 62) but a SUBTOTAL
    gone = br.dropped(vals, leaves, br.prefix_kids([lf['code'] for lf in leaves]), aggs)
    assert gone == {0, 2}
    assert br.double_counted(leaves, vals, gone, aggs, f, AK) == []
