"""
Source quality report — per-source data quality comparison.

For each source: total jobs, duplicates, description completeness,
salary completeness, location completeness, date completeness,
skill extraction success.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pipeline.config import RunManifest


def generate_source_quality_report(
    df: pd.DataFrame,
    manifest: RunManifest,
    output_dir: Path | None = None,
) -> dict:
    """Generate per-source quality comparison.

    Returns the report dict and writes JSON + markdown to output_dir.
    """
    if output_dir is None:
        output_dir = manifest.run_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {}
    total = len(df)

    if "source" not in df.columns:
        report["error"] = "No 'source' column in DataFrame"
        return report

    for source_name, group in df.groupby("source"):
        n = len(group)
        src: dict = {"total_jobs": n}

        # Duplicates
        if "is_duplicate" in group.columns:
            dup_count = int(group["is_duplicate"].sum())
            src["duplicates"] = dup_count
            src["unique_jobs"] = n - dup_count
            src["duplicate_pct"] = round(dup_count / n * 100, 1) if n > 0 else 0

        # Description completeness
        if "description" in group.columns:
            has_desc = int(group["description"].notna().sum())
            src["has_description"] = has_desc
            src["description_pct"] = round(has_desc / n * 100, 1) if n > 0 else 0

        # Salary completeness
        if "salary_max" in group.columns:
            has_salary_mask = (
                group["salary_max"].notna()
                & group["salary_max"].apply(
                    lambda v: isinstance(v, (int, float))
                )
            )
            has_salary = int(has_salary_mask.sum())
            src["has_salary"] = has_salary
            src["salary_pct"] = round(has_salary / n * 100, 1) if n > 0 else 0

        # Location completeness
        if "city" in group.columns:
            has_city = int(
                (group["city"].notna() & (group["city"] != "")).sum()
            )
            src["has_location"] = has_city
            src["location_pct"] = round(has_city / n * 100, 1) if n > 0 else 0

        # Date completeness
        if "posting_date" in group.columns:
            dates = pd.to_datetime(group["posting_date"], errors="coerce")
            has_date = int(dates.notna().sum())
            src["has_date"] = has_date
            src["date_pct"] = round(has_date / n * 100, 1) if n > 0 else 0

        # Skills extraction
        if "skills_list" in group.columns:
            import numpy as np
            has_skills = int(
                group["skills_list"].apply(
                    lambda s: (
                        (isinstance(s, np.ndarray) and len(s) > 0)
                        or (isinstance(s, (list, tuple)) and len(s) > 0)
                    )
                ).sum()
            )
            src["has_skills"] = has_skills
            src["skills_pct"] = round(has_skills / n * 100, 1) if n > 0 else 0

        # DQ score
        if "dq_score" in group.columns:
            scores = group["dq_score"].dropna()
            if len(scores) > 0:
                src["dq_mean"] = round(float(scores.mean()), 1)
                src["dq_below_70"] = int((scores < 70).sum())

        report[source_name] = src

    # --- Save JSON ---
    json_path = output_dir / "source_quality_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    manifest.logger.info(f"Source quality report saved: {json_path}")

    # --- Save markdown ---
    md_path = output_dir / "source_quality_report.md"
    md_lines = ["# Source Quality Report\n"]
    md_lines.append(f"**Total records across all sources:** {total:,}\n")

    for source_name, stats in report.items():
        if source_name == "error":
            continue
        md_lines.append(f"## {source_name}\n")
        md_lines.append(f"- **Total jobs:** {stats.get('total_jobs', 0):,}")
        if "unique_jobs" in stats:
            md_lines.append(f"- **Unique jobs:** {stats['unique_jobs']:,}")
            dup_pct = stats['duplicate_pct']
            md_lines.append(
                f"- **Duplicates:** {stats['duplicates']:,} ({dup_pct}%)"
            )
        md_lines.append(
            f"- **Description:** {stats.get('has_description', '?')} "
            f"({stats.get('description_pct', '?')}%)"
        )
        md_lines.append(
            f"- **Salary:** {stats.get('has_salary', '?')} "
            f"({stats.get('salary_pct', '?')}%)"
        )
        md_lines.append(
            f"- **Location:** {stats.get('has_location', '?')} "
            f"({stats.get('location_pct', '?')}%)"
        )
        md_lines.append(
            f"- **Date:** {stats.get('has_date', '?')} "
            f"({stats.get('date_pct', '?')}%)"
        )
        md_lines.append(
            f"- **Skills:** {stats.get('has_skills', '?')} "
            f"({stats.get('skills_pct', '?')}%)"
        )
        if "dq_mean" in stats:
            md_lines.append(f"- **DQ mean:** {stats['dq_mean']}")
            md_lines.append(f"- **DQ below 70:** {stats['dq_below_70']:,}")
        md_lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    manifest.logger.info(f"Source quality report markdown: {md_path}")

    return report
