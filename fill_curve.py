"""The single monthly fill-up curve, shared by both generators.

A new building does not open full. Occupancy rises across the first years, and revenue that is
collected per occupied unit — plus the utility load — rises with it. This module is the one place
that curve is defined, so `generate_project_budget.py` (the client deliverable) and
`generate_project_output.py` (the internal analysis) ramp identically for the same project.

The curve is a **disclosed assumption, not real data**: linear interpolation between fixed
year-end anchors, starting from 0% at month 0. Flat per-year averages understate how empty the
early months really are (a building does not jump to 50% fill on day one), so month-level
resolution matters. Anchors: 50% by end of year 1, 70% year 2, 90% year 3, 100% year 4 — inside
the ranges the Savills AI Guideline states for a typical residential ramp.

Making the curve a per-project intake field is a deliberate later step (see the change family in
docs/08). Until then every figure distributed by it carries a remark saying so.
"""

# (month_offset, cumulative fill fraction). month 0 = handover start.
MONTH_ANCHORS = [(0, 0.0), (12, 0.50), (24, 0.70), (36, 0.90), (48, 1.00)]

# Electricity does not fall below this fraction of full load even in a near-empty building
# (lifts, pumps, common-area lighting, fire systems all run regardless), and it reaches full load
# once the building is this full — not only at 100%. Both from the guideline's stated behaviour
# for the electricity line.
ELECTRICITY_FLOOR = 0.40
ELECTRICITY_FULL_AT = 0.40

# A project already at stable operation (change use-operating-project-actuals, P3): the intake
# form's 'Stable Operation?' switch replaces the curve with this fill in every month. 100% is the
# answer recorded for PM-4 on 2026-10-11; an entered stable occupancy would change only this value.
STABLE_FILL = 1.0


def _fill_at(month):
    """Interpolated fill fraction at an absolute operational month (1-based)."""
    for (m0, f0), (m1, f1) in zip(MONTH_ANCHORS, MONTH_ANCHORS[1:]):
        if m0 < month <= m1:
            return f0 + (f1 - f0) * (month - m0) / (m1 - m0)
    return MONTH_ANCHORS[-1][1]


def monthly_fill_path(stable=False):
    """48 rows of (absolute month, 'Y<n> M<m>' label, fill fraction) — the multi-year view the
    internal analysis uses. Moved here verbatim from generate_project_output.py. With `stable`,
    every month is STABLE_FILL."""
    path = []
    for month in range(1, 49):
        fill = STABLE_FILL if stable else _fill_at(month)
        year_num = (month - 1) // 12 + 1
        month_in_year = (month - 1) % 12 + 1
        path.append((month, f'Y{year_num} M{month_in_year}', fill))
    return path


def year1_fills(stable=False):
    """The 12 fill fractions for operational months 1..12 — what the single-year client deliverable
    ramps its occupancy-scaled lines by. Rises from ~0.042 (month 1) to 0.50 (month 12); with
    `stable`, STABLE_FILL in every month."""
    if stable:
        return [STABLE_FILL] * 12
    return [_fill_at(m) for m in range(1, 13)]


def year1_electricity_fills(stable=False):
    """The 12 fractions to apply to full monthly electricity: the fill fraction, floored at
    ELECTRICITY_FLOOR and clamped to full once occupancy reaches ELECTRICITY_FULL_AT. With `stable`,
    full load (1.0) in every month."""
    if stable:
        return [1.0] * 12
    return [max(ELECTRICITY_FLOOR, min(1.0, f / ELECTRICITY_FULL_AT)) for f in year1_fills()]


def parking_fills(bays, units, stable=False):
    """The 12 parking fill fractions for a vehicle type. Parking fill tracks resident fill, but
    ~2x faster where the bay count is below the unit count (residents who cannot park on site give
    up sooner), capped at 100%. With `stable`, STABLE_FILL in every month."""
    if stable:
        return [STABLE_FILL] * 12
    k = 2.0 if (bays and units and bays < units) else 1.0
    return [min(1.0, f * k) for f in year1_fills()]
