"""reference_projects.py and the RefKey contract (change reference-projects-by-key).

Against the real registry and the real fact files (read-only): the keys, roles and aliases resolve; every fact file
carries a known RefKey; and no module that runs during a budget or Review spells a reference project's name. The
invented-registry cases use a temporary file.
"""
import csv
import glob
import os

import pytest

import reference_projects as rp

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))           # source_code/
DATA = os.path.join(os.path.dirname(HERE), 'data')
FACT_FILES = (
    ('generation_A_star_schema/Fact_OPEX.csv', False),
    ('generation_A_star_schema/Fact_Capex_Rescanned.csv', False),
    ('generation_A_star_schema/Fact_CapexReserve.csv', False),
    ('master_list_verified/Ref_ComparableVATBasis.csv', True),      # master-list rows may have a blank key
)
# Office-only scripts: they rebuild or migrate data and may spell the names; they never run during a budget or Review
# and build_site_package.py leaves them out of a site package.
OFFICE_ONLY = ('build_site_', 'build_reference_registry', 'build_master_rate_card', 'build_project_plan_v2',
               'build_real_budget_ranges', 'build_service_levels', 'build_prior_coverage', 'build_roster_input_form',
               'rescan_', 'migrate_', 'study_', 'etl_', 'derive_', 'transform_', 'extract_info_sheets',
               'generate_from_real_project', 'method_coverage', 'build_utility_usage')


def runtime_modules():
    files = glob.glob(os.path.join(HERE, '*.py')) + glob.glob(os.path.join(HERE, 'webapp', '*.py')) \
        + glob.glob(os.path.join(HERE, 'verification', '*.py'))
    return sorted(f for f in files if not os.path.basename(f).startswith(OFFICE_ONLY))


# ---------------------------------------------------------------- real registry

def test_registry_has_keys_r01_to_r12_and_the_roles_resolve():
    # R09..R12: store projects added to the capex pool by change widen-utility-and-capex-sources.
    rows = rp.load(force=True)
    assert [r['key'] for r in rows] == [f'R{i:02d}' for i in range(1, 13)]
    assert len(rp.by_role(rp.ROLE_UTILITIES_BASE)) == 1 and len(rp.by_role(rp.ROLE_PARKING_BASE)) == 1
    assert len(rp.by_role(rp.ROLE_CAPEX_ITEMS)) == 11
    assert not any(r['comparable'] for r in rows[8:])
    base = rp.one_by_role(rp.ROLE_UTILITIES_BASE)
    assert base['nfa'] and base['nfa'] > 0 and rp.ROLE_CAPEX_ITEMS in base['roles']
    assert all(r['capex_nfa'] for r in rp.by_role(rp.ROLE_CAPEX_ITEMS))


def test_every_display_name_and_alias_resolves_to_its_own_key():
    for r in rp.load():
        assert rp.key_for_name(r['name']) == r['key']
        assert rp.key_for_name(r['name'].upper()) == r['key']          # case-insensitive
        for a in r['aliases']:
            assert rp.key_for_name(a) == r['key']
    assert rp.key_for_name('Khu Thu Nghiem') is None and rp.key_for_name('') is None


def test_hand_verified_comparables_keep_the_old_shape_plus_key():
    hv = rp.hand_verified_comparables()
    assert len(hv) == 7 and all(c['key'] for c in hv)
    assert {'name', 'nfa', 'units', 'total_units', 'mgmt_rate', 'mgmt_rate_vat', 'source', 'district', 'city',
            'location_source'} <= set(hv[0])
    assert sum(1 for c in hv if c.get('excluded_from_ranking')) == 2        # the two Hà Nội projects


@pytest.mark.parametrize('rel, blank_allowed', FACT_FILES)
def test_fact_files_carry_a_known_refkey_on_every_row(rel, blank_allowed):
    known = set(rp.keys())
    with open(os.path.join(DATA, *rel.split('/')), encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(ln for ln in fh if not ln.startswith('#'))
        assert 'RefKey' in reader.fieldnames, f'{rel}: no RefKey column (run migrate_reference_keys.py)'
        rows = list(reader)
    assert rows
    keys = [(r.get('RefKey') or '').strip() for r in rows]
    unknown = sorted({k for k in keys if k and k not in known})
    assert unknown == [], f'{rel}: unknown keys {unknown}'
    if not blank_allowed:
        assert all(keys), f'{rel}: {keys.count("")} rows without RefKey'


def test_runtime_modules_do_not_spell_a_reference_project_name():
    names = sorted(rp.all_names(), key=len, reverse=True)
    hits = []
    for path in runtime_modules():
        text = open(path, encoding='utf-8', errors='replace').read()
        for n in names:
            if n in text:
                hits.append((os.path.relpath(path, HERE), n))
    assert hits == [], hits


# ---------------------------------------------------------------- invented registry

def test_missing_registry_stops_with_the_file_name(tmp_path):
    missing = str(tmp_path / 'Dim_ReferenceProject.csv')
    with pytest.raises(rp.ReferenceRegistryError) as e:
        rp.load(missing, force=True)
    assert 'Dim_ReferenceProject.csv' in str(e.value)


def _write(path, rows):
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=rp.COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in rp.COLUMNS})
    return str(path)


def test_duplicate_alias_across_keys_is_rejected(tmp_path):
    p = _write(tmp_path / 'reg.csv', [dict(RefKey='R01', DisplayName='Tháp A', Aliases='Thap A'),
                                       dict(RefKey='R02', DisplayName='Tháp B', Aliases='thap a')])
    with pytest.raises(rp.ReferenceRegistryError):
        rp.load(p, force=True)


def test_typed_fields_and_roles(tmp_path):
    p = _write(tmp_path / 'reg.csv', [dict(RefKey='R01', DisplayName='Tháp A', Aliases='Thap A|Budget 2026 Thap A',
                                            TotalNFA_m2='1234.5', CapexNFA_m2='', ApartmentUnits='10', TotalUnits='12',
                                            MgmtRate_VND_m2_month='15000', MgmtRateVAT='incl. VAT', Comparable='1',
                                            Roles='utilities_base|capex_items')])
    r = rp.load(p, force=True)[0]
    assert r['nfa'] == 1234.5 and r['capex_nfa'] is None and r['units'] == 10 and r['total_units'] == 12
    assert r['mgmt_rate'] == 15000.0 and r['mgmt_rate_vat'] == 'incl. VAT' and r['comparable'] is True
    assert r['roles'] == {'utilities_base', 'capex_items'} and r['aliases'] == ['Thap A', 'Budget 2026 Thap A']
    assert rp.key_for_name('budget 2026 thap a', p) == 'R01' and rp.display_name('R01', p) == 'Tháp A'
    assert rp.all_names(p) == {'Tháp A', 'Thap A', 'Budget 2026 Thap A'}
