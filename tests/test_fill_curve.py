"""Unit tests for fill_curve.py (the monthly fill-up ramp shared by both generators).

Covered: _fill_at, monthly_fill_path, year1_fills, year1_electricity_fills, parking_fills.
Not covered: how the generators use the curve (see the verification suite).

Invented data only (the curve itself is a disclosed assumption, no client data involved).

Rule sources: openspec/specs/occupancy-ramp/spec.md (floor at zero occupancy, full load by the
threshold, never above full), docs/05-decisions.md (0% at start, about 50% at end of year 1, parking
about 2x faster where bays are fewer than units), module docstring (anchors 50/70/90/100% at months
12/24/36/48, linear between). The exact 0.40 floor/threshold and the 2x factor are stated in code
comments only.
"""
import pytest

import fill_curve as fc


# ---------------------------------------------------------------- _fill_at

@pytest.mark.parametrize('month, fill', [
    (12, 0.50), (24, 0.70), (36, 0.90), (48, 1.00),     # the anchors
    (6, 0.25), (18, 0.60), (30, 0.80), (42, 0.95),      # halfway between anchors
    (1, 0.5 / 12),                                      # first operating month
    (13, 0.5 + 0.2 / 12),
])
def test_fill_at_follows_the_anchors_linearly(month, fill):
    assert fc._fill_at(month) == pytest.approx(fill)


@pytest.mark.parametrize('month', [49, 60, 120])
def test_fill_stays_at_100_percent_after_the_last_anchor(month):
    assert fc._fill_at(month) == 1.0


def test_fill_is_non_decreasing_and_within_0_and_1():
    values = [fc._fill_at(m) for m in range(1, 61)]
    assert all(0.0 <= v <= 1.0 for v in values)
    assert all(b >= a for a, b in zip(values, values[1:]))


@pytest.mark.xfail(strict=True, reason="possible defect: _fill_at(0) returns 1.0 (the loop's m0 < month "
                   "excludes 0, so it falls through to the last anchor) while the module docstring says "
                   "the curve starts at 0% at month 0. Low impact: callers only pass months 1..48.")
def test_fill_at_month_zero_is_zero():
    # rule source: module docstring ("starting from 0% at month 0")
    assert fc._fill_at(0) == 0.0


def test_fill_at_uses_the_module_anchors(monkeypatch):
    monkeypatch.setattr(fc, 'MONTH_ANCHORS', [(0, 0.0), (10, 1.0)])
    assert fc._fill_at(5) == pytest.approx(0.5)
    assert fc._fill_at(11) == 1.0


# ---------------------------------------------------------------- monthly_fill_path

def test_monthly_fill_path_has_48_labelled_rows():
    path = fc.monthly_fill_path()
    assert len(path) == 48
    assert path[0][:2] == (1, 'Y1 M1')
    assert path[11][:2] == (12, 'Y1 M12')
    assert path[12][:2] == (13, 'Y2 M1')
    assert path[47][:2] == (48, 'Y4 M12')
    assert path[11][2] == pytest.approx(0.5) and path[47][2] == 1.0


# ---------------------------------------------------------------- year1_fills

def test_year1_fills_is_twelve_rising_values_ending_at_half():
    fills = fc.year1_fills()
    assert len(fills) == 12
    assert fills[0] == pytest.approx(0.0417, abs=1e-4)       # docstring: about 0.042 in month 1
    assert fills[-1] == pytest.approx(0.50)
    assert all(b > a for a, b in zip(fills, fills[1:]))


# ---------------------------------------------------------------- year1_electricity_fills

def test_electricity_never_below_the_floor_and_never_above_full():
    # rule source: occupancy-ramp spec (floor requirement)
    values = fc.year1_electricity_fills()
    assert len(values) == 12
    assert all(fc.ELECTRICITY_FLOOR <= v <= 1.0 for v in values)


def test_electricity_early_months_sit_on_the_floor():
    values = fc.year1_electricity_fills()
    assert values[0] == fc.ELECTRICITY_FLOOR == 0.40


def test_electricity_reaches_full_once_fill_reaches_the_threshold():
    # rule source: occupancy-ramp spec; the 40% threshold is stated in a code comment only.
    # Fill is 9/24 = 37.5% in month 9 (below) and 10/24 = 41.7% in month 10 (above).
    fills, values = fc.year1_fills(), fc.year1_electricity_fills()
    assert fills[8] < fc.ELECTRICITY_FULL_AT <= fills[9]
    assert values[8] < 1.0
    assert values[9] == values[10] == values[11] == 1.0


def test_electricity_between_floor_and_full_is_fill_over_threshold():
    # rule source: function docstring only (fill fraction scaled so the threshold maps to full)
    values = fc.year1_electricity_fills()
    assert values[8] == pytest.approx((9 / 24) / 0.40)       # month 9
    assert values[3] == pytest.approx((4 / 24) / 0.40)       # month 4, first month above the floor


def test_electricity_follows_patched_floor_and_threshold(monkeypatch):
    monkeypatch.setattr(fc, 'MONTH_ANCHORS', [(0, 0.0), (12, 0.5)])
    monkeypatch.setattr(fc, 'ELECTRICITY_FLOOR', 0.7)
    monkeypatch.setattr(fc, 'ELECTRICITY_FULL_AT', 0.25)
    values = fc.year1_electricity_fills()
    assert values[0] == 0.7                                   # fill 4.2% -> 16.7% of full, floored at 0.7
    assert values[4] == pytest.approx(0.8333, abs=1e-3)       # month 5: 20.8% / 25%
    assert values[5] == 1.0                                   # month 6: exactly at the threshold


# ---------------------------------------------------------------- parking_fills

def test_parking_equal_bays_and_units_tracks_resident_fill():
    assert fc.parking_fills(100, 100) == fc.year1_fills()


def test_parking_more_bays_than_units_tracks_resident_fill():
    assert fc.parking_fills(150, 100) == fc.year1_fills()


def test_parking_fewer_bays_than_units_fills_twice_as_fast():
    # rule source: docs/05-decisions.md ("roughly 2x faster where parking bays are fewer than units")
    got, base = fc.parking_fills(60, 100), fc.year1_fills()
    assert got == pytest.approx([2 * f for f in base])
    assert len(got) == 12


@pytest.mark.parametrize('bays, units', [(0, 100), (None, 100), (100, 0), (100, None), (None, None), (0, 0)])
def test_parking_blank_or_zero_counts_get_the_normal_curve(bays, units):
    # rule source: code comment only (a missing count is not treated as a shortage); not settled: blank counts
    assert fc.parking_fills(bays, units) == fc.year1_fills()


def test_parking_fill_is_capped_at_100_percent(monkeypatch):
    monkeypatch.setattr(fc, 'MONTH_ANCHORS', [(0, 0.0), (12, 0.8), (24, 1.0)])
    got = fc.parking_fills(10, 100)
    assert max(got) == 1.0
    assert got[5] == pytest.approx(0.8)          # month 6: 0.4 x 2, below the cap
    assert got[11] == 1.0                        # month 12: 0.8 x 2 = 1.6, capped
    assert all(v <= 1.0 for v in got)


def test_parking_default_curve_reaches_exactly_100_percent_in_month_12():
    assert fc.parking_fills(10, 100)[11] == pytest.approx(1.0)
