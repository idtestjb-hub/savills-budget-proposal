"""
Service levels (change add-service-level-table, spec service-level-tiers).

Tells a PM whether the cleaning and security crews the tool proposes are lean, standard or generous next to real
Savills projects. Display only: nothing here changes a figure.

Two data files under Budget_Agent/data/service_levels/ (outer repository, never pushed):
  Ref_ServiceLevelThresholds.csv  one row per service: the two cut-offs, the level names on each side, the sanity
                                  bounds, approval dates. Editable without code. Landscape is "not_set".
  Ref_ServiceLevelProjects.csv    one anonymous row per real project, built by build_service_levels.py from the scan
                                  store in Savills-local.

Measures (design D5/D6):
  cleaning  = total fee-paying NFA (m²) / cleaning people on duty per day (supervisors included)
  security  = security 24-hour posts / (total fee-paying NFA / 10,000).  A row on shift 24H counts 24 h,
              any other shift row counts 8 h (three shift rows of a post = one 24-hour post).
In the tool the people on duty are Staffing Demand's "Staff On Duty / Day" column; the roster's Staff Count
(rest-day cover added) is reported beside it but does not feed the measure.

Rules: a value exactly on a cut-off falls in the higher-numbered band (design D2); a missing or zero input, or a
value outside the bounds, gives "chưa phân loại" with a reason, never a guess (D10); a value within 10% of a cut-off
carries the mark "sát ngưỡng" (D11); cleaning and security are never merged (D3); the percentile is computed over
form-read, classified real projects, leaving the project itself out (D4, D8).
"""
import csv
import hashlib
import math
import os
import unicodedata

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
BUDGET_AGENT = os.path.abspath(os.path.join(SOURCE_DIR, '..'))
DATA_DIR = os.path.join(BUDGET_AGENT, 'data', 'service_levels')
THRESHOLDS_CSV = os.path.join(DATA_DIR, 'Ref_ServiceLevelThresholds.csv')
PROJECTS_CSV = os.path.join(DATA_DIR, 'Ref_ServiceLevelProjects.csv')

SERVICES = ('cleaning', 'security')
NOT_CLASSIFIED = 'chưa phân loại'
NEAR_MARK = 'sát ngưỡng'
REASON_NO_NFA = 'thiếu NFA'
REASON_NO_HEADCOUNT = 'thiếu số người'
REASON_OUT_OF_BOUNDS = 'ngoài cận, nghi đọc sai'
SOURCE_FORM = 'form'
SOURCE_COST = 'chi phí'
NEAR_BAND = 0.10          # within cut-off x (1 - 0.10) .. cut-off x (1 + 0.10), lower edge inclusive
SELF_NFA_TOLERANCE = 0.005  # D8: a real project within 0.5% of the input's NFA is the project itself
SHIFT_HOURS_24H = 24.0
SHIFT_HOURS_OTHER = 8.0
SHEET_NAME = 'Service Levels'

# The same keywords the Service sheet and the deliverable's ESS1/ESS4 remarks use to find the rows (D5).
POSITION_KEYWORDS = {'cleaning': ['cleaning'], 'security': ['security']}


class Threshold:
    __slots__ = ('service', 'measure', 'unit', 'cutoff_1', 'cutoff_2', 'direction', 'levels', 'bound_low',
                 'bound_high', 'approved_on', 'bounds_approved_on', 'source')

    def __init__(self, row):
        self.service = row['service'].strip()
        self.measure = row.get('measure', '')
        self.unit = row.get('unit', '')
        self.direction = row.get('direction', '').strip()
        self.approved_on = row.get('approved_on', '')
        self.bounds_approved_on = row.get('bounds_approved_on', '')
        self.source = row.get('source', '')
        if self.direction == 'not_set':
            self.cutoff_1 = self.cutoff_2 = self.bound_low = self.bound_high = None
            self.levels = None
            return
        self.cutoff_1 = float(row['cutoff_1'])
        self.cutoff_2 = float(row['cutoff_2'])
        if not self.cutoff_1 < self.cutoff_2:
            raise ValueError(f'{self.service}: cutoff_1 must be below cutoff_2')
        self.levels = (row['level_below_cutoff_1'].strip(), row['level_between'].strip(),
                       row['level_from_cutoff_2'].strip())
        self.bound_low = float(row['bound_low']) if row.get('bound_low', '') != '' else None
        self.bound_high = float(row['bound_high']) if row.get('bound_high', '') != '' else None

    @property
    def is_set(self):
        return self.direction != 'not_set'


