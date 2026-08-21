"""
Data coverage report — generates a comprehensive summary of the processed dataset.

Covers: country distribution, role coverage, date range, salary coverage,
work mode, seniority, skills, and source breakdown.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pipeline.config import RunManifest


def generate_coverage_report(
    df: pd.DataFrame,
    manifest: RunManifest,
    output_dir: Path | None = None,
) -> dict:
    """Generate and save a data coverage report.

    Returns the report dict and writes JSON + markdown to output_dir.
    """
    if output_dir is None:
        output_dir = manifest.run_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {}

    # --- Overall ---
    report["overall"] = {
        "total_records": int(len(df)),
        "unique_source_job_ids": int(
            df["source_job_id"].nunique()
        ) if "source_job_id" in df.columns else int(len(df)),
    }

    # --- Country ---
    if "country" in df.columns:
        country_counts = df["country"].value_counts().to_dict()
        report["by_country"] = {str(k): int(v) for k, v in country_counts.items()}

    # --- Source ---
    if "source" in df.columns:
        source_counts = df["source"].value_counts().to_dict()
        report["by_source"] = {str(k): int(v) for k, v in source_counts.items()}

    # --- Role Category ---
    if "role_category" in df.columns:
        rc_counts = df["role_category"].value_counts().to_dict()
        report["by_role_category"] = {str(k): int(v) for k, v in rc_counts.items()}

    # --- Seniority ---
    if "seniority" in df.columns:
        sen_counts = df["seniority"].value_counts().to_dict()
        report["by_seniority"] = {str(k): int(v) for k, v in sen_counts.items()}

    # --- Work Mode ---
    if "work_mode" in df.columns:
        wm_counts = df["work_mode"].value_counts().to_dict()
        report["by_work_mode"] = {str(k): int(v) for k, v in wm_counts.items()}

    # --- Date coverage ---
    if "posting_date" in df.columns:
        dates = pd.to_datetime(df["posting_date"], errors="coerce")
        valid_dates = dates.dropna()
        if len(valid_dates) > 0:
            report["date_coverage"] = {
                "earliest": valid_dates.min().strftime("%Y-%m-%d"),
                "latest": valid_dates.max().strftime("%Y-%m-%d"),
                "records_with_date": int(len(valid_dates)),
                "records_without_date": int(len(dates) - len(valid_dates)),
            }
            monthly = valid_dates.dt.to_period("M").value_counts().sort_index()
            report["by_month"] = {
                str(k): int(v) for k, v in monthly.items()
            }
        else:
            report["date_coverage"] = {
                "records_with_date": 0,
                "records_without_date": int(len(dates)),
            }

    # --- Salary coverage ---
    has_salary = df["salary_max"].notna() & df["salary_max"].apply(
        lambda v: isinstance(v, (int, float))
    ) if "salary_max" in df.columns else pd.Series([False] * len(df))
    salary_count = int(has_salary.sum())
    report["salary_coverage"] = {
        "with_salary": salary_count,
        "without_salary": int(len(df) - salary_count),
        "pct_with_salary": round(salary_count / len(df) * 100, 1) if len(df) > 0 else 0,
    }
    if "salary_currency" in df.columns and salary_count > 0:
        curr_counts = (
            df.loc[has_salary, "salary_currency"]
            .value_counts()
            .to_dict()
        )
        report["salary_coverage"]["by_currency"] = {
            str(k): int(v) for k, v in curr_counts.items()
        }

    # --- Skills ---
    if "skills_list" in df.columns:
        import numpy as np
        all_skills: set[str] = set()
        total_mentions = 0
        for skills in df["skills_list"]:
            if isinstance(skills, np.ndarray):
                skills = skills.tolist()
            if isinstance(skills, (list, tuple)):
                for s in skills:
                    name = s.get("normalized_skill", "") if isinstance(s, dict) else ""
                    if name:
                        all_skills.add(name)
                        total_mentions += 1
        report["skills"] = {
            "unique_skills": len(all_skills),
            "total_mentions": total_mentions,
            "records_with_skills": int(
                df["skills_list"].apply(
                    lambda s: (
                        (isinstance(s, np.ndarray) and len(s) > 0)
                        or (isinstance(s, (list, tuple)) and len(s) > 0)
                    )
                ).sum()
            ),
        }

        # Top skills
        skill_freq: dict[str, int] = {}
        for skills in df["skills_list"]:
            if isinstance(skills, np.ndarray):
                skills = skills.tolist()
            if isinstance(skills, (list, tuple)):
                for s in skills:
                    name = s.get("normalized_skill", "") if isinstance(s, dict) else ""
                    if name:
                        skill_freq[name] = skill_freq.get(name, 0) + 1
        top_skills = sorted(skill_freq.items(), key=lambda x: -x[1])[:20]
        report["skills"]["top_skills"] = [
            {"skill": name, "count": count} for name, count in top_skills
        ]

    # --- Employment type ---
    if "employment_type" in df.columns:
        et_counts = df["employment_type"].value_counts().head(10).to_dict()
        report["by_employment_type"] = {str(k): int(v) for k, v in et_counts.items()}

    # --- City (top 20) ---
    if "city" in df.columns:
        city_counts = df["city"].value_counts().head(20).to_dict()
        report["top_cities"] = {str(k): int(v) for k, v in city_counts.items()}

    # --- DQ Score ---
    if "dq_score" in df.columns:
        scores = df["dq_score"].dropna()
        if len(scores) > 0:
            report["dq_summary"] = {
                "mean": round(float(scores.mean()), 1),
                "median": round(float(scores.median()), 1),
                "min": round(float(scores.min()), 1),
                "max": round(float(scores.max()), 1),
                "below_70": int((scores < 70).sum()),
            }

    # --- Save JSON ---
    json_path = output_dir / "coverage_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    manifest.logger.info(f"Coverage report saved: {json_path}")

    # --- Save markdown ---
    md_path = output_dir / "coverage_report.md"
    md_lines = ["# Data Coverage Report\n"]
    md_lines.append(f"**Total records:** {report['overall']['total_records']:,}")
    md_lines.append(
        f"**Unique source IDs:** {report['overall']['unique_source_job_ids']:,}"
    )
    md_lines.append("")

    for section_name, section_key in [
        ("Country Distribution", "by_country"),
        ("Source Distribution", "by_source"),
        ("Role Categories", "by_role_category"),
        ("Seniority Levels", "by_seniority"),
        ("Work Modes", "by_work_mode"),
        ("Employment Types", "by_employment_type"),
    ]:
        if section_key in report:
            md_lines.append(f"## {section_name}\n")
            for k, v in report[section_key].items():
                md_lines.append(f"- **{k}:** {v:,}")
            md_lines.append("")

    if "date_coverage" in report:
        dc = report["date_coverage"]
        md_lines.append("## Date Coverage\n")
        if "earliest" in dc:
            md_lines.append(f"- **Earliest:** {dc['earliest']}")
            md_lines.append(f"- **Latest:** {dc['latest']}")
        md_lines.append(f"- **With date:** {dc['records_with_date']:,}")
        md_lines.append(f"- **Without date:** {dc['records_without_date']:,}")
        md_lines.append("")

    sc = report.get("salary_coverage", {})
    md_lines.append("## Salary Coverage\n")
    md_lines.append(f"- **With salary:** {sc.get('with_salary', 0):,}")
    md_lines.append(f"- **Without salary:** {sc.get('without_salary', 0):,}")
    md_lines.append(f"- **% with salary:** {sc.get('pct_with_salary', 0)}%")
    md_lines.append("")

    if "skills" in report:
        sk = report["skills"]
        md_lines.append("## Skills\n")
        md_lines.append(f"- **Unique skills:** {sk['unique_skills']:,}")
        md_lines.append(f"- **Total mentions:** {sk['total_mentions']:,}")
        md_lines.append(f"- **Records with skills:** {sk['records_with_skills']:,}")
        md_lines.append("\n### Top 20 Skills\n")
        md_lines.append("| Skill | Count |")
        md_lines.append("|-------|-------|")
        for item in sk.get("top_skills", []):
            md_lines.append(f"| {item['skill']} | {item['count']:,} |")
        md_lines.append("")

    if "dq_summary" in report:
        dq = report["dq_summary"]
        md_lines.append("## DQ Score Summary\n")
        md_lines.append(f"- **Mean:** {dq['mean']}")
        md_lines.append(f"- **Median:** {dq['median']}")
        md_lines.append(f"- **Min:** {dq['min']}")
        md_lines.append(f"- **Records below 70:** {dq['below_70']:,}")
        md_lines.append("")

    if "top_cities" in report:
        md_lines.append("## Top 20 Cities\n")
        for k, v in report["top_cities"].items():
            md_lines.append(f"- **{k}:** {v:,}")
        md_lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    manifest.logger.info(f"Coverage report markdown: {md_path}")

    return report
