-- ============================================================================================
-- Full budget estimate for a NEW project — SQL equivalent of estimate_new_project.py.
-- Four components, four different real datasets, four different sample sizes — kept separate,
-- never blended into one confidence number. Parameters to replace before running:
--   @new_project_name         text   -- excludes itself if it happens to match a real comparable
--   @new_project_total_gfa    number -- whole-building GFA (m²) -- drives Staff and Capex
--   @new_project_apartment_nfa number -- apartment-only NFA (m²) -- drives Management Fee
--   @new_project_real_headcount number, nullable -- pass NULL if the roster doesn't exist yet
-- ============================================================================================

-- ============================================================================================
-- 1. MANAGEMENT FEE — master_comparables.py's nearest_comparables() + derive_mgmt_rate(), as SQL.
--    Source: the 7-project MASTER_COMPARABLES table (hand-verified real rates this session).
-- ============================================================================================
WITH Dim_Comparables (ProjectName, ApartmentNFA_m2, MgmtFeeRate, MgmtFeeVAT) AS (
    VALUES
        ('11D Thi Sach',                13936.10, NULL,    NULL),
        ('A&K Tower',                   59285.70, NULL,    NULL),
        ('Lumi Prestige & Elite',      122571.00, 21000.0, 'excl_VAT'),
        ('Lumi Signature',             181662.20, 17000.0, 'excl_VAT'),
        ('Green Skyline',               81281.06, 15000.0, 'incl_VAT'),
        ('Fiato Airport - F Zone G2',   25935.64, NULL,    NULL),
        ('Fiato Airport - F Zone MF Pre/Y1/Y2', 25935.64, 18000.0, 'excl_VAT')
),
RankedComparables AS (
    SELECT
        ProjectName, ApartmentNFA_m2, MgmtFeeRate,
        ABS(ApartmentNFA_m2 - @new_project_apartment_nfa)                    AS NfaDelta,
        ROW_NUMBER() OVER (ORDER BY ABS(ApartmentNFA_m2 - @new_project_apartment_nfa)) AS Rank
    FROM Dim_Comparables
    WHERE ProjectName <> @new_project_name   -- exact match; the Python version uses substring
                                               -- containment for "New Prospect (X)"-style names
),
Top2Comparables AS (
    SELECT * FROM RankedComparables WHERE Rank <= 2
),
DerivedRate AS (
    -- Average of whichever of the top 2 have a real rate. If both are blank, this returns no
    -- rows -- the Python version's fallback-to-3rd-nearest is a deliberate extra step not
    -- reproduced here for brevity; see derive_mgmt_rate() in master_comparables.py.
    SELECT AVG(MgmtFeeRate) AS DerivedRate, COUNT(MgmtFeeRate) AS RatedComparableCount
    FROM Top2Comparables
    WHERE MgmtFeeRate IS NOT NULL
),
ManagementFeeResult AS (
    SELECT
        d.DerivedRate,
        d.RatedComparableCount,
        d.DerivedRate * @new_project_apartment_nfa            AS MonthlyRevenue,
        d.DerivedRate * @new_project_apartment_nfa * 12        AS AnnualRevenue
    FROM DerivedRate d
),

-- ============================================================================================
-- 2. STAFF — headcount from the Master List's real headcount-per-GFA distribution (bucketed:
--    bigger buildings need proportionally fewer staff/m² -- a real, measured effect), then ×
--    real median cost-per-headcount. Both ratios computed here directly from the source CSVs
--    (loaded as tables) rather than hardcoded, so this stays live if the Master List refreshes.
-- ============================================================================================
StaffPopulation AS (
    SELECT GFA_m2, Headcount, StaffCost
    FROM Dim_Property_Residential          -- data/master_list_verified/Dim_Property_Residential.csv
    WHERE GFA_m2 IS NOT NULL AND Headcount IS NOT NULL AND GFA_m2 > 0
),
SizeBucketed AS (
    SELECT
        *,
        Headcount / (GFA_m2 / 1000.0) AS HeadcountPer1000sqm,
        CASE
            WHEN GFA_m2 < 30000  THEN '<30k'
            WHEN GFA_m2 < 80000  THEN '30k-80k'
            WHEN GFA_m2 < 150000 THEN '80k-150k'
            ELSE '>150k'
        END AS SizeBucket
    FROM StaffPopulation
),
BucketRatio AS (
    SELECT
        SizeBucket, COUNT(*) AS N,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY HeadcountPer1000sqm) AS MedianHeadcountPer1000sqm
    FROM SizeBucketed
    GROUP BY SizeBucket
),
CostPerHeadcountRatio AS (
    SELECT
        COUNT(*) AS N,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY StaffCost / NULLIF(Headcount, 0)) AS MedianCostPerHeadcount
    FROM StaffPopulation
    WHERE Headcount > 0
),
NewProjectBucket AS (
    SELECT CASE
        WHEN @new_project_total_gfa < 30000  THEN '<30k'
        WHEN @new_project_total_gfa < 80000  THEN '30k-80k'
        WHEN @new_project_total_gfa < 150000 THEN '80k-150k'
        ELSE '>150k'
    END AS SizeBucket
),
StaffResult AS (
    SELECT
        COALESCE(@new_project_real_headcount,
                 ROUND(@new_project_total_gfa / 1000.0 * br.MedianHeadcountPer1000sqm))       AS EstimatedHeadcount,
        CASE WHEN @new_project_real_headcount IS NOT NULL THEN 'real (given)' ELSE 'estimated from GFA' END AS HeadcountSource,
        br.N                                                                                   AS HeadcountRatio_N,
        cph.MedianCostPerHeadcount,
        cph.N                                                                                  AS CostRatio_N
    FROM NewProjectBucket npb
    JOIN BucketRatio br ON br.SizeBucket = npb.SizeBucket
    CROSS JOIN CostPerHeadcountRatio cph
),

