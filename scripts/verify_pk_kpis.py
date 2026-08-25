"""Verify Pakistan KPIs from source data."""
import pandas as pd
from pathlib import Path

d = Path("data/analytics")

ov = pd.read_csv(d / "01_market_overview.csv")
print("=== MARKET OVERVIEW ===")
print(ov[["source_name", "total_jobs", "unique_companies", "unique_cities"]].to_string())

roles = pd.read_csv(d / "02_role_demand.csv")
pk_roles = (
    roles[roles.country_code == "PK"]
    .groupby("role_category")["job_count"]
    .sum()
    .sort_values(ascending=False)
)
print("\n=== PK ROLES ===")
for r, c in pk_roles.items():
    print(f"  {r}: {c} ({c / 5227 * 100:.1f}%)")

sen = pd.read_csv(d / "10_seniority_analysis.csv")
pk_sen = (
    sen[sen.country_code == "PK"]
    .groupby("seniority")["total_jobs"]
    .sum()
    .sort_values(ascending=False)
)
print("\n=== PK SENIORITY ===")
for s, c in pk_sen.items():
    print(f"  {s}: {c} ({c / 5227 * 100:.1f}%)")

skills = pd.read_csv(d / "03_skill_demand.csv")
pk_sk = skills[skills.country_code == "PK"].nlargest(15, "job_count")
print("\n=== TOP 15 PK SKILLS ===")
for _, r in pk_sk.iterrows():
    print(f"  {r.skill_name}: {r.job_count} ({r.penetration_pct:.1f}%)")

jobs = pd.read_csv(d / "13_analytical_jobs.csv")
pk = jobs[jobs.country_code == "PK"]
cities = pk.city.value_counts().head(10)
print("\n=== TOP 10 PK CITIES ===")
for c, n in cities.items():
    print(f"  {c}: {n} ({n / 5227 * 100:.1f}%)")

emp = pd.read_csv(d / "11_employer_analysis.csv")
pk_emp = emp[emp.country_code == "PK"].nlargest(10, "job_count")
print("\n=== TOP 10 PK EMPLOYERS ===")
for _, r in pk_emp.iterrows():
    print(f"  {r.company_name}: {r.job_count}")

print("\n=== PK WORK MODE ===")
print(pk.work_mode.value_counts().to_dict())

temp = pd.read_csv(d / "12_temporal_analysis.csv")
pk_t = temp[temp.country_code == "PK"].sort_values("job_count", ascending=False)
print("\n=== PK TEMPORAL ===")
print(f"  Months: {len(pk_t)}")
print(f"  Range: {pk_t.month.min()} to {pk_t.month.max()}")
print(f"  Peak: {pk_t.iloc[0]['month']} ({pk_t.iloc[0]['job_count']} jobs)")

# UK comparison data
uk = jobs[jobs.country_code == "GB"]
print("\n=== UK vs PK SUMMARY ===")
print(f"  UK: {len(uk)} jobs, {uk.company_name.nunique()} companies, {uk.city.nunique()} cities")
print(f"  PK: {len(pk)} jobs, {pk.company_name.nunique()} companies, {pk.city.nunique()} cities")

# Career intel
rs = pd.read_csv(d / "06_role_skills.csv")
pk_da = rs[(rs.country_code == "PK") & (rs.role_category == "data_analyst")]
print("\n=== PK DATA ANALYST SKILLS ===")
for _, r in pk_da.nlargest(10, "penetration_pct").iterrows():
    print(f"  {r.skill_name}: {r.penetration_pct:.1f}%")

pk_ds = rs[(rs.country_code == "PK") & (rs.role_category == "data_scientist")]
print("\n=== PK DATA SCIENTIST SKILLS ===")
if len(pk_ds) > 0:
    for _, r in pk_ds.nlargest(10, "penetration_pct").iterrows():
        print(f"  {r.skill_name}: {r.penetration_pct:.1f}%")
else:
    print("  (insufficient data)")

# Skill categories
cat = pd.read_csv(d / "03_skill_demand.csv")
pk_cat = cat[cat.country_code == "PK"].groupby("skill_category")["job_count"].sum().sort_values(ascending=False)
print("\n=== PK SKILL CATEGORIES ===")
for c, n in pk_cat.items():
    print(f"  {c}: {n}")
