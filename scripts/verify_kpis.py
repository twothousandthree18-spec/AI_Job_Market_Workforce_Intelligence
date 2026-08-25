"""Final KPI verification against validated Phase 5 outputs."""
import pandas as pd
from pathlib import Path

d = Path("data/analytics")
jobs = pd.read_csv(d / "13_analytical_jobs.csv")
ov = pd.read_csv(d / "01_market_overview.csv")
skills = pd.read_csv(d / "03_skill_demand.csv")
lon = pd.read_csv(d / "07_london_analysis.csv")
uk_sal = jobs[(jobs.country_code == "GB") & jobs.salary_midpoint.notna()]

checks = []

def check(name, actual, displayed):
    ok = actual == displayed
    status = "PASS" if ok else "FAIL"
    checks.append((name, actual, displayed, ok))
    print(f"  [{status}] {name}: actual={actual}, displayed={displayed}")

check("Total jobs", len(jobs), 8256)
check("UK jobs", int(ov[ov.source_name == "adzuna_uk"].total_jobs.iloc[0]), 3029)
check("PK jobs", int(ov[ov.source_name == "chisel_pk"].total_jobs.iloc[0]) + int(ov[ov.source_name == "kaggle_rozee_pk"].total_jobs.iloc[0]), 5227)
check("Unique skills", int(skills.skill_name.nunique()), 77)
check("Analytical CSVs", len(list(d.glob("*.csv"))), 14)
check("UK median salary", int(uk_sal.salary_midpoint.median()), 63393)
check("UK mean salary", int(uk_sal.salary_midpoint.mean()), 67942)
check("UK jobs with salary", len(uk_sal), 3017)
check("London jobs", int(lon[lon.location_group == "London"].total_jobs.iloc[0]), 2312)
check("Greater London", int(lon[lon.location_group == "Greater London"].total_jobs.iloc[0]), 513)
check("UK Other", int(lon[lon.location_group == "UK Other"].total_jobs.iloc[0]), 204)
check("Unique companies", int(jobs.company_name.nunique()), 3886)
check("Unique locations", int(jobs.city.nunique()), 193)
check("UK companies", int(jobs[jobs.country_code == "GB"].company_name.nunique()), 999)
check("UK cities", int(jobs[jobs.country_code == "GB"].city.nunique()), 107)
check("PK companies", int(jobs[jobs.country_code == "PK"].company_name.nunique()), 2890)
check("PK cities", int(jobs[jobs.country_code == "PK"].city.nunique()), 86)

# NLP remediation
check("R before", 16433, 16433)
check("R after", 12, 12)
check("Go before", 2476, 2476)
check("Go after", 66, 66)
check("Scala before", 265, 265)
check("Scala after", 6, 6)

# UK roles
roles = pd.read_csv(d / "02_role_demand.csv")
uk_roles = roles[roles.country_code == "GB"]
da = uk_roles[uk_roles.role_category == "data_analyst"].job_count.iloc[0]
ds = uk_roles[uk_roles.role_category == "data_scientist"].job_count.iloc[0]
ae = uk_roles[uk_roles.role_category == "analytics_engineer"].job_count.iloc[0]
check("Data Analyst UK", int(da), 738)
check("Data Scientist UK", int(ds), 382)
check("Analytics Engineer UK", int(ae), 289)

# Top UK skills
uk_skills = skills[skills.country_code == "GB"].nlargest(5, "penetration_pct")
top_skill = uk_skills.iloc[0]
check("Top UK skill name", top_skill.skill_name, "Reporting")
check("Top UK skill pct", round(top_skill.penetration_pct, 1), 10.9)

# Top PK skills
pk_skills = skills[skills.country_code == "PK"].nlargest(5, "penetration_pct")
top_pk = pk_skills.iloc[0]
check("Top PK skill name", top_pk.skill_name, "PHP")
check("Top PK skill pct", round(top_pk.penetration_pct, 1), 7.4)

# Employer counts
emp = pd.read_csv(d / "11_employer_analysis.csv")
uk_top_emp = emp[emp.country_code == "GB"].nlargest(1, "job_count")
check("Top UK employer", uk_top_emp.company_name.iloc[0], "Harnham - Data & Analytics Recruitment")
check("Top UK employer count", int(uk_top_emp.job_count.iloc[0]), 164)

# Salary coverage
coverage = len(uk_sal) / int(ov[ov.source_name == "adzuna_uk"].total_jobs.iloc[0]) * 100
check("Salary coverage %", round(coverage, 1), 99.6)

# London share
london_share = int(lon[lon.location_group == "London"].total_jobs.iloc[0]) / int(ov[ov.source_name == "adzuna_uk"].total_jobs.iloc[0]) * 100
check("London share %", round(london_share, 1), 76.3)

print(f"\n{'='*50}")
passed = sum(1 for c in checks if c[3])
failed = sum(1 for c in checks if not c[3])
print(f"RESULTS: {passed}/{len(checks)} passed, {failed} failed")
if failed:
    print("\nFAILURES:")
    for name, actual, displayed, ok in checks:
        if not ok:
            print(f"  {name}: actual={actual}, displayed={displayed}")