-- ============================================================================================
-- 3. SERVICE — flat citywide reference rates (Fact_MasterRateCard.csv, Domain='Service'). Same
--    number for every project; not a sample, a citywide card, so no ratio/N to report.
-- ============================================================================================
ServiceResult AS (
    SELECT
        MAX(CASE WHEN Category = 'Security'  THEN UnitPrice END) AS SecurityRate,
        MAX(CASE WHEN Category = 'Cleaning'  THEN UnitPrice END) AS CleaningRate,
        MAX(CASE WHEN Category = 'Landscape' THEN UnitPrice END) AS LandscapeRate
    FROM Fact_MasterRateCard
    WHERE Domain = 'Service' AND (Item LIKE '%24/24 position%' OR Item LIKE '%8/24 position%')
),

-- ============================================================================================
-- 4. CAPEX — real Qty ÷ verified NFA (Study 1, n=5-6/category) and Qty ÷ headcount (Study 2,
--    n=1, Green Skyline only) — see estimate_capex_qty.sql for the full derivation; ratios
--    inlined here as constants since they're small, hand-verified tables, not worth re-deriving
--    in every query that needs them. Sourced from Fact_Capex_Rescanned (rescan_capex_from_source.py),
--    NOT the original Fact_Capex — that table read the wrong quantity column on 7 of the 8 real
--    files and never captured the 4th category (Amenity Area) at all; see estimate_capex_qty.py's
--    docstring for the full bug list.
-- ============================================================================================
Study1CapexRatio (CapexCategory, MedianQtyPer1000sqmNFA, N) AS (
    VALUES ('M&E Equipment', 2.054, 6), ('MO Equipment', 1.007, 6), ('Public Area', 2.272, 6), ('Amenity Area', 0.091, 5)
),
Study2CapexRatio (CapexCategory, QtyPerHeadcount, N) AS (
    VALUES ('M&E Equipment', 7.286, 1), ('MO Equipment', 4.143, 1), ('Public Area', 8.429, 1), ('Amenity Area', 0.429, 1)
),
CapexResult AS (
    SELECT
        s1.CapexCategory,
        s1.N                                                                    AS Study1_N,
        ROUND(@new_project_total_gfa / 1000.0 * s1.MedianQtyPer1000sqmNFA, 1)   AS Study1_EstimatedQty,
        s2.N                                                                    AS Study2_N,
        ROUND(sr.EstimatedHeadcount * s2.QtyPerHeadcount, 1)                    AS Study2_CrossCheckQty
    FROM Study1CapexRatio s1
    JOIN Study2CapexRatio s2 ON s2.CapexCategory = s1.CapexCategory
    CROSS JOIN StaffResult sr    -- Capex's headcount cross-check uses Staff's own estimate above
)

-- ============================================================================================
-- Final combined output — one row per component, so the four different N's stay visible instead
-- of collapsing into a single number. Run as 4 separate SELECTs (below) or UNION ALL into one
-- result set if your tooling wants a single table.
-- ============================================================================================
SELECT 'Management Fee' AS Component, DerivedRate AS PrimaryValue, RatedComparableCount AS N,
       AnnualRevenue AS SecondaryValue
FROM ManagementFeeResult
UNION ALL
SELECT 'Staff (annual cost)', MedianCostPerHeadcount, CostRatio_N,
       EstimatedHeadcount * MedianCostPerHeadcount * 12
FROM StaffResult
UNION ALL
SELECT 'Service (annual, citywide)', SecurityRate + CleaningRate + LandscapeRate, NULL,
       (SecurityRate + CleaningRate + LandscapeRate) * 12
FROM ServiceResult
UNION ALL
SELECT 'Capex — ' || CapexCategory, Study1_EstimatedQty, Study1_N, Study2_CrossCheckQty
FROM CapexResult;
