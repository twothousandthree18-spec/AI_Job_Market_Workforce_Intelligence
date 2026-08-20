"""Verify staging parquet output."""
import pandas as pd

PARQUET_PATH = (
    "D:/M Projects/AI-Powered Job Market & Workforce Intelligence "
    "Platform/data/staging/kaggle_rozee_pk.parquet"
)
df = pd.read_parquet(PARQUET_PATH)
print(f"Staging parquet: {len(df)} rows, {len(df.columns)} cols")
print(f"Countries: {df['country'].value_counts().to_dict()}")
print("\nSample titles:")
for t in df["job_title"].head(5):
    print(f"  - {t}")
print("Salary data (last 5 rows):")
cols = ["job_title", "salary_min", "salary_max", "salary_currency"]
for _, r in df[cols].tail(5).iterrows():
    sal = f"{r['salary_min']}-{r['salary_max']}"
    print(f"  {r['job_title']}: {sal} {r['salary_currency']}")
