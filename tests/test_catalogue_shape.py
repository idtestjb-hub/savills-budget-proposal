"""verification.checks.catalogue_shape_problems / check_catalogue_shape: an unquoted comma in a text cell, a blank
code and a repeated code are reported; quoted commas and multi-line quoted cells are fine. TEST DATA."""
from verification import checks

HEADER = 'code,item_en,method_detail,section\n'


def test_well_formed_lines_pass():
    lines = ['# comment, with commas\n', HEADER,
             'XA1,Item one,"Priced at 1,000 USD, times 1.10",expense\n',
             'XA2,Item two,"two\n', 'lines",expense\n']
    problems, count = checks.catalogue_shape_problems(lines)
    assert problems == []
    assert count == 2


def test_unquoted_comma_blank_and_repeated_codes_fail():
    lines = [HEADER,
             'XA1,Item one,Priced at 1,000 USD,expense\n',
             ',Item blank,detail,expense\n',
             'XA3,Item three,detail,expense\n',
             'XA3,Item three again,detail,expense\n']
    problems, _count = checks.catalogue_shape_problems(lines)
    reasons = {(label, reason.split(' (')[0]) for label, reason in problems}
    assert ('XA1', '5 fields, header has 4') in reasons
    assert ('record 2', 'blank code') in reasons
    assert ('XA3', 'code listed twice') in reasons


def test_live_catalogue_is_well_formed():
    ok, rows, diffs, _notes = checks.check_catalogue_shape()
    assert ok, diffs
    assert rows[0][1] >= 125
