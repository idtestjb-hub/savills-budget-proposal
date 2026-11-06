"""
Reference-project registry (change reference-projects-by-key).

The real budgets the tool prices from are identified by a stable key (R01, R02, ...) held in one data file,
`data/master_list_verified/Dim_ReferenceProject.csv`. Every other data file that carries one of their figures
holds that key in a `RefKey` column, and the code joins on the key. Names are display data only: on the office
data they are the real names, in a site package they are pseudonyms, and the code reads the same either way.

Columns of the registry (one row per reference project):
  RefKey, DisplayName, Aliases ('|'-separated name variants other files use), TotalNFA_m2 (whole-building NFA the
  comparables ranking uses), CapexNFA_m2 (the NFA the capex item scaling uses; the grand total of the source file,
  parking included, where that is what was measured), ApartmentUnits, TotalUnits, MgmtRate_VND_m2_month,
  MgmtRateVAT, District, City, Comparable (1 = part of the hand-verified comparables pool), ExcludedFromRanking
  (reason text, blank when not excluded), Roles ('|'-separated: utilities_base, parking_base, capex_items),
  Source, LocationSource, VerifiedOn.

Reading the registry is the only way the tool learns a reference project's name. Nothing writes it at run time.
"""
import csv
import os
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET_AGENT = os.path.dirname(HERE)
REGISTRY_CSV = os.path.join(BUDGET_AGENT, 'data', 'master_list_verified', 'Dim_ReferenceProject.csv')

ROLE_UTILITIES_BASE = 'utilities_base'
ROLE_PARKING_BASE = 'parking_base'
ROLE_CAPEX_ITEMS = 'capex_items'

COLUMNS = ['RefKey', 'DisplayName', 'Aliases', 'TotalNFA_m2', 'CapexNFA_m2', 'ApartmentUnits', 'TotalUnits',
           'MgmtRate_VND_m2_month', 'MgmtRateVAT', 'District', 'City', 'Comparable', 'ExcludedFromRanking', 'Roles',
           'Source', 'LocationSource', 'VerifiedOn']

_CACHE = {}


class ReferenceRegistryError(RuntimeError):
    """The registry file is missing or malformed. The message names the file and the row."""


def norm(name):
    """Name key for matching: NFC, case-folded, single spaces."""
    return ' '.join(unicodedata.normalize('NFC', str(name or '')).casefold().split())


def _float(v):
    v = (v or '').strip()
    return float(v) if v else None


def _int(v):
    f = _float(v)
    return int(f) if f is not None else None


def _rate(v):
    """A management-fee rate: an int when the file writes a whole number (the figure the analysis prints), else a float."""
    f = _float(v)
    if f is None:
        return None
    return int(f) if f == int(f) and '.' not in (v or '') else f


def _row(raw, row_no, path):
    key = (raw.get('RefKey') or '').strip()
    name = (raw.get('DisplayName') or '').strip()
    if not key or not name:
        raise ReferenceRegistryError(f'{os.path.basename(path)} row {row_no}: RefKey and DisplayName are required.')
    aliases = [a.strip() for a in (raw.get('Aliases') or '').split('|') if a.strip()]
    roles = {r.strip() for r in (raw.get('Roles') or '').split('|') if r.strip()}
    return dict(
        key=key, name=name, aliases=aliases,
        nfa=_float(raw.get('TotalNFA_m2')), capex_nfa=_float(raw.get('CapexNFA_m2')),
        units=_int(raw.get('ApartmentUnits')), total_units=_int(raw.get('TotalUnits')),
        mgmt_rate=_rate(raw.get('MgmtRate_VND_m2_month')), mgmt_rate_vat=(raw.get('MgmtRateVAT') or '').strip() or None,
        district=(raw.get('District') or '').strip() or None, city=(raw.get('City') or '').strip() or None,
        comparable=(raw.get('Comparable') or '').strip() in ('1', 'true', 'True', 'yes'),
        excluded_from_ranking=(raw.get('ExcludedFromRanking') or '').strip() or None,
        roles=roles, source=(raw.get('Source') or '').strip(), location_source=(raw.get('LocationSource') or '').strip(),
        verified_on=(raw.get('VerifiedOn') or '').strip(),
    )


def load(path=None, force=False):
    """All registry rows as typed dicts, cached per path. Raises ReferenceRegistryError when the file is missing."""
    path = path or REGISTRY_CSV
    if not force and path in _CACHE:
        return _CACHE[path]
    if not os.path.isfile(path):
        raise ReferenceRegistryError(f'Reference-project registry not found: {path}. The tool cannot price without it.')
    rows = []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(ln for ln in fh if not ln.startswith('#'))
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ReferenceRegistryError(f'{os.path.basename(path)} is missing columns: {", ".join(missing)}.')
        for row_no, raw in enumerate(reader, start=2):
            rows.append(_row(raw, row_no, path))
    keys = [r['key'] for r in rows]
    if len(set(keys)) != len(keys):
        raise ReferenceRegistryError(f'{os.path.basename(path)}: duplicate RefKey.')
    seen = {}
    for r in rows:
        for n in [r['name']] + r['aliases']:
            k = norm(n)
            if k in seen and seen[k] != r['key']:
                raise ReferenceRegistryError(f'{os.path.basename(path)}: name "{n}" is listed under {seen[k]} and {r["key"]}.')
            seen[k] = r['key']
    _CACHE[path] = rows
    return rows


def clear_cache():
    _CACHE.clear()


def by_key(key, path=None):
    for r in load(path):
        if r['key'] == key:
            return r
    raise KeyError(key)


def by_role(role, path=None):
    return [r for r in load(path) if role in r['roles']]


def one_by_role(role, path=None):
    rows = by_role(role, path)
    if not rows:
        raise ReferenceRegistryError(f'No reference project carries the role "{role}" in the registry.')
    return rows[0]


def key_for_name(name, path=None):
    """The key whose display name or alias equals `name` (normalised), or None."""
    k = norm(name)
    if not k:
        return None
    for r in load(path):
        if k == norm(r['name']) or any(k == norm(a) for a in r['aliases']):
            return r['key']
    return None


def display_name(key, path=None):
    return by_key(key, path)['name']


def all_names(path=None):
    """Every display name and alias in the registry (as written)."""
    out = set()
    for r in load(path):
        out.add(r['name'])
        out.update(r['aliases'])
    return out


def keys(path=None):
    return [r['key'] for r in load(path)]


def hand_verified_comparables(path=None):
    """The comparables pool entries (Comparable = 1) in the dict shape the comparables module has always used, plus
    `key`. `excluded_from_ranking` carries the reason text or is absent."""
    out = []
    for r in load(path):
        if not r['comparable']:
            continue
        c = dict(key=r['key'], name=r['name'], nfa=r['nfa'], units=r['units'], total_units=r['total_units'],
                 mgmt_rate=r['mgmt_rate'], mgmt_rate_vat=r['mgmt_rate_vat'], source=r['source'],
                 district=r['district'], city=r['city'], location_source=r['location_source'])
        if r['excluded_from_ranking']:
            c['excluded_from_ranking'] = r['excluded_from_ranking']
        out.append(c)
    return out
