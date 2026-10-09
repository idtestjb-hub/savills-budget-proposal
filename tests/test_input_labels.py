"""Unit tests for input_labels.py (finding intake-form fields by their column-A label).

Covered: normalise, SheetLabels (has / row_of / value / section_row / rows_under) and the two
errors LabelNotFound and AmbiguousLabel.
Not covered: reading real workbooks (a tiny stub sheet stands in; no Excel files are opened).

Invented data only.

Rule sources: the module docstring and docstrings (labels cut at the first '(' or dash-run, a
missing label is fatal and names itself, a duplicate key is fatal, an empty value cell is an empty
field not a missing one - docs/05-decisions.md D1). The 200-row scan limit and the blank-run rule
in rows_under are stated in code only.
"""
import pytest

from input_labels import AmbiguousLabel, LabelNotFound, SheetLabels, normalise


class StubSheet:
    """Just enough of an openpyxl worksheet: .title, .max_row and .cell(row=, column=).value."""

    class _Cell:
        def __init__(self, value):
            self.value = value

    def __init__(self, cells, title='Stub', max_row=None):
        self.title = title
        self._cells = cells                      # {(row, col): value}
        self.max_row = max_row if max_row is not None else max((r for r, _ in cells), default=0)

    def cell(self, row, column):
        return self._Cell(self._cells.get((row, column)))


def sheet_from(col_a, col_b=None, **kw):
    """col_a: {row: label}; col_b: {row: value}."""
    cells = {(r, 1): v for r, v in col_a.items()}
    cells.update({(r, 2): v for r, v in (col_b or {}).items()})
    return StubSheet(cells, **kw)


# ---------------------------------------------------------------- normalise

@pytest.mark.parametrize('raw, key', [
    ('Pool Area (m²) — optional', 'pool area'),
    ('Pool Area', 'pool area'),
    ('POOL AREA:', 'pool area'),
    ('  Car   Parking\tSlots  ', 'car parking slots'),
    ('Pool Area – optional', 'pool area'),                     # en dash
    ('Pool Area -- optional', 'pool area'),                    # double hyphen
    ('Pool Area — optional (m²)', 'pool area'),
    ('% of Collected Management Fee — leave blank if not %-based', '% of collected management fee'),
    ('Check-in Time', 'check-in time'),                        # a single hyphen is not a cut point
    ('Số tầng (tầng)', 'số tầng'),
    ('(only a hint)', ''),
    ('— lone dash', ''),
    ('', ''),
    ('   ', ''),
    (None, ''),
    (123, '123'),
])
def test_normalise(raw, key):
    assert normalise(raw) == key


def test_normalise_keeps_similar_labels_apart():
    assert normalise('Car Parking Slots') != normalise('Moto Parking Slots')


# ---------------------------------------------------------------- SheetLabels basics

def test_row_of_finds_by_label_ignoring_hints_and_case():
    labels = SheetLabels(sheet_from({3: 'Pool Area (m²) — optional', 4: 'Gate Count'}))
    assert labels.row_of('pool area') == 3
    assert labels.row_of('Pool Area (m2)') == 3
    assert labels.row_of('GATE COUNT') == 4
    assert labels.has('Gate Count') and not labels.has('Garden Area')


def test_value_reads_the_cell_beside_the_label():
    labels = SheetLabels(sheet_from({3: 'Gate Count', 4: 'Tower Count'}, {3: 6, 4: 2}))
    assert labels.value('Gate Count') == 6
    assert labels.value('Tower Count') == 2


def test_value_can_read_another_column():
    cells = {(3, 1): 'Gate Count', (3, 2): 6, (3, 4): 'note'}
    labels = SheetLabels(StubSheet(cells), value_col=2)
    assert labels.value('Gate Count', col=4) == 'note'


def test_value_of_present_label_with_empty_cell_is_none_not_an_error():
    # rule source: docs/05-decisions.md D1 (blank Savills-fee cells must keep reading as blank)
    labels = SheetLabels(sheet_from({3: 'Savills Fee'}))
    assert labels.value('Savills Fee') is None


def test_section_row_is_the_row_of_the_header():
    labels = SheetLabels(sheet_from({10: 'PRODUCT MIX', 11: 'Apartment'}))
    assert labels.section_row('Product Mix') == 10


def test_blank_and_hint_only_labels_are_skipped_not_indexed():
    labels = SheetLabels(sheet_from({1: None, 2: '   ', 3: '(hint only)', 4: 'Gate Count'}))
    assert labels.row_of('Gate Count') == 4
    assert not labels.has('')


# ---------------------------------------------------------------- failures

def test_missing_label_is_fatal_and_names_sheet_and_label():
    labels = SheetLabels(sheet_from({3: 'Pool Area', 4: 'Pool Depth'}, title='Project Info'))
    with pytest.raises(LabelNotFound) as err:
        labels.row_of('Pool Volume')
    msg = str(err.value)
    assert 'Project Info' in msg and 'Pool Volume' in msg
    assert 'Nothing was read from a fallback position' in msg


