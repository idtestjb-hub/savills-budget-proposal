"""How many project facts every known project would get, and from which source (change project-info-everywhere, D8).

    python verification/fact_coverage.py [--library]

Master: for every row of the master list, the facts master_facts() gives under the agreed rules (tower never filled,
floors / lifts only for one tower). With --library: for every readable file of the budget library, the parking slots
its 0. Info gives (read_info) and the master facts its folded project name finds. Prints counts only, no project names.
A report, not a gate.
"""
import argparse
import csv
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from webapp import facts_prefill as fp  # noqa: E402


def master_coverage(path=fp.MASTER_CSV):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.DictReader(fh))
    per_field, per_project = Counter(), Counter()
    for row in rows:
        facts, _notes = fp.row_facts(row)
        for k in facts:
            per_field[k] += 1
        per_project[len(facts)] += 1
    return len(rows), per_field, per_project


def library_coverage():
    import shutil
    import tempfile

    import review_import as ri
    from webapp import library
    entries = [e for e in library.entries() if e.get('selectable')]
    found, names_hit, errors = Counter(), Counter(), 0
    for e in entries:
        tmp = tempfile.mkdtemp(prefix='cov_')
        try:
            wb, _ = ri.open_workbook(library.long_path(e['path']), workdir=tmp)
            try:
                info = ri.read_info(wb)
            finally:
                wb.close()
            found['car_slots (0. Info)'] += info.car_bays is not None
            found['moto_slots (0. Info)'] += info.moto_bays is not None
            mfacts, notes = fp.master_facts(e.get('project') or info.name)
            names_hit['one master row' if mfacts else ('several rows' if notes and not notes[0]['key'] else 'no row')] += 1
            for k in mfacts:
                found[f'{k} (master)'] += 1
        except Exception:      # noqa: BLE001 - unreadable file: counted, not named
            errors += 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return len(entries), found, names_hit, errors


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--library', action='store_true', help='also read every selectable library file (slow)')
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8')
    n, per_field, per_project = master_coverage()
    print(f'Master list: {n} projects')
    for k in fp.FIELDS:
        print(f'  {k:<12} {per_field.get(k, 0):>4} / {n}')
    print('  facts per project:', dict(sorted(per_project.items())))
    if a.library:
        n, found, hits, errors = library_coverage()
        print(f'Library: {n} selectable files, {errors} unreadable')
        print('  master name match:', dict(hits))
        for k, v in sorted(found.items()):
            print(f'  {k:<26} {v:>4} / {n}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
