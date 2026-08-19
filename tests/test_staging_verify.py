"""Verify staging parquet output."""
import pandas as pd

df = pd.read_parquet(r"D:\M Projects\AI-Powered Job Market & Workforce Intelligence Platform\data\staging\kaggle_rozee_pk.parquet")
print(f"Staging parquet: {len(df)} rows, {len(df.columns)} columns")
print(f"Countries: {df['country'].value_counts().to_dict()}")
print(f"\nSample titles:")
for t in df["job_title"].head(5):
    print(f"  - {t}")
print(f"Salary data (last 5 rows from new import):")
for _, r in df[["job_title", "salary_min", "salary_max", "salary_currency"]].tail(5).iterrows():
    print(f"  {r['job_title']}: {r['salary_min']}-{r['salary_max']} {r['salary_currency']}")
