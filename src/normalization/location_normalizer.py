from __future__ import annotations

import pandas as pd

COUNTRY_MAP: dict[str, str] = {
    "pk": "Pakistan",
    "gb": "United Kingdom",
    "uk": "United Kingdom",
    "us": "United States",
    "in": "India",
}

COUNTRY_CODE_MAP: dict[str, str] = {v: k.upper() for k, v in COUNTRY_MAP.items()}

PAKISTAN_CITIES: dict[str, str] = {
    "karachi": "Karachi",
    "lahore": "Lahore",
    "islamabad": "Islamabad",
    "rawalpindi": "Rawalpindi",
    "faisalabad": "Faisalabad",
    "multan": "Multan",
    "peshawar": "Peshawar",
    "quetta": "Quetta",
}

UK_CITIES: dict[str, str] = {
    "london": "London",
    "manchester": "Manchester",
    "birmingham": "Birmingham",
    "edinburgh": "Edinburgh",
    "leeds": "Leeds",
    "glasgow": "Glasgow",
    "bristol": "Bristol",
    "liverpool": "Liverpool",
}

_CITY_MAPS: dict[str, dict[str, str]] = {
    "Pakistan": PAKISTAN_CITIES,
    "United Kingdom": UK_CITIES,
}


class LocationNormalizer:
    """Standardise country codes, country names, and city names."""

    def normalize_country(self, code: str) -> str:
        """Return a 2-letter upper-country code, validated against known codes."""
        upper = code.strip().upper()
        if upper in COUNTRY_MAP:
            return upper
        return upper

    def normalize_city(self, city: str, country: str) -> str:
        """Return canonical city name or title-cased original."""
        country_name = COUNTRY_MAP.get(country.lower().strip(), country)
        city_map = _CITY_MAPS.get(country_name, {})
        canonical = city_map.get(city.lower().strip())
        return canonical if canonical else city.strip().title()

    def normalize_country_name(self, code: str) -> str:
        """Return full country name from a code, or the input if unknown."""
        return COUNTRY_MAP.get(code.strip().lower(), code)

    def normalize_record(self, record: dict) -> dict:
        """Normalise country, city, region fields in-place. Returns *record*."""
        code = record.get("country", "")
        if isinstance(code, str) and code:
            record["country"] = self.normalize_country_name(code)
            record["country_code"] = self.normalize_country(code)

        city = record.get("city", "")
        if isinstance(city, str) and city:
            record["city"] = self.normalize_city(city, code)

        region = record.get("region")
        if isinstance(region, str) and region:
            record["region"] = region.strip().title()

        return record

    def normalize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalise location columns across a DataFrame."""
        df = df.copy()
        for idx, row in df.iterrows():
            record = row.to_dict()
            self.normalize_record(record)
            for key in ("country", "country_code", "city", "region"):
                if key in record:
                    df.at[idx, key] = record[key]
        return df