def load_thresholds(path=None):
    """{service: Threshold}. Raises if the file is missing or a service is malformed: a sheet that silently
    classified with no thresholds would be worse than a run that stops."""
    path = path or THRESHOLDS_CSV
    out = {}
    with open(path, encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            if not row.get('service', '').strip():
                continue
            t = Threshold(row)
            out[t.service] = t
    for s in SERVICES:
        if s not in out or not out[s].is_set:
            raise ValueError(f'{os.path.basename(path)} has no thresholds for {s}')
    return out


class Classification:
    """level is None when not classified; reason says why. near is the 'sát ngưỡng' mark (bool)."""
    __slots__ = ('service', 'value', 'level', 'reason', 'near')

    def __init__(self, service, value, level, reason='', near=False):
        self.service, self.value, self.level, self.reason, self.near = service, value, level, reason, near

    @property
    def label(self):
        if self.level is None:
            return f'{NOT_CLASSIFIED}: {self.reason}' if self.reason else NOT_CLASSIFIED
        return self.level

    def as_dict(self):
        return {'service': self.service, 'value': self.value, 'level': self.level, 'reason': self.reason,
                'near': self.near, 'label': self.label}


def classify(service, value, thresholds, reason_if_missing=REASON_NO_HEADCOUNT):
    """Classify one measure. `value` None/0/negative -> not classified with `reason_if_missing`.
    Edge rule (D2): value < cutoff_1 -> first level; cutoff_1 <= value < cutoff_2 -> second; value >= cutoff_2 -> third.
    Bounds (D10): value < bound_low or value > bound_high -> not classified, 'ngoài cận, nghi đọc sai'.
    Near (D11): cutoff x 0.9 <= value < cutoff x 1.1 for either cut-off -> near = True (level unchanged)."""
    t = thresholds[service]
    if value is None or (isinstance(value, float) and math.isnan(value)) or value <= 0:
        return Classification(service, value, None, reason_if_missing)
    if (t.bound_low is not None and value < t.bound_low) or (t.bound_high is not None and value > t.bound_high):
        return Classification(service, value, None, REASON_OUT_OF_BOUNDS)
    if value < t.cutoff_1:
        level = t.levels[0]
    elif value < t.cutoff_2:
        level = t.levels[1]
    else:
        level = t.levels[2]
    near = any(c * (1 - NEAR_BAND) <= value < c * (1 + NEAR_BAND) for c in (t.cutoff_1, t.cutoff_2))
    return Classification(service, value, level, '', near)


def measure_cleaning(nfa, people):
    """m² of fee-paying NFA per cleaning person on duty; None when either input is missing or zero."""
    if not nfa or nfa <= 0 or not people or people <= 0:
        return None
    return nfa / people


def measure_security(nfa, posts24):
    """24-hour-equivalent security posts per 10,000 m² of fee-paying NFA; None when either is missing or zero."""
    if not nfa or nfa <= 0 or not posts24 or posts24 <= 0:
        return None
    return posts24 / (nfa / 10_000.0)


def shift_hours(shift_code):
    return SHIFT_HOURS_24H if str(shift_code or '').strip().upper() == '24H' else SHIFT_HOURS_OTHER


def roster_count(staff_per_day, coverage_days):
    """The roster's Staff Count for one demand row: 7-day coverage needs 7/6 the people on duty, rounded up."""
    spd = staff_per_day or 0
    return math.ceil(spd * 7 / 6) if (coverage_days or 0) >= 7 else spd


def tool_headcount(demand):
    """Count the tool's own cleaning and security rows of Staffing Demand (D5).

    Returns {'cleaning': {...}, 'security': {...}} with, per service: on_duty (sum of Staff On Duty / Day),
    roster (sum of the roster's Staff Count), posts24 (security only: sum of on-duty x shift hours / 24),
    rows ([(position, shift, on_duty, hours, roster_count)]).
    """
    out = {}
    for service, kws in POSITION_KEYWORDS.items():
        rows, on_duty, roster, post_hours = [], 0.0, 0, 0.0
        for d in demand or []:
            pos = str(d.get('Position') or '')
            if not any(k in pos.lower() for k in kws):
                continue
            spd = float(d.get('StaffPerDay') or 0)
            hrs = shift_hours(d.get('ShiftCode')) if service == 'security' else 0.0
            rc = roster_count(spd, d.get('CoverageDays'))
            rows.append((pos, d.get('ShiftCode'), spd, hrs if service == 'security' else None, rc))
            on_duty += spd
            roster += rc
            post_hours += spd * hrs
        # hours summed first, divided once: 3 x (5 people x 8 h) / 24 is exactly 5 posts, not 4.999...
        out[service] = {'on_duty': on_duty, 'roster': roster, 'rows': rows,
                        'posts24': post_hours / 24.0 if service == 'security' else None}
    return out


def name_key(name):
    """First 16 hex characters of SHA-256 of the normalised project name (NFC, case-folded, letters and digits
    only). The same key the real-budget-ranges change uses (its design D2), so a project already in the store
    is left out of its own comparison. Empty for a blank name."""
    s = unicodedata.normalize('NFC', str(name or '')).casefold()
    s = ''.join(ch for ch in s if ch.isalnum())
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16] if s else ''