def test_missing_label_lists_nearest_labels_sharing_the_first_word():
    labels = SheetLabels(sheet_from({3: 'pool area', 4: 'pool depth', 5: 'gate count'}))
    with pytest.raises(LabelNotFound) as err:
        labels.row_of('Pool Volume')
    assert "'pool area'" in str(err.value) and "'pool depth'" in str(err.value)
    assert "'gate count'" not in str(err.value)


def test_value_of_missing_label_raises_instead_of_guessing():
    labels = SheetLabels(sheet_from({3: 'Gate Count'}, {3: 6}))
    with pytest.raises(LabelNotFound):
        labels.value('Tower Count')


def test_has_is_false_and_does_not_raise_for_missing_label():
    assert SheetLabels(sheet_from({3: 'Gate Count'})).has('Tower Count') is False


def test_two_labels_with_the_same_key_are_fatal_not_first_wins():
    # 'Pool Area' and 'Pool Area (m²)' both reduce to 'pool area'
    with pytest.raises(AmbiguousLabel) as err:
        SheetLabels(sheet_from({3: 'Pool Area', 9: 'Pool Area (m²)'}, title='Project Info'))
    msg = str(err.value)
    assert "'pool area'" in msg and 'row 3' in msg and 'row 9' in msg and 'Project Info' in msg


def test_errors_are_runtime_errors():
    assert issubclass(LabelNotFound, RuntimeError) and issubclass(AmbiguousLabel, RuntimeError)


# ---------------------------------------------------------------- scan limits

def test_labels_below_row_200_are_not_indexed_by_default():
    # rule source: code comment only (min(max_row, 200)). Not settled: a label past row 200 is not indexed, so
    # row_of raises LabelNotFound for it, and a duplicate past row 200 would go undetected.
    sheet = sheet_from({200: 'Last Seen', 201: 'Past The Limit'}, max_row=500)
    labels = SheetLabels(sheet)
    assert labels.has('Last Seen')
    assert not labels.has('Past The Limit')


def test_explicit_max_row_extends_the_scan():
    sheet = sheet_from({201: 'Past The Limit'}, max_row=500)
    assert SheetLabels(sheet, max_row=300).has('Past The Limit')


def test_scan_stops_at_the_sheets_own_max_row():
    sheet = sheet_from({3: 'Inside', 8: 'Beyond Max Row'}, max_row=5)
    labels = SheetLabels(sheet)
    assert labels.has('Inside') and not labels.has('Beyond Max Row')


def test_label_column_can_be_changed():
    cells = {(2, 3): 'Gate Count', (2, 4): 6}
    labels = SheetLabels(StubSheet(cells), label_col=3, value_col=4)
    assert labels.value('Gate Count') == 6


# ---------------------------------------------------------------- rows_under

def block(entries, header_row=5, **kw):
    """entries: {row: label}; header at header_row."""
    col_a = {header_row: 'PRODUCT MIX'}
    col_a.update(entries)
    return SheetLabels(sheet_from(col_a, **kw))


def test_rows_under_lists_rows_until_two_blank_rows():
    labels = block({6: 'Apartment', 7: 'Officetel', 8: 'Shophouse', 11: 'Unrelated Later Label'})
    assert labels.rows_under('Product Mix') == [6, 7, 8]


def test_rows_under_tolerates_a_single_blank_row():
    labels = block({6: 'Apartment', 7: 'Officetel', 9: 'Shophouse', 10: 'Villas'})
    assert labels.rows_under('Product Mix') == [6, 7, 9, 10]


def test_rows_under_blank_counter_resets_after_an_entry():
    labels = block({6: 'A', 8: 'B', 10: 'C'})        # blank, entry, blank, entry, blank, entry
    assert labels.rows_under('Product Mix') == [6, 8, 10]


def test_rows_under_leading_blank_rows_do_not_end_the_block():
    labels = block({8: 'Apartment', 9: 'Officetel'})
    assert labels.rows_under('Product Mix') == [8, 9]


def test_rows_under_stops_at_a_stop_header_even_with_hints():
    labels = block({6: 'Apartment', 7: 'Officetel', 8: 'PARKING (slots)', 9: 'Car Parking Slots'})
    assert labels.rows_under('Product Mix', stop_headers=['Parking']) == [6, 7]


def test_rows_under_without_stop_headers_runs_into_the_next_section():
    labels = block({6: 'Apartment', 7: 'PARKING'})
    assert labels.rows_under('Product Mix') == [6, 7]


def test_rows_under_respects_max_rows():
    labels = block({r: f'Item {r}' for r in range(6, 20)})
    assert labels.rows_under('Product Mix', max_rows=3) == [6, 7, 8]
    assert len(labels.rows_under('Product Mix')) == 14


def test_rows_under_empty_block():
    assert block({}).rows_under('Product Mix') == []


def test_rows_under_unknown_header_is_fatal():
    with pytest.raises(LabelNotFound):
        block({6: 'Apartment'}).rows_under('Public Holidays')
