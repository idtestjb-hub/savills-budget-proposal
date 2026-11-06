"""
One-off migration (change reference-projects-by-key, task 1.2): add a filled `RefKey` column to the four data files
that carry a reference project's figures, keyed through the registry's display names and aliases.

    python migrate_reference_keys.py [--data <data folder>] [--date 2026-11-06] [--dry-run]

For each file: a copy `<file>.backup-<date>` is written beside it first; then the file is rewritten with the same
comment lines, the same columns in the same order plus `RefKey` last, every original value byte-identical, line
endings as in the original. The script refuses to write anything when a row of Fact_OPEX, Fact_Capex_Rescanned or
Fact_CapexReserve cannot be mapped to a key. Rows of Ref_ComparableVATBasis that belong to a master-list project
(not a reference project) get an empty RefKey by design. Office-only; never shipped in a site package.
"""
import argparse
import csv
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import reference_projects as rp  # noqa: E402

DEFAULT_DATA = os.path.join(os.path.dirname(HERE), 'data')
FILES = (
    ('generation_A_star_schema/Fact_OPEX.csv', 'Project', True),
    ('generation_A_star_schema/Fact_Capex_Rescanned.csv', 'Project', True),
    ('generation_A_star_schema/Fact_CapexReserve.csv', 'Project', True),
    ('master_list_verified/Ref_ComparableVATBasis.csv', 'project_key', False),
)


def read_csv_text(path):
    with open(path, 'rb') as fh:
        raw = fh.read()
    text = raw.decode('utf-8-sig')
    eol = '\r\n' if '\r\n' in text else '\n'
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and lines[i].startswith('#'):
        i += 1
    comments, body = lines[:i], ''.join(lines[i:])
    rows = list(csv.reader(io.StringIO(body)))
    return comments, rows[0], rows[1:], eol, raw.startswith(b'\xef\xbb\xbf')


def plan(data, registry):
    out = []
    problems = []
    for rel, col, strict in FILES:
        path = os.path.join(data, *rel.split('/'))
        comments, header, rows, eol, bom = read_csv_text(path)
        if 'RefKey' in header:
            problems.append(f'{rel}: already has a RefKey column; nothing to do.')
            continue
        ci = header.index(col)
        keys = []
        for n, r in enumerate(rows, start=2):
            name = r[ci].strip() if ci < len(r) else ''
            key = rp.key_for_name(name, registry) if name else None
            if key is None and strict and name:
                problems.append(f'{rel} row {n}: "{name}" is not in the registry (display name or alias).')
            keys.append(key or '')
        out.append(dict(rel=rel, path=path, comments=comments, header=header, rows=rows, eol=eol, bom=bom, keys=keys))
    return out, problems


def write_file(item, date):
    backup = item['path'] + f'.backup-{date}'
    if not os.path.exists(backup):
        shutil.copy2(item['path'], backup)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator=item['eol'])
    w.writerow(item['header'] + ['RefKey'])
    for r, k in zip(item['rows'], item['keys']):
        w.writerow(r + [k])
    text = ''.join(item['comments']) + buf.getvalue()
    with open(item['path'], 'wb') as fh:
        if item['bom']:
            fh.write(b'\xef\xbb\xbf')
        fh.write(text.encode('utf-8'))
    return backup


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=DEFAULT_DATA)
    ap.add_argument('--date', default='2026-11-06')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    registry = os.path.join(a.data, 'master_list_verified', 'Dim_ReferenceProject.csv')
    rp.load(registry, force=True)
    items, problems = plan(a.data, registry)
    for p in problems:
        print('STOP:', p)
    if problems:
        return 1
    for it in items:
        filled = sum(1 for k in it['keys'] if k)
        print(f"{it['rel']}: {len(it['rows'])} rows, RefKey filled on {filled}, blank on {len(it['rows']) - filled}, "
              f"eol={'CRLF' if it['eol'] == chr(13) + chr(10) else 'LF'}")
        if not a.dry_run:
            print('   backup ->', write_file(it, a.date))
    return 0


if __name__ == '__main__':
    sys.exit(main())
