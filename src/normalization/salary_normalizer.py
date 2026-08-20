from __future__ import annotations

import pandas as pd

_VALID_PERIODS = {"annual", "monthly", "hourly"}


class SalaryNormalizer:
    """Clean salary fields and compute salary bands."""

    def normalize_record(self, record: dict) -> dict:
        """Ensure min <= max, uppercase currency, lowercase period."""
        sal_min = record.get("salary_min")
        sal_max = record.get("salary_max")

        if (
            sal_min is not None
            and sal_max is not None
            and isinstance(sal_min, (int, float))
            and isinstance(sal_max, (int, float))
            and sal_min > sal_max
        ):
            record["salary_min"] = sal_max
            record["salary_max"] = sal_min

        currency = record.get("salary_currency")
        if isinstance(currency, str):
            record["salary_currency"] = currency.strip().upper()

        period = record.get("salary_period")
        if isinstance(period, str):
            record["salary_period"] = period.strip().lower()

        return record

    def _compute_band(self, row: pd.Series) -> str | None:
        currency = row.get("salary_currency")
        period = row.get("salary_period")
        sal_max = row.get("salary_max")

        if pd.isna(currency) or pd.isna(period) or pd.isna(sal_max):
            return None
        if not isinstance(sal_max, (int, float)):
            return None

        currency = str(currency).upper()
        period = str(period).lower()

        if currency == "PKR" and period == "monthly":
            if sal_max < 50_000:
                return "low"
            if sal_max <= 100_000:
                return "mid"
            return "high"

        if currency == "GBP" and period == "annual":
            if sal_max < 30_000:
                return "low"
            if sal_max <= 60_000:
                return "mid"
            return "high"

        return None

    def normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalise salary fields and add a salary_band column."""
        df = df.copy()

        for idx, row in df.iterrows():
            record = row.to_dict()
            self.normalize_record(record)
            for key in ("salary_min", "salary_max", "salary_currency", "salary_period"):
                if key in record:
                    df.at[idx, key] = record[key]

        df["salary_band"] = df.apply(self._compute_band, axis=1)
        return df

    def compute_salary_stats(self, df: pd.DataFrame) -> dict:
        """Return summary statistics for salary data."""
        has_salary = df["salary_max"].notna() & df["salary_max"].apply(
            lambda v: isinstance(v, (int, float))
        )

        with_sal = int(has_salary.sum())
        without_sal = int((~has_salary).sum())

        subset = df.loc[has_salary]
        median_min = float(subset["salary_min"].median()) if len(subset) else None
        median_max = float(subset["salary_max"].median()) if len(subset) else None

        by_country: dict[str, dict[str, int | float | None]] = {}
        for country, group in subset.groupby("country"):
            by_country[country] = {
                "count": int(len(group)),
                "median_min": float(group["salary_min"].median()),
                "median_max": float(group["salary_max"].median()),
            }

        return {
            "count_with_salary": with_sal,
            "count_without_salary": without_sal,
            "median_min": median_min,
            "median_max": median_max,
            "by_country": by_country,
        }
