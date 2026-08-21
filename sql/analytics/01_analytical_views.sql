-- =============================================================================
-- STEP 1 + 18: Analytical Data Model & SQL Analytics
-- =============================================================================
-- Purpose: Create analytical views and queries for workforce intelligence
-- Grain: Each view documents its analytical grain explicitly
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 01: ENRICHED JOB FACT TABLE
-- Grain: 1 row = 1 unique job posting
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_analytical_jobs AS
SELECT
    j.job_id,
    j.job_title,
    jt.normalized_title,
    jt.role_category,
    jt.seniority,
    c.name              AS company_name,
    l.city,
    l.region,
    l.country           AS country_code,
    CASE
        WHEN l.country = 'GB' AND l.city = 'London' THEN 'London'
        WHEN l.country = 'GB' AND l.city IN (
            'The City','Farringdon','Blackfriars','Charing Cross',
            'South West London','South East London','West London',
            'Central London','Kings Cross','Liverpool Street',
            'Tower Bridge','Victoria','Monument','Fenchurch St',
            'Uxbridge','Enfield','Greenwich','Islington','Westminster',
            'City of London','Canary Wharf','Shoreditch','Soho',
            'Mayfair','Covent Garden','Holborn','Bloomsbury',
            'Marylebone','Paddington','Knightsbridge','Chelsea',
            'Fulham','Brixton','Hackney','Lambeth','Southwark',
            'Camden','Hammersmith','Richmond','Kingston',
            'Croydon','Bromley','Bexley','Havering','Harrow',
            'Barnet','Ealing','Hounslow','Redbridge','Waltham Forest',
            'Newham','Tower Hamlets','Lewisham','Greenwich','Merton',
            'Sutton','Kingston','Hillingdon','Brent','Haringey',
            'Enfield','Havering','Barking and Dagenham','Bexley'
        ) THEN 'Greater London'
        WHEN l.country = 'GB' THEN 'UK Other'
        WHEN l.country = 'PK' AND l.city = 'Lahore' THEN 'Lahore'
        WHEN l.country = 'PK' AND l.city = 'Islamabad' THEN 'Islamabad'
        WHEN l.country = 'PK' AND l.city = 'Karachi' THEN 'Karachi'
        WHEN l.country = 'PK' THEN 'Pakistan Other'
        ELSE 'Unknown'
    END AS location_group,
    j.salary_min,
    j.salary_max,
    j.salary_currency,
    j.salary_period,
    j.salary_type,
    j.employment_type,
    j.work_mode,
    j.experience_level,
    j.education_requirement,
    j.posting_date,
    j.collected_at,
    j.dq_score,
    js.name             AS source_name,
    -- Derived fields
    CASE WHEN j.salary_min IS NOT NULL OR j.salary_max IS NOT NULL
         THEN true ELSE false END AS has_salary,
    CASE WHEN j.salary_min IS NOT NULL AND j.salary_max IS NOT NULL
         THEN (j.salary_min + j.salary_max) / 2.0
         WHEN j.salary_min IS NOT NULL THEN j.salary_min
         WHEN j.salary_max IS NOT NULL THEN j.salary_max
         ELSE NULL END AS salary_midpoint,
    -- Temporal fields
    CASE
        WHEN js.name = 'adzuna_uk' THEN 'Recent UK (2023-2026)'
        WHEN js.name = 'chisel_pk' THEN 'Historical PK (2019-2021)'
        WHEN js.name = 'kaggle_rozee_pk' THEN 'Supplementary PK'
        ELSE 'Unknown'
    END AS dataset_period
FROM jobs j
LEFT JOIN job_titles jt   ON j.title_id    = jt.title_id
LEFT JOIN companies c     ON j.company_id  = c.company_id
LEFT JOIN locations l     ON j.location_id = l.location_id
LEFT JOIN job_sources js  ON j.source_id   = js.source_id;

-- ---------------------------------------------------------------------------
-- 02: MARKET OVERVIEW
-- Grain: 1 row = 1 country/source combination
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_market_overview AS
SELECT
    country_code,
    source_name,
    dataset_period,
    COUNT(*) AS total_jobs,
    COUNT(*) FILTER (WHERE has_salary) AS jobs_with_salary,
    ROUND(100.0 * COUNT(*) FILTER (WHERE has_salary) / NULLIF(COUNT(*), 0), 1) AS salary_coverage_pct,
    COUNT(*) FILTER (WHERE work_mode = 'remote') AS remote_jobs,
    COUNT(*) FILTER (WHERE work_mode = 'hybrid') AS hybrid_jobs,
    COUNT(*) FILTER (WHERE work_mode = 'on_site') AS on_site_jobs,
    COUNT(DISTINCT company_name) AS unique_companies,
    COUNT(DISTINCT city) AS unique_cities,
    ROUND(AVG(dq_score), 1) AS avg_dq_score
