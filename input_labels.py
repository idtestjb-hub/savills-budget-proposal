"""
Finds fields in the intake workbook by the label that names them, rather than by cell address.

WHY THIS EXISTS. `read_input()` used to read twenty-one fixed addresses — `pi['B25']` for car
parking slots, `rs['B12']` for the roster month, and so on. Growing the Product Mix block from 5
products to 9 pushed every section below it down four rows, and the reader kept reading the old
addresses: the PARKING block was read as product data. It produced no error. The figures survived
only because pricing requires NFA and that column happened to be empty.

The labels sit in column A immediately beside every one of those fields. They are stable, they are
what a human uses to find the field, and they move with it. So the reader uses them.

A label that cannot be found is FATAL and names itself. That is the whole point: the bug being
fixed was a silent misread, and replacing it with a different silent behaviour would achieve
nothing.
"""
import re


class LabelNotFound(RuntimeError):
    """Raised when an expected label is not present on the sheet."""


class AmbiguousLabel(RuntimeError):
    """Raised when two labels on one sheet normalise to the same key."""


def normalise(label):
    """Reduce a label to a stable matching key.

    The form's labels carry units and hints — 'Pool Area (m²) — optional', '% of Collected
    Management Fee — leave blank if not %-based'. Matching on the full string would break the read
    every time someone edited a parenthetical. Matching on a loose substring would be worse:
    'Car Parking Slots' and 'Moto Parking Slots' share one, and a sloppy rule would pick whichever
    came first.

    So: cut at the first '(' or dash-run, collapse whitespace, casefold. 'Pool Area (m²) —
    optional' and 'Pool Area' both key to 'pool area'.
    """
    text = str(label or '')
    text = re.split(r'[(—–]|--', text, maxsplit=1)[0]
    text = re.sub(r'\s+', ' ', text).strip().strip(':').strip()
    return text.casefold()


class SheetLabels:
    """A one-pass index of a worksheet's column-A labels."""

    def __init__(self, worksheet, label_col=1, value_col=2, max_row=None):
        self.ws = worksheet
        self.name = worksheet.title
        self.label_col = label_col
        self.value_col = value_col
        self._index = {}
        last = max_row or min(worksheet.max_row or 1, 200)
        for row in range(1, last + 1):
            raw = worksheet.cell(row=row, column=label_col).value
            if raw is None or not str(raw).strip():
                continue
            key = normalise(raw)
            if not key:
                continue
            if key in self._index:
                # Deliberately fatal rather than first-wins. Two fields the reader cannot tell
                # apart is a programming error in the form, and silently picking one reintroduces
                # exactly the class of bug this module exists to remove.
                raise AmbiguousLabel(
                    f"Two labels on sheet {self.name!r} both reduce to {key!r}: "
                    f"row {self._index[key]} and row {row}. The reader cannot tell which field is "
                    f"meant. Rename one of them in build_project_input_form.py."
                )
            self._index[key] = row

    def has(self, label):
        return normalise(label) in self._index

    def row_of(self, label):
        key = normalise(label)
        if key not in self._index:
            near = [k for k in self._index if key.split(' ')[0] in k][:3]
            raise LabelNotFound(
                f"Sheet {self.name!r} has no field labelled {str(label)!r} (looked for {key!r}). "
                + (f"Nearest labels present: {near}. " if near else '')
                + "The intake form may be from a different version, or the label was renamed. "
                  "Nothing was read from a fallback position — fix the form or the expected label "
                  "rather than letting a value be taken from the wrong row."
            )
        return self._index[key]

    def value(self, label, col=None):
        """The value beside `label`.

        A present label whose value cell is empty returns None — that is an empty FIELD, not a
        missing one. Project Info's Savills-fee cells are deliberately blank (docs/05-decisions.md
        D1) and must keep reading as blank rather than raising.
        """
        return self.ws.cell(row=self.row_of(label), column=col or self.value_col).value

    def section_row(self, header):
        """The row of a section header such as 'PRODUCT MIX' or 'PARKING'."""
        return self.row_of(header)

    def rows_under(self, header, stop_headers=(), max_rows=60):
        """Row numbers below a section header, stopping at the next section or a blank run.

        Used for blocks whose length varies — the product mix, the public-holiday list — so the
        reader does not depend on how many entries the form happens to carry.
        """
        start = self.section_row(header) + 1
        stops = {normalise(h) for h in stop_headers}
        out = []
        blanks = 0
        for row in range(start, start + max_rows):
            raw = self.ws.cell(row=row, column=self.label_col).value
            key = normalise(raw)
            if not key:
                blanks += 1
                if blanks >= 2 and out:
                    break
                continue
            if key in stops:
                break
            blanks = 0
            out.append(row)
        return out