PROJECT_COLUMNS = ['project_id', 'name_key', 'nfa_m2', 'budget_year', 'nfa_fee_m2',
                   'cln_people', 'cln_source', 'cln_m2_per_person', 'cln_level', 'cln_reason', 'cln_near',
                   'sec_posts24', 'sec_source', 'sec_per_10k', 'sec_level', 'sec_reason', 'sec_near',
                   'flag', 'snapshot']


def _num(v):
    if v in (None, ''):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_projects(path=None):
    """The anonymous real-project table as a list of dicts (numbers parsed, '' -> None)."""
    path = path or PROJECTS_CSV
    rows = []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            r = dict(row)
            for k in ('nfa_m2', 'nfa_fee_m2', 'cln_people', 'cln_m2_per_person', 'sec_posts24', 'sec_per_10k'):
                r[k] = _num(r.get(k))
            r['budget_year'] = int(float(r['budget_year'])) if r.get('budget_year') not in (None, '') else None
            for k in ('cln_near', 'sec_near'):
                r[k] = str(r.get(k, '')).strip().lower() in ('1', 'true', 'yes', NEAR_MARK)
            rows.append(r)
    return rows


def comparison_set(service, projects, self_name_key=None, self_nfa=None):
    """Form-read, classified rows of `service`, with the project itself left out (D4, D8).
    Returns (values, n_inferred_classified)."""
    col_v = 'cln_m2_per_person' if service == 'cleaning' else 'sec_per_10k'
    col_src = 'cln_source' if service == 'cleaning' else 'sec_source'
    col_lvl = 'cln_level' if service == 'cleaning' else 'sec_level'
    values, n_inferred = [], 0
    for r in projects:
        if not r.get(col_lvl) or r[col_lvl] == NOT_CLASSIFIED or r.get(col_v) is None:
            continue
        if self_name_key and r.get('name_key') == self_name_key:
            continue
        if self_nfa and r.get('nfa_m2') and abs(r['nfa_m2'] - self_nfa) <= SELF_NFA_TOLERANCE * self_nfa:
            continue
        if r.get(col_src) == SOURCE_FORM:
            values.append(r[col_v])
        else:
            n_inferred += 1
    return values, n_inferred


def percentile(value, values):
    """Share (0-100) of the comparison values at or below `value`; None when there is nothing to compare."""
    if value is None or not values:
        return None
    return 100.0 * sum(1 for v in values if v <= value) / len(values)


def evaluate(project, demand, thresholds=None, projects=None):
    """Everything the Service Levels sheet shows, for the project being budgeted. Reads the two data files
    when not given. Never raises for a missing input: the sheet then shows 'chưa phân loại' and the reason."""
    thresholds = thresholds or load_thresholds()
    projects = projects if projects is not None else load_projects()
    nfa = float(project.get('total_nfa') or 0)
    counts = tool_headcount(demand)
    self_key = name_key(project.get('name'))
    out = {'nfa': nfa, 'counts': counts, 'thresholds': thresholds, 'services': {},
           'headcount_source': project.get('staffing_source') or 'Staffing Demand (input or ratio-driven estimate)'}
    for service in SERVICES:
        c = counts[service]
        if service == 'cleaning':
            value = measure_cleaning(nfa, c['on_duty'])
        else:
            value = measure_security(nfa, c['posts24'])
        reason = REASON_NO_NFA if nfa <= 0 else REASON_NO_HEADCOUNT
        cls = classify(service, value, thresholds, reason_if_missing=reason)
        values, n_inferred = comparison_set(service, projects, self_key, nfa if nfa > 0 else None)
        out['services'][service] = {
            'classification': cls, 'value': value, 'on_duty': c['on_duty'], 'roster': c['roster'],
            'posts24': c['posts24'], 'percentile': percentile(value, values) if cls.level else None,
            'n_form': len(values), 'n_inferred': n_inferred, 'rows': c['rows'],
        }
    out['landscape'] = 'chưa đặt ngưỡng: thiếu diện tích cây xanh'
    return out