FROM v_analytical_jobs
GROUP BY country_code, source_name, dataset_period;

-- ---------------------------------------------------------------------------
-- 03: ROLE DEMAND ANALYSIS
-- Grain: 1 row = 1 role/country combination
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_role_demand AS
SELECT
    role_category,
    country_code,
    dataset_period,
    COUNT(*) AS job_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY country_code), 1) AS pct_within_country,
    COUNT(*) FILTER (WHERE seniority = 'junior') AS junior_count,
    COUNT(*) FILTER (WHERE seniority = 'mid') AS mid_count,
    COUNT(*) FILTER (WHERE seniority = 'senior') AS senior_count,
    COUNT(*) FILTER (WHERE seniority = 'unknown') AS unknown_seniority,
    COUNT(*) FILTER (WHERE has_salary) AS jobs_with_salary,
    ROUND(AVG(salary_midpoint), 0) AS avg_salary_midpoint
FROM v_analytical_jobs
GROUP BY role_category, country_code, dataset_period;

-- ---------------------------------------------------------------------------
-- 04: SKILL DEMAND (JOB-LEVEL PENETRATION)
-- Grain: 1 row = 1 skill/country combination
-- IMPORTANT: Each job counts ONCE per skill regardless of mention count
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_skill_demand AS
SELECT
    sk.canonical_name   AS skill_name,
    sk.category         AS skill_category,
    j.country           AS country_code,
    CASE
        WHEN js2.name = 'adzuna_uk' THEN 'Recent UK (2023-2026)'
        WHEN js2.name = 'chisel_pk' THEN 'Historical PK (2019-2021)'
        WHEN js2.name = 'kaggle_rozee_pk' THEN 'Supplementary PK'
        ELSE 'Unknown'
    END AS dataset_period,
    COUNT(DISTINCT j.job_id) AS job_count,
    -- Job-level penetration (each job counted once)
    ROUND(100.0 * COUNT(DISTINCT j.job_id) / (
        SELECT COUNT(*) FROM jobs j2 WHERE j2.country = j.country
    ), 1) AS penetration_pct
FROM job_skills jsk
JOIN skills sk      ON jsk.skill_id = sk.skill_id
JOIN jobs j         ON jsk.job_id   = j.job_id
JOIN job_sources js2 ON j.source_id = js2.source_id
GROUP BY sk.canonical_name, sk.category, j.country, js2.name;

-- ---------------------------------------------------------------------------
-- 05: UK vs PAKISTAN SKILL COMPARISON
-- Grain: 1 row = 1 skill with UK and PK penetration
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_skill_comparison AS
WITH uk_skills AS (
    SELECT
        sk.canonical_name AS skill_name,
        sk.category AS skill_category,
        COUNT(DISTINCT j.job_id) AS uk_job_count,
        ROUND(100.0 * COUNT(DISTINCT j.job_id) / (
            SELECT COUNT(*) FROM jobs WHERE country = 'GB'
        ), 1) AS uk_penetration_pct
    FROM job_skills jsk
    JOIN skills sk ON jsk.skill_id = sk.skill_id
    JOIN jobs j ON jsk.job_id = j.job_id
    WHERE j.country = 'GB'
    GROUP BY sk.canonical_name, sk.category
),
pk_skills AS (
    SELECT
        sk.canonical_name AS skill_name,
        COUNT(DISTINCT j.job_id) AS pk_job_count,
        ROUND(100.0 * COUNT(DISTINCT j.job_id) / (
            SELECT COUNT(*) FROM jobs WHERE country = 'PK'
        ), 1) AS pk_penetration_pct
    FROM job_skills jsk
    JOIN skills sk ON jsk.skill_id = sk.skill_id
    JOIN jobs j ON jsk.job_id = j.job_id
    WHERE j.country = 'PK'
    GROUP BY sk.canonical_name
)
SELECT
    COALESCE(u.skill_name, p.skill_name) AS skill_name,
    COALESCE(u.skill_category, 'unknown') AS skill_category,
    COALESCE(u.uk_job_count, 0) AS uk_job_count,
    COALESCE(u.uk_penetration_pct, 0) AS uk_penetration_pct,
    COALESCE(p.pk_job_count, 0) AS pk_job_count,
    COALESCE(p.pk_penetration_pct, 0) AS pk_penetration_pct,
    ROUND(COALESCE(u.uk_penetration_pct, 0) - COALESCE(p.pk_penetration_pct, 0), 1) AS penetration_diff,
    CASE
        WHEN u.uk_penetration_pct > p.pk_penetration_pct THEN 'UK-emphasized'
        WHEN p.pk_penetration_pct > u.uk_penetration_pct THEN 'PK-emphasized'
        ELSE 'Equal'
    END AS emphasis
