"""Unit tests for master_comparables.resolve_product_rates, the one place each product's applied
management-fee rate is decided (change use-operating-project-actuals, P5).

The resolver must give exactly the figures the generators derived on their own before P5:
- Apartment: derive_product_rate_capped, or the blended derive_mgmt_rate over the 2 nearest
  comparables when no comparable has an Apartment rate;
- every other product: derive_product_rate over the same ranking, uncapped, or the Apartment rate.

The module is loaded under a private name with the reference CSVs reported as absent, so these
tests never read anything under data/. Invented data only: fictional towers and districts.
This file sets up its own import path, so it runs with or without a conftest.py beside it.
"""
import importlib.util
import os
import sys
from unittest import mock

import pytest

SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)
SRC = os.path.join(SOURCE_DIR, 'master_comparables.py')


@pytest.fixture(scope='module')
def mc_module():
    real_exists = os.path.exists

    def fake_exists(path):
        if str(path).lower().endswith('.csv'):
            return False
        return real_exists(path)

    with mock.patch('os.path.exists', side_effect=fake_exists):
        spec = importlib.util.spec_from_file_location('master_comparables_resolver_test', SRC)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mc(mc_module, monkeypatch):
    monkeypatch.setattr(mc_module, 'MASTER_COMPARABLES', [])
    monkeypatch.setattr(mc_module, 'SIZE_SIMILARITY_BAND', 0.50)
    monkeypatch.setattr(mc_module, 'DISTANCE_COMPARISON_ENABLED', False)
    return mc_module


def comp(name, nfa, district='Quan Alpha', city='Thanh pho X', rate=None, rates=None):
    return dict(name=name, nfa=nfa, district=district, city=city, mgmt_rate=rate,
                mgmt_rate_vat='incl_VAT', rates=rates if rates is not None else {'Apartment': rate})


def project(products, name='ZZ Invented Tower', district='Quan Alpha', city='Thanh pho X'):
    prods = {p: dict(gfa=0, nfa=nfa, units=0) for p, nfa in products.items()}
    return dict(name=name, district=district, city=city, lat=None, lon=None, products=prods,
                total_nfa=sum(v['nfa'] for v in prods.values()))


POOL = [
    comp('Tower A', 50_000, rate=15_000, rates={'Apartment': 15_000, 'Shophouse': 40_000}),
    comp('Tower B', 60_000, rate=17_000, rates={'Apartment': 17_000}),
    comp('Tower C', 90_000, rate=20_000, rates={'Apartment': 20_000, 'Shophouse': 50_000}),
]


def test_apartment_rate_is_the_capped_comparable_rate(mc, monkeypatch):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', POOL)
    p = project({'Apartment': 50_000})
    res = mc.resolve_product_rates(p)
    rate, used, note, all_ranked = mc.derive_product_rate_capped(
        p['total_nfa'], p['name'], 'Apartment', input_district='Quan Alpha', input_city='Thanh pho X')
    assert res['apartment_rate'] == rate == 16_000
    assert res['apartment_source'] == 'comparable'
    assert [c['name'] for c in res['comparables']] == [c['name'] for c in used]
    assert res['apartment_used'] == used
    assert res['rate_note'] == note
    assert [c['name'] for c in res['all_ranked']] == [c['name'] for c in all_ranked]
    apt = res['products']['Apartment']
    assert (apt['rate'], apt['source'], apt['is_fallback']) == (16_000, 'comparable', False)


def test_other_product_with_a_comparable_rate_uses_it_uncapped(mc, monkeypatch):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', POOL)
    p = project({'Apartment': 50_000, 'Shophouse': 2_000})
    res = mc.resolve_product_rates(p)
    expected, used, note = mc.derive_product_rate(res['all_ranked'], 'Shophouse', n=2)
    shop = res['products']['Shophouse']
    assert shop['rate'] == expected == 45_000
    assert shop['used'] == used and shop['note'] == note
    assert (shop['source'], shop['is_fallback']) == ('comparable', False)


def test_other_product_without_a_comparable_rate_falls_back_to_apartment(mc, monkeypatch):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', POOL)
    res = mc.resolve_product_rates(project({'Apartment': 50_000, 'Officetel': 900}))
    off = res['products']['Officetel']
    assert off['rate'] == res['apartment_rate']
    assert (off['source'], off['is_fallback'], off['used']) == ('apartment-fallback', True, [])


def test_a_product_without_area_is_not_priced(mc, monkeypatch):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', POOL)
    res = mc.resolve_product_rates(project({'Apartment': 50_000, 'Shophouse': 0, 'Villas': 0}))
    assert list(res['products']) == ['Apartment']


