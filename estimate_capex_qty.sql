-- ============================================================================================
-- Capex Qty estimation for a NEW project — SQL equivalent of estimate_capex_qty.py.
-- Source table: Fact_Capex_Rescanned (data/generation_A_star_schema/Fact_Capex_Rescanned.csv,
-- loaded as a table — columns Project, Category, Item, Unit, Qty, UnitPrice, Total, SourceSheet,
-- SourceRow). Written against ANSI SQL / PERCENTILE_CONT, which Fabric Warehouse, Snowflake,
-- BigQuery, Postgres, and SQL Server all support; swap the median expression if your engine
-- doesn't (e.g. SQL Server 2016- needs PERCENTILE_CONT(...) OVER (...) instead of WITHIN GROUP +
-- a separate GROUP BY — see the note above Study1Ratio below).
--
-- REVISED: this query originally read Fact_Capex.csv (Generation A's star-schema extraction)
-- directly, via a Fact_Capex/Dim_Equipment/Dim_Project join. That table had real bugs — 7 of the
-- 8 real files lay out their Capex sheets with 3 sub-quantity columns (Required/Standard/
-- Optional) before the TRUE total Quantity column, and the ETL read the wrong one; it also
-- double-counted section-header rows as line items, and never extracted a 4th sheet category at
-- all ("Capex khu tiện ích" / Amenity Area). rescan_capex_from_source.py re-extracts directly
-- from source with a column-detector that finds "Unit Price" by text and takes Quantity/Total as
-- the columns immediately left/right of it — true in every layout seen. Fact_Capex_Rescanned is
-- already deduped (one row per real project, no '__repaired' copies) and already excludes
-- contingency-fee rows (their Quantity column held a VND amount, not a real item count — the row
-- that first surfaced this whole investigation), so this query is simpler than the original.
--
-- THE LOGIC — same two studies, same reasoning, as estimate_capex_qty.py:
--   Study 1 (primary): real Capex quantities ÷ each project's VERIFIED TotalNFA (NOT any
--   TotalNFA the star schema might supply — Generation A's own Dim_Project.NFA_m2 is broken for
--   several projects, sharing an identical placeholder value of 59865.9 across three unrelated
--   ones — see Dim_Property_Verified below). Median ratio per category, applied to the new
--   project's own TotalNFA.
--   Study 2 (cross-check only, never blended into Study 1): the same real quantities ÷ headcount,
--   but only Green Skyline overlaps both the old files and the new Master List with a real
--   headcount — n=1, carried through to the final output explicitly rather than hidden in an
--   average.
-- ============================================================================================

-- Verified TotalNFA per real project, hand-read from each project's own Info sheet this session.
WITH Dim_Property_Verified (ProjectName, TotalNFA_m2) AS (
    VALUES
        ('11D Thi Sach',               16783.14),
        ('A&K Tower',                  64124.00),
        ('Lumi Prestige',             134117.40),
        ('Lumi Signature',            195269.50),
        ('Green Skyline',              99252.45),
        ('Fiato Airport - F Zone G2',  35836.27)
),

CleanCapex AS (
    SELECT Project AS ProjectName, Category AS CapexCategory, Qty AS Quantity
    FROM Fact_Capex_Rescanned
    WHERE Qty IS NOT NULL
),

-- Per-project, per-category real ratio: total observed Qty ÷ that project's verified NFA (/1000).
Study1Base AS (
    SELECT
        c.CapexCategory,
        v.ProjectName,
        SUM(c.Quantity)                              AS TotalQty,
        v.TotalNFA_m2,
        SUM(c.Quantity) / (v.TotalNFA_m2 / 1000.0)    AS QtyPer1000sqmNFA
    FROM CleanCapex c
    JOIN Dim_Property_Verified v ON v.ProjectName = c.ProjectName
    GROUP BY c.CapexCategory, v.ProjectName, v.TotalNFA_m2
),

-- Study 1 ratio: median (not mean — a handful of real projects means one outlier would otherwise
-- swing the whole estimate) Qty per 1,000 m² NFA, by category. N varies by category because not
-- every old project has both real capex data AND a verified NFA for every category — reported
-- explicitly, not padded to look like a bigger sample than it is.
Study1Ratio AS (
    SELECT
        CapexCategory,
        COUNT(*)                                                          AS N,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY QtyPer1000sqmNFA)     AS MedianQtyPer1000sqmNFA,
        MIN(QtyPer1000sqmNFA)                                             AS MinRatio,
        MAX(QtyPer1000sqmNFA)                                             AS MaxRatio
    FROM Study1Base
    GROUP BY CapexCategory
),

-- Study 2: Qty per Headcount, Green Skyline only (n=1 — the ONE old project with a real headcount
-- in the new Master List; 21 staff, read from data/master_list_verified/Dim_Property_Residential.csv).
Study2Ratio AS (
    SELECT
        CapexCategory,
        SUM(Quantity) / 21.0   AS QtyPerHeadcount,
        1                      AS N
    FROM CleanCapex
    WHERE ProjectName = 'Green Skyline'
    GROUP BY CapexCategory
)

-- ============================================================================================
-- Final estimate for a NEW project. Replace @new_project_nfa (required) and
-- @new_project_headcount (optional — pass NULL if not yet known; Study2 columns come back NULL
-- too, which is correct, not an error) with the prospect's own values.
-- ============================================================================================
SELECT
    s1.CapexCategory,
    s1.N                                                                AS Study1_N,
    ROUND(@new_project_nfa / 1000.0 * s1.MedianQtyPer1000sqmNFA, 1)     AS Study1_EstimatedQty,
    s1.MinRatio,
    s1.MaxRatio,
    s2.N                                                                AS Study2_N,
    ROUND(@new_project_headcount * s2.QtyPerHeadcount, 1)               AS Study2_CrossCheckQty
FROM Study1Ratio s1
LEFT JOIN Study2Ratio s2 ON s2.CapexCategory = s1.CapexCategory
ORDER BY s1.CapexCategory;