FROM uk_skills u
FULL OUTER JOIN pk_skills p ON u.skill_name = p.skill_name
ORDER BY COALESCE(u.uk_penetration_pct, 0) + COALESCE(p.pk_penetration_pct, 0) DESC;

-- ---------------------------------------------------------------------------
-- 06: SKILL CO-OCCURRENCE
-- Grain: 1 row = 1 skill pair/country combination
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_skill_cocurrence AS
SELECT
    s1.canonical_name AS skill_a,
    s2.canonical_name AS skill_b,
    j.country AS country_code,
    COUNT(DISTINCT j.job_id) AS co_occurrence_count,
    ROUND(100.0 * COUNT(DISTINCT j.job_id) / (
        SELECT COUNT(*) FROM jobs j2 WHERE j2.country = j.country
    ), 1) AS co_occurrence_pct
FROM job_skills js1
JOIN job_skills js2 ON js1.job_id = js2.job_id AND js1.skill_id < js2.skill_id
JOIN skills s1 ON js1.skill_id = s1.skill_id
JOIN skills s2 ON js2.skill_id = s2.skill_id
JOIN jobs j ON js1.job_id = j.job_id
GROUP BY s1.canonical_name, s2.canonical_name, j.country
HAVING COUNT(DISTINCT j.job_id) >= 5
ORDER BY co_occurrence_count DESC;

-- ---------------------------------------------------------------------------
-- 07: ROLE-SPECIFIC SKILL ANALYSIS
-- Grain: 1 row = 1 skill/role/country combination
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_role_skills AS
SELECT
    jt.role_category,
    sk.canonical_name AS skill_name,
    sk.category AS skill_category,
    j.country AS country_code,
    COUNT(DISTINCT j.job_id) AS job_count,
    ROUND(100.0 * COUNT(DISTINCT j.job_id) / (
        SELECT COUNT(*) FROM jobs j2
        JOIN job_titles jt2 ON j2.title_id = jt2.title_id
        WHERE jt2.role_category = jt.role_category AND j2.country = j.country
    ), 1) AS penetration_pct
FROM job_skills jsk
JOIN skills sk ON jsk.skill_id = sk.skill_id
JOIN jobs j ON jsk.job_id = j.job_id
JOIN job_titles jt ON j.title_id = jt.title_id
GROUP BY jt.role_category, sk.canonical_name, sk.category, j.country
HAVING COUNT(DISTINCT j.job_id) >= 3
ORDER BY jt.role_category, job_count DESC;

-- ---------------------------------------------------------------------------
-- 08: LONDON ANALYSIS
-- Grain: 1 row = 1 metric for London vs rest of UK
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_london_analysis AS
SELECT
    location_group,
    COUNT(*) AS total_jobs,
    COUNT(*) FILTER (WHERE role_category = 'data_analyst') AS data_analyst_jobs,
    COUNT(*) FILTER (WHERE role_category = 'data_scientist') AS data_scientist_jobs,
    COUNT(*) FILTER (WHERE role_category = 'analytics_engineer') AS analytics_engineer_jobs,
    COUNT(*) FILTER (WHERE has_salary) AS jobs_with_salary,
    ROUND(AVG(salary_midpoint), 0) AS avg_salary_midpoint,
    COUNT(*) FILTER (WHERE work_mode = 'remote') AS remote_jobs,
    COUNT(*) FILTER (WHERE work_mode = 'hybrid') AS hybrid_jobs,
    COUNT(*) FILTER (WHERE work_mode = 'on_site') AS on_site_jobs,
    COUNT(*) FILTER (WHERE seniority = 'junior') AS junior_count,
    COUNT(*) FILTER (WHERE seniority = 'senior') AS senior_count
FROM v_analytical_jobs
WHERE country_code = 'GB'
GROUP BY location_group;

-- ---------------------------------------------------------------------------
-- 09: SALARY ANALYSIS
-- Grain: 1 row = 1 salary observation (jobs with salary only)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_salary_analysis AS
SELECT
    j.job_id,
    jt.role_category,
    jt.seniority,
    l.city,
    l.country AS country_code,
    js.name AS source_name,
    j.salary_min,
    j.salary_max,
    j.salary_currency,
    j.salary_period,
    j.salary_type,
    (j.salary_min + j.salary_max) / 2.0 AS salary_midpoint,
    j.job_title
