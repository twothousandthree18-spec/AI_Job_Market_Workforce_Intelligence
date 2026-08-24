// =============================================================================
// Power Query (M) — Import preparation for the Workforce Intelligence model
// =============================================================================
// Apply these steps to every CSV import (replace <SourceCsv> with each file's
// source step). They are deliberately minimal:
//   1. Correct column types.
//   2. Convert PostgreSQL float8 'NaN' artifacts to null in salary columns
//      so "salary coverage" reflects REAL observations only.
//   3. Normalise blank company/city strings to null so DISTINCTCOUNT is honest.
// Full context: dashboard/powerbi/model_specification.md §1 rule 5 and
// docs/powerbi_data_dictionary.md per-table notes.
// =============================================================================

// ---------------------------------------------------------------------------
// Jobs (13_analytical_jobs.csv) — job-grain fact
// ---------------------------------------------------------------------------
let
    Source = Csv.Document(<SourceCsv>, [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"job_id", Int64.Type},
            {"job_title", type text},
            {"normalized_title", type text},
            {"role_category", type text},
            {"seniority", type text},
            {"company_name", type text},
            {"city", type text},
            {"region", type text},
            {"country_code", type text},
            {"location_group", type text},
            {"salary_min", type number},
            {"salary_max", type number},
            {"salary_currency", type text},
            {"salary_period", type text},
            {"salary_type", type text},
            {"employment_type", type text},
            {"work_mode", type text},
            {"experience_level", type text},
            {"education_requirement", type text},
            {"posting_date", type date},
            {"collected_at", type datetimezone},
            {"dq_score", type number},
            {"source_name", type text},
            {"has_salary", type logical},
            {"salary_midpoint", type number},
            {"dataset_period", type text}
        }
    ),
    // NaN floats from PostgreSQL float8 columns -> null (real coverage only)
    SalaryMinClean = Table.ReplaceValue(
        Typed, Number.NaN, null, Replacer.ReplaceValue, {"salary_min"}),
    SalaryMaxClean = Table.ReplaceValue(
        SalaryMinClean, Number.NaN, null, Replacer.ReplaceValue, {"salary_max"}),
    SalaryMidClean = Table.ReplaceValue(
        SalaryMaxClean, Number.NaN, null, Replacer.ReplaceValue, {"salary_midpoint"}),
    // Empty strings -> null for clean DISTINCTCOUNT
    CompanyClean = Table.ReplaceValue(
        SalaryMidClean, "", null, Replacer.ReplaceValue, {"company_name"}),
    Output = Table.ReplaceValue(
        CompanyClean, "", null, Replacer.ReplaceValue, {"city"})
in
    Output

// ---------------------------------------------------------------------------
// Reusable helper — apply the same NaN cleanup to any other imported table
// that carries salary_midpoint / median_salary / avg_salary_midpoint /
// q25_salary / q75_salary columns (tables 02, 07, 08, 09, 10, 12).
//
// Table.RemoveRowsWithErrors alternative is NOT used: we keep the rows and
// blank the measure inputs so denominators stay visible in tooltips.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// SkillSalary (09_skill_salary.csv) — additionally restrict to GB.
// Rationale: CHISEL (PK) salary medians are all NaN; keeping PK rows would
// imply a Pakistani salary distribution that does not exist in this data.
// ---------------------------------------------------------------------------
let
    Source = Csv.Document(<SourceSkillSalary>, [Delimiter = ",", Encoding = 65001]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"skill_name", type text},
            {"skill_category", type text},
            {"country_code", type text},
            {"job_count", Int64.Type},
            {"avg_salary_midpoint", type number},
            {"median_salary", type number},
            {"q25_salary", type number},
            {"q75_salary", type number}
        }
    ),
    MedianClean = Table.ReplaceValue(
        Typed, Number.NaN, null, Replacer.ReplaceValue,
        {"avg_salary_midpoint", "median_salary", "q25_salary", "q75_salary"}),
    Output = Table.SelectRows(MedianClean, each [country_code] = "GB")
in
    Output

// ---------------------------------------------------------------------------
// JobSkills bridge (14_job_skills_bridge.csv)
// ---------------------------------------------------------------------------
let
    Source = Csv.Document(<SourceJobSkillsBridge>, [Delimiter = ",", Encoding = 65001]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Output = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"job_id", Int64.Type},
            {"skill_name", type text},
            {"skill_category", type text},
            {"country_code", type text}
        }
    )
in
    Output