def test_blended_fallback_when_no_comparable_has_an_apartment_rate(mc, monkeypatch):
    pool = [comp('Tower D', 50_000, rate=14_000, rates={}),
            comp('Tower E', 55_000, rate=18_000, rates={}),
            comp('Tower F', 80_000, rate=30_000, rates={})]
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', pool)
    p = project({'Apartment': 50_000, 'Officetel': 500})
    res = mc.resolve_product_rates(p)
    top2 = mc.nearest_comparables(p['total_nfa'], exclude_name=p['name'], n=2,
                                  input_district='Quan Alpha', input_city='Thanh pho X')
    blended, _ = mc.derive_mgmt_rate(top2, all_ranked=res['all_ranked'])
    assert res['apartment_rate'] == blended == 16_000
    assert res['apartment_source'] == 'blended-fallback'
    assert res['apartment_used'] == []
    assert [c['name'] for c in res['comparables']] == [c['name'] for c in top2]
    assert res['rate_note'].endswith(
        'No comparable has a real Apartment rate — fell back to the whole-property blended rate.')
    assert res['products']['Officetel']['rate'] == 16_000


def test_no_rate_anywhere_stops(mc, monkeypatch):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', [comp('Tower G', 50_000, rate=None, rates={})])
    with pytest.raises(ValueError, match='Could not derive a management-fee rate'):
        mc.resolve_product_rates(project({'Apartment': 50_000}))


def test_project_location_and_size_reach_the_capped_call(mc, monkeypatch):
    seen = {}

    def spy(project_nfa, exclude_name, product, **kw):
        seen.update(project_nfa=project_nfa, exclude_name=exclude_name, product=product, **kw)
        return 12_345, [], None, []

    monkeypatch.setattr(mc, 'derive_product_rate_capped', spy)
    p = project({'Apartment': 40_000, 'Shophouse': 1_000})
    p.update(lat=10.5, lon=106.5)
    res = mc.resolve_product_rates(p)
    assert res['apartment_rate'] == 12_345
    assert seen == dict(project_nfa=41_000, exclude_name='ZZ Invented Tower', product='Apartment',
                        input_district='Quan Alpha', input_city='Thanh pho X',
                        input_lat=10.5, input_lon=106.5)


# ---------------------------------------------------------------- P1: an entered rate wins

def entered(p, **rates):
    """Attach entered rates as read_input() does (project['operating']['rates'])."""
    p['operating'] = dict(rates={k.replace('_', ' '): dict(rate=v[0], vat=v[1]) for k, v in rates.items()})
    return p


def test_entered_apartment_rate_is_applied_uncapped(mc, monkeypatch):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', POOL)
    plain = mc.resolve_product_rates(project({'Apartment': 50_000}))
    res = mc.resolve_product_rates(entered(project({'Apartment': 50_000}), Apartment=(40_000, 'excl. VAT')))
    # far outside any swing cap around the comparable-derived 16,000: applied unchanged
    assert res['apartment_rate'] == 40_000 and res['apartment_source'] == 'entered'
    apt = res['products']['Apartment']
    assert (apt['rate'], apt['source'], apt['vat'], apt['used']) == (40_000, 'entered', 'excl. VAT', [])
    assert apt['comparable_rate'] == res['apartment_comparable_rate'] == plain['apartment_rate']
    assert res['comparables'] == plain['comparables']          # the Comparison sheet keeps them
    assert res['apartment_entered'] == dict(rate=40_000, vat='excl. VAT')


def test_fallback_product_follows_the_entered_apartment_rate(mc, monkeypatch):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', POOL)
    res = mc.resolve_product_rates(entered(project({'Apartment': 50_000, 'Villas': 2_000}),
                                           Apartment=(21_000, 'incl. VAT')))
    villas = res['products']['Villas']
    assert (villas['rate'], villas['source'], villas['is_fallback']) == (21_000, 'apartment-fallback', True)


def test_product_with_its_own_comparable_is_unchanged_by_another_entered_rate(mc, monkeypatch):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', POOL)
    plain = mc.resolve_product_rates(project({'Apartment': 50_000, 'Shophouse': 1_000}))
    res = mc.resolve_product_rates(entered(project({'Apartment': 50_000, 'Shophouse': 1_000}),
                                           Apartment=(21_000, 'incl. VAT')))
    assert res['products']['Shophouse']['rate'] == plain['products']['Shophouse']['rate']
    assert res['products']['Shophouse']['source'] == 'comparable'


def test_entered_non_apartment_rate_keeps_its_comparable_for_reference(mc, monkeypatch):
    monkeypatch.setattr(mc, 'MASTER_COMPARABLES', POOL)
    plain = mc.resolve_product_rates(project({'Apartment': 50_000, 'Shophouse': 1_000}))
    res = mc.resolve_product_rates(entered(project({'Apartment': 50_000, 'Shophouse': 1_000}),
                                           Shophouse=(99_000, 'incl. VAT')))
    sh = res['products']['Shophouse']
    assert (sh['rate'], sh['source'], sh['comparable_rate']) == (99_000, 'entered',
                                                                  plain['products']['Shophouse']['rate'])
    assert res['apartment_rate'] == plain['apartment_rate'] and res['apartment_entered'] is None