FROM jobs j
LEFT JOIN job_titles jt ON j.title_id = jt.title_id
LEFT JOIN locations l ON j.location_id = l.location_id
LEFT JOIN job_sources js ON j.source_id = js.source_id
WHERE j.salary_min IS NOT NULL OR j.salary_max IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 10: SKILL-SALARY ASSOCIATION
-- Grain: 1 row = 1 skill with salary statistics
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_skill_salary AS
SELECT
    sk.canonical_name AS skill_name,
    sk.category AS skill_category,
    j.country AS country_code,
    COUNT(DISTINCT j.job_id) AS job_count,
    ROUND(AVG((j.salary_min + j.salary_max) / 2.0)::numeric, 0) AS avg_salary_midpoint,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY (j.salary_min + j.salary_max) / 2.0
    ))::numeric, 0) AS median_salary,
    ROUND((PERCENTILE_CONT(0.25) WITHIN GROUP (
        ORDER BY (j.salary_min + j.salary_max) / 2.0
    ))::numeric, 0) AS q25_salary,
    ROUND((PERCENTILE_CONT(0.75) WITHIN GROUP (
        ORDER BY (j.salary_min + j.salary_max) / 2.0
    ))::numeric, 0) AS q75_salary
FROM job_skills jsk
JOIN skills sk ON jsk.skill_id = sk.skill_id
JOIN jobs j ON jsk.job_id = j.job_id
WHERE j.salary_min IS NOT NULL OR j.salary_max IS NOT NULL
GROUP BY sk.canonical_name, sk.category, j.country
HAVING COUNT(DISTINCT j.job_id) >= 10;

-- ---------------------------------------------------------------------------
-- 11: SENIORITY ANALYSIS
-- Grain: 1 row = 1 seniority/country combination
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_seniority_analysis AS
SELECT
    seniority,
    country_code,
    dataset_period,
    COUNT(*) AS total_jobs,
    COUNT(*) FILTER (WHERE role_category = 'data_analyst') AS data_analyst,
    COUNT(*) FILTER (WHERE role_category = 'data_scientist') AS data_scientist,
    COUNT(*) FILTER (WHERE role_category = 'analytics_engineer') AS analytics_engineer,
    COUNT(*) FILTER (WHERE has_salary) AS jobs_with_salary,
    ROUND(AVG(salary_midpoint), 0) AS avg_salary_midpoint,
    COUNT(*) FILTER (WHERE work_mode = 'remote') AS remote_count,
    COUNT(*) FILTER (WHERE work_mode = 'hybrid') AS hybrid_count,
    COUNT(*) FILTER (WHERE work_mode = 'on_site') AS on_site_count
FROM v_analytical_jobs
GROUP BY seniority, country_code, dataset_period;

-- ---------------------------------------------------------------------------
-- 12: EMPLOYER CONCENTRATION
-- Grain: 1 row = 1 company/country combination
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_employer_analysis AS
SELECT
    company_name,
    country_code,
    source_name,
    COUNT(*) AS job_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY country_code), 2) AS pct_of_country,
    COUNT(DISTINCT role_category) AS distinct_roles,
    COUNT(*) FILTER (WHERE has_salary) AS jobs_with_salary
FROM v_analytical_jobs
WHERE company_name IS NOT NULL AND company_name != ''
GROUP BY company_name, country_code, source_name
ORDER BY job_count DESC;

-- ---------------------------------------------------------------------------
-- 13: TEMPORAL ANALYSIS
-- Grain: 1 row = 1 month/country combination
-- Note: posting_date may not be available for all records
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_temporal_analysis AS
SELECT
    DATE_TRUNC('month', posting_date) AS month,
    country_code,
    source_name,
    COUNT(*) AS job_count,
    COUNT(*) FILTER (WHERE role_category = 'data_analyst') AS data_analyst_count,
    COUNT(*) FILTER (WHERE role_category = 'data_scientist') AS data_scientist_count,
    COUNT(*) FILTER (WHERE has_salary) AS jobs_with_salary,
    ROUND(AVG(salary_midpoint), 0) AS avg_salary_midpoint
FROM v_analytical_jobs
WHERE posting_date IS NOT NULL
GROUP BY DATE_TRUNC('month', posting_date), country_code, source_name
ORDER BY month;

-- ---------------------------------------------------------------------------
-- Done.
-- ---------------------------------------------------------------------------
