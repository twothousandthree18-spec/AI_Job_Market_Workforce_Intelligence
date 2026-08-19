-- =============================================================================
-- AI Job Market & Workforce Intelligence Platform — PostgreSQL Analytical Schema
-- =============================================================================
-- Version: 1.0
-- Created: 2026-08-18
-- =============================================================================

-- ---------------------------------------------------------------------------
-- REFERENCE TABLES
-- ---------------------------------------------------------------------------

CREATE TABLE job_sources (
    source_id       SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    country         VARCHAR(5) NOT NULL,
    base_url        VARCHAR(500),
    api_type        VARCHAR(50),
    auth_type       VARCHAR(50),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE companies (
    company_id      SERIAL PRIMARY KEY,
    name            VARCHAR(300) NOT NULL,
    name_raw        VARCHAR(300) NOT NULL,
    domain          VARCHAR(200),
    country         VARCHAR(5),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (name, country)
);

CREATE TABLE locations (
    location_id     SERIAL PRIMARY KEY,
    city            VARCHAR(100),
    region          VARCHAR(100),
    country         VARCHAR(5) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (city, region, country)
);

CREATE TABLE industries (
    industry_id     SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (name)
);

CREATE TABLE job_titles (
    title_id        SERIAL PRIMARY KEY,
    normalized_title VARCHAR(200) NOT NULL,
    role_category   VARCHAR(100) NOT NULL,
    seniority       VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (normalized_title, role_category)
);

CREATE TABLE skills (
    skill_id        SERIAL PRIMARY KEY,
    canonical_name  VARCHAR(100) NOT NULL UNIQUE,
    category        VARCHAR(50) NOT NULL CHECK (
                        category IN ('technical','analytical','ai_ml',
                                     'tool','business_soft','certification','education')
                    ),
    aliases         JSONB DEFAULT '[]',
    is_standard     BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE job_categories (
    category_id     SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    taxonomy_source VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (name, taxonomy_source)
);

-- ---------------------------------------------------------------------------
-- FACT / PRIMARY TABLE
-- ---------------------------------------------------------------------------

CREATE TABLE jobs (
    job_id              SERIAL PRIMARY KEY,
    source_id           INT NOT NULL REFERENCES job_sources(source_id),
    source_job_id       VARCHAR(200) NOT NULL,
    job_title           VARCHAR(500) NOT NULL,
    title_id            INT REFERENCES job_titles(title_id),
    company_id          INT REFERENCES companies(company_id),
    location_id         INT REFERENCES locations(location_id),
    country             VARCHAR(5) NOT NULL,
    salary_min          NUMERIC(12,2),
    salary_max          NUMERIC(12,2),
    salary_currency     CHAR(3),
    salary_period       VARCHAR(20) CHECK (salary_period IN ('annual','monthly','hourly')),
    salary_type         VARCHAR(20) CHECK (salary_type IN ('advertised','estimated')),
    employment_type     VARCHAR(50),
    work_mode           VARCHAR(50) CHECK (work_mode IN ('on_site','hybrid','remote',NULL)),
    experience_level    VARCHAR(50),
    industry_id         INT REFERENCES industries(industry_id),
    education_requirement VARCHAR(100),
    description_raw     TEXT,
    posting_date        DATE,
    closing_date        DATE,
    job_url             VARCHAR(1000),
    is_active           BOOLEAN DEFAULT true,
    dq_score            NUMERIC(5,2),
    collected_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (source_id, source_job_id)
);

CREATE INDEX idx_jobs_posting_date   ON jobs (posting_date);
CREATE INDEX idx_jobs_country        ON jobs (country);
CREATE INDEX idx_jobs_company        ON jobs (company_id);
CREATE INDEX idx_jobs_location       ON jobs (location_id);
CREATE INDEX idx_jobs_title          ON jobs (title_id);
CREATE INDEX idx_jobs_industry       ON jobs (industry_id);
CREATE INDEX idx_jobs_url            ON jobs (job_url) WHERE job_url IS NOT NULL;

-- ---------------------------------------------------------------------------
-- JUNCTION / DETAIL TABLES
-- ---------------------------------------------------------------------------

CREATE TABLE job_skills (
    job_id          INT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    skill_id        INT NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    mention_count   INT DEFAULT 1,
    is_required     BOOLEAN,
    extraction_method VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (job_id, skill_id)
);

CREATE INDEX idx_job_skills_skill ON job_skills (skill_id);

CREATE TABLE salary_data (
    salary_id       SERIAL PRIMARY KEY,
    job_id          INT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    salary_min      NUMERIC(12,2),
    salary_max      NUMERIC(12,2),
    currency        CHAR(3),
    period          VARCHAR(20),
    salary_type     VARCHAR(20) CHECK (salary_type IN ('advertised','estimated')),
    estimate_method VARCHAR(100),
    note            TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_salary_job ON salary_data (job_id);

CREATE TABLE job_duplicates (
    group_id        SERIAL,
    job_id          INT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    dup_reason      VARCHAR(50) NOT NULL CHECK (
                        dup_reason IN ('url','source_id','title_company','fuzzy_title')
                    ),
    confidence      NUMERIC(3,2),
    resolved        BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (group_id, job_id)
);

-- ---------------------------------------------------------------------------
-- PIPELINE / QUALITY TRACKING
-- ---------------------------------------------------------------------------

CREATE TABLE ingestion_runs (
    run_id              SERIAL PRIMARY KEY,
    run_type            VARCHAR(20) NOT NULL CHECK (run_type IN ('historical','incremental')),
    source_id           INT REFERENCES job_sources(source_id),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ,
    status              VARCHAR(20) DEFAULT 'running' CHECK (
                            status IN ('running','completed','failed','cancelled')
                        ),
    records_read        INT DEFAULT 0,
    records_accepted    INT DEFAULT 0,
    records_rejected    INT DEFAULT 0,
    error_summary       JSONB,
    config_snapshot     JSONB,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE data_quality_results (
    result_id       SERIAL PRIMARY KEY,
    run_id          INT REFERENCES ingestion_runs(run_id),
    job_id          INT REFERENCES jobs(job_id) ON DELETE CASCADE,
    check_name      VARCHAR(100) NOT NULL,
    severity        VARCHAR(20) CHECK (severity IN ('critical','major','minor')),
    passed          BOOLEAN NOT NULL,
    details         JSONB,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_dq_run   ON data_quality_results (run_id);
CREATE INDEX idx_dq_job   ON data_quality_results (job_id);
CREATE INDEX idx_dq_check ON data_quality_results (check_name);

-- ---------------------------------------------------------------------------
-- DERIVED / MATERIALIZED TABLES (built by pipeline, not direct inserts)
-- ---------------------------------------------------------------------------

CREATE TABLE skill_trends (
    id              SERIAL PRIMARY KEY,
    month           DATE NOT NULL,
    country         VARCHAR(5) NOT NULL,
    role_category   VARCHAR(100),
    skill_id        INT REFERENCES skills(skill_id),
    postings_with_skill INT NOT NULL,
    total_postings  INT NOT NULL,
    share_pct       NUMERIC(5,2) NOT NULL,
    computed_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_st_month_country ON skill_trends (month, country);
CREATE INDEX idx_st_skill         ON skill_trends (skill_id);

-- ---------------------------------------------------------------------------
-- VIEWS — Star Schema for Power BI / API
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_fact_jobs AS
SELECT
    j.job_id,
    j.job_title,
    jt.normalized_title,
    jt.role_category,
    jt.seniority,
    c.name              AS company_name,
    l.city,
    l.region,
    l.country,
    i.name              AS industry,
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
    j.job_url,
    j.dq_score,
    j.collected_at,
    js.name             AS source_name
FROM jobs j
LEFT JOIN job_titles jt   ON j.title_id    = jt.title_id
LEFT JOIN companies c     ON j.company_id  = c.company_id
LEFT JOIN locations l     ON j.location_id = l.location_id
LEFT JOIN industries i    ON j.industry_id = i.industry_id
LEFT JOIN job_sources js  ON j.source_id   = js.source_id;

CREATE OR REPLACE VIEW v_skill_summary AS
SELECT
    sk.canonical_name   AS skill_name,
    sk.category         AS skill_category,
    j.country,
    jt.role_category,
    COUNT(DISTINCT js2.job_id) AS job_count
FROM job_skills js2
JOIN skills sk   ON js2.skill_id = sk.skill_id
JOIN jobs j      ON js2.job_id   = j.job_id
LEFT JOIN job_titles jt ON j.title_id = jt.title_id
GROUP BY sk.canonical_name, sk.category, j.country, jt.role_category;

-- ---------------------------------------------------------------------------
-- Done.
-- ---------------------------------------------------------------------------
