"""
Usage benchmark for a new prospect's electricity, water and diesel (change widen-utility-and-capex-sources).

The usage per m² per month of each energy line is the median over real projects whose common-area consumption was
checked by hand, read from `data/generation_B_verified/Ref_UtilityUsage.csv` (one row per project and utility, with
the source cell and the check result; built office-side by build_utility_usage.py, never written at run time).

Rule (user decision 2026-11-06, outer docs/05-decisions.md "Utility and capex sources: four rules"):
- only rows with check = accepted count, one project once per utility;
- values outside [Q1 - 1.5 IQR, Q3 + 1.5 IQR] of the accepted values are dropped (quartiles by linear interpolation,
  statistics.quantiles(method='inclusive'));
- at least MIN_PROJECTS projects must remain, otherwise the caller falls back to the utilities base project (n=1) and
  says so on the remark.
"""
import csv
import os
import statistics

BUDGET_AGENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
USAGE_CSV = os.path.join(BUDGET_AGENT, 'data', 'generation_B_verified', 'Ref_UtilityUsage.csv')

MIN_PROJECTS = 5
IQR_FENCE = 1.5
CATEGORY_UTILITY = {'Electricity': 'electricity', 'Water': 'water', 'Diesel (Generator Fuel)': 'diesel'}
UNITS = {'electricity': 'kWh', 'water': 'm3', 'diesel': 'litre'}
COLUMNS = ['file_id', 'project_id', 'utility', 'quantity_month', 'unit', 'period_basis', 'conversion', 'nfa_m2',
           'nfa_source', 'usage_per_m2_month', 'source_sheet', 'source_cell', 'check', 'reason', 'checked_by',
           'checked_on']

_CACHE = {}


class UtilityUsageError(RuntimeError):
    """The usage table is missing or malformed. The message names the file and the row."""


def _num(value, path, row_no, column):
    try:
        return float(str(value).replace(',', ''))
    except (TypeError, ValueError):
        raise UtilityUsageError(f'{os.path.basename(path)} row {row_no}: {column} is not a number ({value!r}).')


def load(path=None, force=False):
    """{utility: [{project_id, file_id, usage_per_m2, quantity_month, nfa_m2, period_basis}]} of the accepted rows."""
    path = os.path.abspath(path or USAGE_CSV)
    if path in _CACHE and not force:
        return _CACHE[path]
    if not os.path.isfile(path):
        raise UtilityUsageError(f'Thiếu file lượng dùng điện/nước/dầu: {path}')
    out = {u: [] for u in UNITS}
    seen = set()
    with open(path, encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(ln for ln in fh if not ln.startswith('#'))
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise UtilityUsageError(f'{os.path.basename(path)} is missing columns {missing}.')
        for row_no, row in enumerate(reader, start=2):
            if (row.get('check') or '').strip().lower() != 'accepted':
                continue
            utility = (row.get('utility') or '').strip().lower()
            if utility not in out:
                raise UtilityUsageError(f'{os.path.basename(path)} row {row_no}: unknown utility {utility!r}.')
            pid = (row.get('project_id') or '').strip()
            if (utility, pid) in seen:
                raise UtilityUsageError(f'{os.path.basename(path)} row {row_no}: {pid} has two accepted {utility} rows.')
            seen.add((utility, pid))
            qty = _num(row['quantity_month'], path, row_no, 'quantity_month')
            nfa = _num(row['nfa_m2'], path, row_no, 'nfa_m2')
            if qty <= 0 or nfa <= 0:
                raise UtilityUsageError(f'{os.path.basename(path)} row {row_no}: quantity and NFA must be positive.')
            out[utility].append(dict(project_id=pid, file_id=(row.get('file_id') or '').strip(), quantity_month=qty,
                                     nfa_m2=nfa, usage_per_m2=qty / nfa,
                                     period_basis=(row.get('period_basis') or '').strip()))
    _CACHE[path] = out
    return out


def clear_cache():
    _CACHE.clear()


def fence(values, k=IQR_FENCE):
    """(low, high) of the IQR fence, or (None, None) with fewer than four values (no quartiles worth the name)."""
    if len(values) < 4:
        return None, None
    q1, _, q3 = statistics.quantiles(values, n=4, method='inclusive')
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def benchmark(category, path=None):
    """dict(utility, unit, median, n, kept=[(project_id, usage)], dropped=[(project_id, usage)], enough, reason).
    `enough` is False when fewer than MIN_PROJECTS remain; the caller then falls back to the utilities base."""
    utility = CATEGORY_UTILITY[category]
    rows = load(path)[utility]
    values = [r['usage_per_m2'] for r in rows]
    low, high = fence(values)
    kept = [(r['project_id'], r['usage_per_m2']) for r in rows
            if low is None or low <= r['usage_per_m2'] <= high]
    dropped = [(r['project_id'], r['usage_per_m2']) for r in rows
               if low is not None and not low <= r['usage_per_m2'] <= high]
    kept.sort(key=lambda kv: kv[1])
    enough = len(kept) >= MIN_PROJECTS
    median = statistics.median([v for _, v in kept]) if kept else None
    reason = None if enough else (f'chỉ {len(kept)} dự án có lượng dùng đã kiểm (cần tối thiểu {MIN_PROJECTS})')
    return dict(utility=utility, unit=UNITS[utility], median=median, n=len(kept), kept=kept, dropped=dropped,
                fence=(low, high), enough=enough, reason=reason)
