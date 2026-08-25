"""Complementary Python/Matplotlib analytical charts for workforce intelligence.

These charts complement the Power BI dashboard and can be used for
reports, presentations, or standalone analysis.

Usage:
    python -m analytics.charts
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

matplotlib.use("Agg")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "analytics"
OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "analytics" / "charts"
)

COLORS = {
    "uk": "#2E86AB",
    "pk": "#A23B72",
    "accent": "#F18F01",
    "alert": "#C73E1D",
    "bg": "#F5F7FA",
    "text": "#1B2A4A",
    "secondary": "#5A6B7F",
    "light": "#E8ECF1",
}

SKILL_CATEGORIES = {
    "technical": COLORS["uk"],
    "analytical": "#4A90D9",
    "ai_ml": "#6C5CE7",
    "tool": COLORS["accent"],
    "business_soft": "#00B894",
    "education": "#636E72",
}


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def _save(fig: plt.Figure, name: str) -> None:  # type: ignore[type-arg]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: charts/{name}")


def chart_skill_comparison() -> None:
    comp = _load("04_skill_comparison.csv")
    comp["total"] = comp["uk_job_count"] + comp["pk_job_count"]
    top = comp.nlargest(20, "total")
    top = top.iloc[::-1]

    fig, ax = plt.subplots(figsize=(12, 9))
    y_pos = np.arange(len(top))
    h = 0.35
    ax.barh(
        y_pos + h / 2, top["uk_penetration_pct"], h,
        label="UK (Recent 2023-2026)",
        color=COLORS["uk"], edgecolor="white", linewidth=0.5,
    )
    ax.barh(
        y_pos - h / 2, top["pk_penetration_pct"], h,
        label="PK (Historical 2019-2021)",
        color=COLORS["pk"], edgecolor="white", linewidth=0.5,
    )

    for i, (_, r) in enumerate(top.iterrows()):
        if r["uk_penetration_pct"] > 0:
            ax.text(
                r["uk_penetration_pct"] + 0.3, i + h / 2,
                f'{r["uk_penetration_pct"]:.1f}%',
                va="center", fontsize=8, color=COLORS["uk"],
            )
        if r["pk_penetration_pct"] > 0:
            ax.text(
                r["pk_penetration_pct"] + 0.3, i - h / 2,
                f'{r["pk_penetration_pct"]:.1f}%',
                va="center", fontsize=8, color=COLORS["pk"],
            )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(top["skill_name"], fontsize=9)
    ax.set_xlabel(
        "Penetration % (jobs with skill / total jobs)",
        fontsize=10, color=COLORS["text"],
    )
    ax.set_title(
        "Top 20 Skills: UK vs Pakistan Market Comparison",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "01_skill_comparison_top20.png")


def chart_role_distribution() -> None:
    roles = _load("02_role_demand.csv")
    uk = (
        roles[roles["country_code"] == "GB"]
        .groupby("role_category")["job_count"]
        .sum()
    )
    pk = (
        roles[roles["country_code"] == "PK"]
        .groupby("role_category")["job_count"]
        .sum()
    )

    all_roles = sorted(set(uk.index) | set(pk.index))
    uk_vals = [int(uk.get(r, 0)) for r in all_roles]
    pk_vals = [int(pk.get(r, 0)) for r in all_roles]

    order = sorted(
        range(len(all_roles)),
        key=lambda i: uk_vals[i] + pk_vals[i],
        reverse=True,
    )
    all_roles = [all_roles[i] for i in order]
    uk_vals = [uk_vals[i] for i in order]
    pk_vals = [pk_vals[i] for i in order]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(14, 7), gridspec_kw={"width_ratios": [1, 1]},
    )

    ax1.barh(all_roles[::-1], uk_vals[::-1], color=COLORS["uk"], edgecolor="white")
    ax1.set_title(
        "UK (Recent 2023-2026)",
        fontsize=11, fontweight="bold", color=COLORS["uk"],
    )
    ax1.set_xlabel("Job Count", fontsize=9, color=COLORS["text"])
    ax1.spines[["top", "right"]].set_visible(False)

    ax2.barh(all_roles[::-1], pk_vals[::-1], color=COLORS["pk"], edgecolor="white")
    ax2.set_title(
        "PK (Historical 2019-2021)",
        fontsize=11, fontweight="bold", color=COLORS["pk"],
    )
    ax2.set_xlabel("Job Count", fontsize=9, color=COLORS["text"])
    ax2.spines[["top", "right"]].set_visible(False)

    fig.suptitle(
        "Role Distribution by Country",
        fontsize=14, fontweight="bold", color=COLORS["text"], y=1.02,
    )
    fig.tight_layout()
    _save(fig, "02_role_distribution.png")


def chart_london_comparison() -> None:
    lon = _load("07_london_analysis.csv")

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    locs = lon["location_group"].tolist()
    colors_map = {
        "London": COLORS["uk"],
        "Greater London": "#4A90D9",
        "UK Other": COLORS["secondary"],
    }

    ax = axes[0, 0]
    vals = lon["total_jobs"].tolist()
    bars = ax.bar(
        locs, vals,
        color=[colors_map[loc] for loc in locs], edgecolor="white",
    )
    for bar_item, val in zip(bars, vals, strict=True):
        ax.text(
            bar_item.get_x() + bar_item.get_width() / 2,
            val + 20, f"{int(val):,}", ha="center", fontsize=9,
        )
    ax.set_title("Total Jobs", fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[0, 1]
    role_cols = [
        "data_analyst_jobs", "data_scientist_jobs",
        "analytics_engineer_jobs",
    ]
    role_labels = ["Data Analyst", "Data Scientist", "Analytics Engineer"]
    x_pos = np.arange(len(locs))
    w = 0.25
    for i, (col, label) in enumerate(
        zip(role_cols, role_labels, strict=True),
    ):
        ax.bar(x_pos + i * w, lon[col], w, label=label, edgecolor="white")
    ax.set_xticks(x_pos + w)
    ax.set_xticklabels(locs, fontsize=9)
    ax.set_title(
        "Data Roles by Location",
        fontsize=11, fontweight="bold", color=COLORS["text"],
    )
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1, 0]
    work_cols = [
        ("remote_jobs", "Remote", COLORS["uk"]),
        ("hybrid_jobs", "Hybrid", COLORS["accent"]),
        ("on_site_jobs", "On-Site", COLORS["secondary"]),
    ]
    for col, label, color in work_cols:
        ax.bar(locs, lon[col], label=label, color=color, edgecolor="white")
    ax.set_title("Work Mode", fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1, 1]
    sal = lon["avg_salary_midpoint"].fillna(0)
    bars = ax.bar(
        locs, sal,
        color=[colors_map[loc] for loc in locs], edgecolor="white",
    )
    for bar_item, val in zip(bars, sal, strict=True):
        if val > 0:
            ax.text(
                bar_item.get_x() + bar_item.get_width() / 2,
                val + 500, f"£{int(val):,}", ha="center", fontsize=9,
            )
    ax.set_title(
        "Avg Salary Midpoint",
        fontsize=11, fontweight="bold", color=COLORS["text"],
    )
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"£{int(x):,}"),
    )
    ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle(
        "London Intelligence",
        fontsize=14, fontweight="bold", color=COLORS["text"], y=1.01,
    )
    fig.tight_layout()
    _save(fig, "03_london_intelligence.png")


def chart_salary_distribution() -> None:
    jobs = _load("13_analytical_jobs.csv")
    uk_sal = jobs[
        (jobs["country_code"] == "GB") & jobs["salary_midpoint"].notna()
    ]["salary_midpoint"]

    fig, ax = plt.subplots(figsize=(10, 6))
    bins = [0, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 100000, 150000]
    labels = [
        "<20k", "20-30k", "30-40k", "40-50k",
        "50-60k", "60-70k", "70-80k", "80-100k", "100k+",
    ]

    hist_vals, _ = np.histogram(uk_sal, bins=bins)
    bars = ax.bar(
        labels, hist_vals,
        color=COLORS["uk"], edgecolor="white", linewidth=0.5,
    )
    for bar_item, val in zip(bars, hist_vals, strict=True):
        ax.text(
            bar_item.get_x() + bar_item.get_width() / 2,
            val + 10, str(val), ha="center", fontsize=9,
            color=COLORS["text"],
        )

    ax.set_title(
        "UK Salary Distribution (Advertised)",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Salary Range (GBP)", fontsize=10, color=COLORS["text"])
    ax.set_ylabel("Number of Jobs", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "04_salary_distribution.png")


def chart_skill_categories() -> None:
    demand = _load("03_skill_demand.csv")
    cat_total = (
        demand.groupby("skill_category")["job_count"]
        .sum()
        .sort_values(ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    cat_colors = [SKILL_CATEGORIES.get(c, "#999") for c in cat_total.index]
    bars = ax.barh(
        cat_total.index, cat_total.values,
        color=cat_colors, edgecolor="white",
    )
    for bar_item, val in zip(bars, cat_total.values, strict=True):
        ax.text(
            val + 50, bar_item.get_y() + bar_item.get_height() / 2,
            f"{val:,}", va="center", fontsize=9,
        )

    ax.set_title(
        "Skill Mentions by Category",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Total Job Mentions", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "05_skill_categories.png")


def chart_cooccurrence() -> None:
    pairs = _load("05_skill_cocurrence.csv")
    uk_pairs = pairs[pairs["country_code"] == "GB"].nlargest(
        15, "co_occurrence_count",
    )
    uk_pairs = uk_pairs.iloc[::-1]

    fig, ax = plt.subplots(figsize=(10, 7))
    pair_labels = [
        f"{r.skill_a} + {r.skill_b}" for _, r in uk_pairs.iterrows()
    ]
    vals = uk_pairs["co_occurrence_count"].tolist()

    ax.barh(pair_labels, vals, color=COLORS["uk"], edgecolor="white")
    for idx, val in enumerate(vals):
        ax.text(val + 2, idx, str(val), va="center", fontsize=9)

    ax.set_title(
        "Top 15 UK Skill Co-occurrences",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Number of Jobs", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "06_cooccurrence_top15.png")


def chart_temporal() -> None:
    temporal = _load("12_temporal_analysis.csv")
    temporal["month"] = pd.to_datetime(temporal["month"], utc=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=False)

    uk_t = temporal[temporal["country_code"] == "GB"].sort_values("month")
    pk_t = temporal[temporal["country_code"] == "PK"].sort_values("month")

    ax1.plot(
        uk_t["month"], uk_t["job_count"], marker="o",
        color=COLORS["uk"], linewidth=2, markersize=4, label="UK",
    )
    ax1.set_title(
        "UK Monthly Job Postings",
        fontsize=11, fontweight="bold", color=COLORS["uk"],
    )
    ax1.set_ylabel("Job Count", fontsize=9)
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.legend(frameon=False)
    ax1.xaxis.set_major_formatter(
        matplotlib.dates.DateFormatter("%b %Y"),
    )
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

    ax2.plot(
        pk_t["month"], pk_t["job_count"], marker="o",
        color=COLORS["pk"], linewidth=2, markersize=4, label="PK",
    )
    ax2.set_title(
        "PK Monthly Job Postings (Historical)",
        fontsize=11, fontweight="bold", color=COLORS["pk"],
    )
    ax2.set_ylabel("Job Count", fontsize=9)
    ax2.set_xlabel("Month", fontsize=10, color=COLORS["text"])
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.legend(frameon=False)
    ax2.xaxis.set_major_formatter(
        matplotlib.dates.DateFormatter("%b %Y"),
    )
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha="right")

    fig.suptitle(
        "Temporal Trends by Country",
        fontsize=14, fontweight="bold", color=COLORS["text"], y=1.01,
    )
    fig.tight_layout()
    _save(fig, "07_temporal_trends.png")


def chart_career_progression() -> None:
    rs = _load("06_role_skills.csv")
    uk_rs = rs[rs["country_code"] == "GB"]

    target_roles = ["data_analyst", "analytics_engineer", "data_scientist"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 7))

    for ax, role in zip(axes, target_roles, strict=True):
        role_data = uk_rs[uk_rs["role_category"] == role].nlargest(
            10, "penetration_pct",
        )
        role_data = role_data.iloc[::-1]
        ax.barh(
            role_data["skill_name"], role_data["penetration_pct"],
            color=COLORS["uk"], edgecolor="white",
        )
        ax.set_title(
            role.replace("_", " ").title(),
            fontsize=11, fontweight="bold", color=COLORS["text"],
        )
        ax.set_xlabel("Penetration %", fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)

    fig.suptitle(
        "UK Career Intelligence: Top Skills by Role",
        fontsize=14, fontweight="bold", color=COLORS["text"], y=1.02,
    )
    fig.tight_layout()
    _save(fig, "08_career_progression.png")


def chart_skill_salary() -> None:
    ss = _load("09_skill_salary.csv")
    uk_ss = ss[ss["country_code"] == "GB"].dropna(subset=["median_salary"])

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.scatter(
        uk_ss["job_count"], uk_ss["median_salary"],
        s=uk_ss["job_count"] * 8, alpha=0.6, c=COLORS["uk"],
        edgecolors="white", linewidth=0.5,
    )
    for _, r in uk_ss.iterrows():
        if r["job_count"] > 30 or r["median_salary"] > 55000:
            ax.annotate(
                r["skill_name"],
                (r["job_count"], r["median_salary"]),
                fontsize=7, ha="left", va="bottom", color=COLORS["text"],
            )

    ax.set_title(
        "UK Skill-Salary Association",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Jobs with Skill", fontsize=10, color=COLORS["text"])
    ax.set_ylabel("Median Salary (GBP)", fontsize=10, color=COLORS["text"])
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"£{int(x):,}"),
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "09_skill_salary.png")


def chart_employers() -> None:
    emp = _load("11_employer_analysis.csv")
    uk_emp = emp[emp["country_code"] == "GB"].nlargest(15, "job_count")

    fig, ax = plt.subplots(figsize=(10, 7))
    uk_emp = uk_emp.iloc[::-1]
    ax.barh(
        uk_emp["company_name"], uk_emp["job_count"],
        color=COLORS["uk"], edgecolor="white",
    )
    for i, (_, r) in enumerate(uk_emp.iterrows()):
        ax.text(
            r["job_count"] + 1, i, str(int(r["job_count"])),
            va="center", fontsize=9,
        )

    ax.set_title(
        "Top 15 UK Employers (Data Roles)",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Job Count", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "10_employers_top15.png")


def chart_pk_employers() -> None:
    emp = _load("11_employer_analysis.csv")
    pk_emp = emp[emp["country_code"] == "PK"].nlargest(15, "job_count")

    fig, ax = plt.subplots(figsize=(10, 7))
    pk_emp = pk_emp.iloc[::-1]
    ax.barh(
        pk_emp["company_name"], pk_emp["job_count"],
        color=COLORS["pk"], edgecolor="white",
    )
    for i, (_, r) in enumerate(pk_emp.iterrows()):
        ax.text(
            r["job_count"] + 1, i, str(int(r["job_count"])),
            va="center", fontsize=9,
        )

    ax.set_title(
        "Top 15 Pakistan Employers (Data Roles)",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Job Count", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "11_pk_employers_top15.png")


def chart_pk_cities() -> None:
    jobs = _load("13_analytical_jobs.csv")
    pk = jobs[jobs["country_code"] == "PK"]
    city_counts = pk["city"].value_counts().head(10)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(
        city_counts.index[::-1], city_counts.values[::-1],
        color=COLORS["pk"], edgecolor="white",
    )
    for bar_item, val in zip(bars, city_counts.values[::-1], strict=True):
        ax.text(
            val + 20, bar_item.get_y() + bar_item.get_height() / 2,
            f"{val:,}", va="center", fontsize=9,
        )

    ax.set_title(
        "Pakistan: Top 10 Cities by Job Postings",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Job Count", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "12_pk_cities_top10.png")


def chart_pk_skills() -> None:
    demand = _load("03_skill_demand.csv")
    pk_skills = (
        demand[demand["country_code"] == "PK"]
        .nlargest(20, "job_count")
        .iloc[::-1]
    )

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(
        pk_skills["skill_name"], pk_skills["job_count"],
        color=COLORS["pk"], edgecolor="white",
    )
    for i, (_, r) in enumerate(pk_skills.iterrows()):
        ax.text(
            r["job_count"] + 5, i,
            f'{r["job_count"]} ({r["penetration_pct"]:.1f}%)',
            va="center", fontsize=8,
        )

    ax.set_title(
        "Pakistan: Top 20 Skills by Job Count",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Job Count", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "13_pk_skills_top20.png")


def chart_pk_seniority() -> None:
    sen = _load("10_seniority_analysis.csv")
    pk_sen = sen[sen["country_code"] == "PK"].copy()
    pk_sen = pk_sen[pk_sen["seniority"] != "unknown"]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors_sen = {
        "junior": COLORS["uk"],
        "mid": COLORS["accent"],
        "senior": COLORS["pk"],
    }
    bars = ax.bar(
        pk_sen["seniority"], pk_sen["total_jobs"],
        color=[colors_sen.get(s, "#999") for s in pk_sen["seniority"]],
        edgecolor="white",
    )
    for bar_item, (_, r) in zip(bars, pk_sen.iterrows(), strict=True):
        pct = r["pct_within_country"] if "pct_within_country" in r.index else 0
        ax.text(
            bar_item.get_x() + bar_item.get_width() / 2,
            r["total_jobs"] + 50,
            f'{int(r["total_jobs"]):,}\n({pct:.1f}%)',
            ha="center", fontsize=9,
        )

    ax.set_title(
        "Pakistan: Seniority Distribution",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_ylabel("Job Count", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "14_pk_seniority.png")


def chart_pk_skill_categories() -> None:
    demand = _load("03_skill_demand.csv")
    pk_cat = (
        demand[demand["country_code"] == "PK"]
        .groupby("skill_category")["job_count"]
        .sum()
        .sort_values(ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    cat_colors = [SKILL_CATEGORIES.get(c, "#999") for c in pk_cat.index]
    bars = ax.barh(pk_cat.index, pk_cat.values, color=cat_colors, edgecolor="white")
    for bar_item, val in zip(bars, pk_cat.values, strict=True):
        ax.text(
            val + 10, bar_item.get_y() + bar_item.get_height() / 2,
            f"{val:,}", va="center", fontsize=9,
        )

    ax.set_title(
        "Pakistan: Skill Mentions by Category",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Total Job Mentions", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "15_pk_skill_categories.png")


def chart_pk_cooccurrence() -> None:
    pairs = _load("05_skill_cocurrence.csv")
    pk_pairs = pairs[pairs["country_code"] == "PK"].nlargest(10, "co_occurrence_count")
    pk_pairs = pk_pairs.iloc[::-1]

    fig, ax = plt.subplots(figsize=(10, 6))
    pair_labels = [
        f"{r.skill_a} + {r.skill_b}" for _, r in pk_pairs.iterrows()
    ]
    vals = pk_pairs["co_occurrence_count"].tolist()

    ax.barh(pair_labels, vals, color=COLORS["pk"], edgecolor="white")
    for idx, val in enumerate(vals):
        ax.text(val + 1, idx, str(val), va="center", fontsize=9)

    ax.set_title(
        "Pakistan: Top 10 Skill Co-occurrences",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Number of Jobs", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "16_pk_cooccurrence_top10.png")


def chart_pk_career_da() -> None:
    rs = _load("06_role_skills.csv")
    pk_rs = rs[(rs["country_code"] == "PK") & (rs["role_category"] == "data_analyst")]
    pk_da = pk_rs.nlargest(10, "penetration_pct").iloc[::-1]

    if pk_da.empty:
        print("    SKIPPED: No PK Data Analyst role-skill data")
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(
        pk_da["skill_name"], pk_da["penetration_pct"],
        color=COLORS["pk"], edgecolor="white",
    )
    for i, (_, r) in enumerate(pk_da.iterrows()):
        ax.text(
            r["penetration_pct"] + 0.5, i,
            f'{r["penetration_pct"]:.1f}%',
            va="center", fontsize=9,
        )

    ax.set_title(
        "Pakistan: Data Analyst Skill Profile",
        fontsize=13, fontweight="bold", color=COLORS["text"], pad=15,
    )
    ax.set_xlabel("Penetration %", fontsize=10, color=COLORS["text"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["bg"])
    fig.patch.set_facecolor("white")
    _save(fig, "17_pk_career_data_analyst.png")


BI_DARK = "#0D0D0D"
BI_GOLD = "#B8860B"
BI_IVORY = "#F5F1E8"
BI_CARD = "#1A1A1A"
BI_BORDER = "#2A2A2A"
BI_TEXT = "#F5F1E8"
BI_SECONDARY = "#7A7A7A"


def _bi_kpi_card(ax, x, y, value, label, w=0.18, h=0.28):
    ax.add_patch(plt.Rectangle((x, y), w, h, transform=ax.transAxes,
                               facecolor=BI_CARD, edgecolor=BI_BORDER, linewidth=1,
                               clip_on=False, zorder=2))
    ax.text(x + w / 2, y + h * 0.62, value, transform=ax.transAxes,
            ha="center", va="center", fontsize=14, fontweight="bold",
            color=BI_GOLD, fontfamily="sans-serif", zorder=3)
    ax.text(x + w / 2, y + h * 0.28, label, transform=ax.transAxes,
            ha="center", va="center", fontsize=7, color=BI_SECONDARY,
            fontfamily="sans-serif", zorder=3)


def _bi_bar(ax, labels, values, colors, title, max_val=None):
    ax.set_facecolor(BI_CARD)
    ax.set_title(title, fontsize=9, fontweight="bold", color=BI_TEXT, pad=6)
    y_pos = np.arange(len(labels))
    if max_val is None:
        max_val = max(values) * 1.15 if values else 1
    for i, (_lbl, val, c) in enumerate(zip(labels, values, colors, strict=True)):
        ax.barh(i, val, color=c, edgecolor="none", height=0.6)
        ax.text(val + max_val * 0.02, i, f"{val:,.0f}", va="center",
                fontsize=7, color=BI_TEXT)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=7, color=BI_TEXT)
    ax.set_xlim(0, max_val)
    ax.spines[:].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    ax.invert_yaxis()


def chart_bi_executive_overview():
    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor(BI_DARK)
    ax.set_facecolor(BI_DARK)
    ax.axis("off")
    ax.text(0.5, 0.96, "Executive Workforce Overview", transform=ax.transAxes,
            ha="center", va="top", fontsize=16, fontweight="bold", color=BI_GOLD)
    ax.text(0.5, 0.91, "UK (2023\u20132026) + Pakistan (2019\u20132021)  \u2022  8,256 Total Jobs",
            transform=ax.transAxes, ha="center", va="top", fontsize=9, color=BI_SECONDARY)
    _bi_kpi_card(ax, 0.04, 0.56, "8,256", "Total Jobs", 0.18, 0.28)
    _bi_kpi_card(ax, 0.25, 0.56, "3,029", "UK Postings", 0.18, 0.28)
    _bi_kpi_card(ax, 0.46, 0.56, "5,227", "PK Postings", 0.18, 0.28)
    _bi_kpi_card(ax, 0.67, 0.56, "77", "Unique Skills", 0.18, 0.28)
    _bi_kpi_card(ax, 0.04, 0.20, "3,886", "Companies", 0.18, 0.28)
    _bi_kpi_card(ax, 0.25, 0.20, "193", "Cities", 0.18, 0.28)
    _bi_kpi_card(ax, 0.46, 0.20, "\u00a363,393", "UK Median Salary", 0.18, 0.28)
    _bi_kpi_card(ax, 0.67, 0.20, "99.6%", "UK Salary Coverage", 0.18, 0.28)
    ax.text(
        0.5, 0.14, "\u2500" * 80, transform=ax.transAxes,
        ha="center", color=BI_BORDER, fontsize=6,
    )
    footer = (
        "Interactive dashboard with slicers for Country, Role,"
        " Seniority, Location  \u2022  DAX: 50+ measures"
        "  \u2022  Star schema model"
    )
    ax.text(
        0.5, 0.08, footer, transform=ax.transAxes,
        ha="center", fontsize=7, color=BI_SECONDARY,
    )
    _save(fig, "bi_01_executive_overview.png")


def chart_bi_uk_market():
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.patch.set_facecolor(BI_DARK)
    fig.suptitle("UK Job Market", fontsize=14, fontweight="bold", color=BI_GOLD, y=0.98)
    fig.text(0.5, 0.945, "Adzuna API  \u2022  2023\u20132026  \u2022  3,029 Postings",
             ha="center", fontsize=8, color=BI_SECONDARY)
    for row in axes:
        for a in row:
            a.set_facecolor(BI_CARD)
    ax = axes[0, 0]
    _bi_kpi_card(ax, 0.0, 0.3, "3,029", "UK Jobs", 0.4, 0.55)
    _bi_kpi_card(ax, 0.5, 0.3, "999", "Employers", 0.4, 0.55)
    ax.axis("off")
    ax.set_title("", pad=0)
    ax = axes[0, 1]
    roles = ["Data Analyst", "Other Data-Adjacent", "Data Scientist", "Analytics Engineer", "Other"]
    role_vals = [738, 1454, 382, 289, 166]
    _bi_bar(ax, roles, role_vals, [BI_GOLD]*5, "Role Distribution")
    ax = axes[1, 0]
    skills = ["Reporting", "Machine Learning", "Leadership", "Python", "SQL"]
    skill_vals = [330, 230, 139, 133, 106]
    _bi_bar(ax, skills, skill_vals, [BI_GOLD]*5, "Top 5 Skills (Penetration %)")
    for i, v in enumerate([10.9, 7.6, 4.6, 4.4, 3.5]):
        ax.text(skill_vals[i] + 5, i, f"{v}%", va="center", fontsize=7, color=BI_GOLD)
    ax = axes[1, 1]
    sen = ["Junior", "Senior", "Unknown", "Mid"]
    sen_vals = [1509, 482, 657, 381]
    _bi_bar(ax, sen, sen_vals, [BI_GOLD]*4, "Seniority")
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    ax_last = fig.add_axes([0.0, 0.01, 1.0, 0.03])
    ax_last.set_facecolor(BI_DARK)
    ax_last.axis("off")
    ax_last.text(
        0.5, 0.5,
        "Slicers: Role Category \u2022 Seniority"
        " \u2022 Location Group \u2022 Work Mode",
        ha="center", va="center", fontsize=7, color=BI_SECONDARY,
    )
    _save(fig, "bi_02_uk_market.png")


def chart_bi_pk_market():
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.patch.set_facecolor(BI_DARK)
    fig.suptitle("Pakistan Job Market", fontsize=14, fontweight="bold", color=BI_GOLD, y=0.98)
    fig.text(0.5, 0.945, "CHISEL/LUMS  \u2022  Dec 2019 \u2013 Mar 2021  \u2022  5,227 Postings",
             ha="center", fontsize=8, color=BI_SECONDARY)
    for row in axes:
        for a in row:
            a.set_facecolor(BI_CARD)
    ax = axes[0, 0]
    _bi_kpi_card(ax, 0.0, 0.3, "5,227", "PK Jobs", 0.4, 0.55)
    _bi_kpi_card(ax, 0.5, 0.3, "2,890", "Employers", 0.4, 0.55)
    ax.axis("off")
    ax.set_title("", pad=0)
    ax = axes[0, 1]
    cities = ["Lahore", "Islamabad", "Karachi", "Rawalpindi", "Faisalabad"]
    city_vals = [1662, 1487, 1323, 157, 98]
    _bi_bar(ax, cities, city_vals, [BI_GOLD]*5, "Top 5 Cities")
    ax = axes[1, 0]
    skills = ["PHP", "Communication", "JavaScript", "HTML", "C#"]
    skill_vals = [386, 261, 203, 121, 117]
    _bi_bar(ax, skills, skill_vals, [BI_GOLD]*5, "Top 5 Skills")
    for i, v in enumerate([7.4, 5.0, 3.9, 2.3, 2.2]):
        ax.text(skill_vals[i] + 5, i, f"{v}%", va="center", fontsize=7, color=BI_GOLD)
    ax = axes[1, 1]
    sen = ["Junior", "Mid", "Senior", "Unknown"]
    sen_vals = [3942, 1113, 66, 106]
    _bi_bar(ax, sen, sen_vals, [BI_GOLD]*4, "Seniority")
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    ax_last = fig.add_axes([0.0, 0.01, 1.0, 0.03])
    ax_last.set_facecolor(BI_DARK)
    ax_last.axis("off")
    ax_last.text(0.5, 0.5, "Slicers: City \u2022 Seniority \u2022 Skill Category",
                 ha="center", va="center", fontsize=7, color=BI_SECONDARY)
    _save(fig, "bi_03_pk_market.png")


def chart_bi_comparison():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor(BI_DARK)
    fig.suptitle("UK vs Pakistan Comparison", fontsize=14, fontweight="bold", color=BI_GOLD, y=0.99)
    fig.text(
        0.5, 0.94,
        "Dataset-based comparison  \u2022"
        "  UK (2023\u20132026) vs PK (2019\u20132021)",
        ha="center", fontsize=8, color=BI_SECONDARY,
    )
    for a in axes:
        a.set_facecolor(BI_CARD)
    ax = axes[0]
    labels = ["UK", "Pakistan"]
    vals = [3029, 5227]
    bars = ax.bar(labels, vals, color=[BI_GOLD, BI_SECONDARY], edgecolor="none", width=0.5)
    for b, v in zip(bars, vals, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, v + 80, f"{v:,}", ha="center",
                fontsize=11, fontweight="bold", color=BI_TEXT)
    ax.set_title("Total Jobs by Market", fontsize=10, fontweight="bold", color=BI_TEXT, pad=8)
    ax.spines[:].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=False, labelleft=False)
    ax.set_ylim(0, 6500)
    ax = axes[1]
    cats = ["Technical", "Business-Soft", "AI/ML", "Tool", "Analytical"]
    uk_c = [2180, 386, 195, 166, 75]
    pk_c = [1139, 421, 27, 200, 0]
    y = np.arange(len(cats))
    h = 0.35
    ax.barh(y + h/2, uk_c, h, color=BI_GOLD, label="UK")
    ax.barh(y - h/2, pk_c, h, color=BI_SECONDARY, label="PK")
    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=8, color=BI_TEXT)
    ax.set_title("Skill Category Comparison", fontsize=10, fontweight="bold", color=BI_TEXT, pad=8)
    ax.legend(frameon=False, fontsize=8, labelcolor=BI_TEXT, loc="lower right")
    ax.spines[:].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    fig.tight_layout(rect=[0, 0.04, 1, 0.91])
    ax_last = fig.add_axes([0.0, 0.01, 1.0, 0.03])
    ax_last.set_facecolor(BI_DARK)
    ax_last.axis("off")
    ax_last.text(
        0.5, 0.5,
        "Slicers: Country \u2022 Role Category"
        " \u2022 Skill Category \u2022 Seniority",
        ha="center", va="center", fontsize=7, color=BI_SECONDARY,
    )
    _save(fig, "bi_04_comparison.png")


def chart_bi_london():
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.patch.set_facecolor(BI_DARK)
    fig.suptitle("London Deep Dive", fontsize=14, fontweight="bold", color=BI_GOLD, y=0.98)
    fig.text(
        0.5, 0.945,
        "UK Geographic Sub-Analysis  \u2022"
        "  London vs Greater London vs UK Other",
        ha="center", fontsize=8, color=BI_SECONDARY,
    )
    for row in axes:
        for a in row:
            a.set_facecolor(BI_CARD)
    ax = axes[0, 0]
    _bi_kpi_card(ax, 0.0, 0.3, "2,312", "London Jobs", 0.4, 0.55)
    _bi_kpi_card(ax, 0.5, 0.3, "76.3%", "UK Share", 0.4, 0.55)
    ax.axis("off")
    ax.set_title("", pad=0)
    ax = axes[0, 1]
    locs = ["London", "Greater London", "UK Other"]
    loc_vals = [2312, 513, 204]
    _bi_bar(ax, locs, loc_vals, [BI_GOLD, "#4A4A4A", "#7A7A7A"], "Jobs by Location")
    ax = axes[1, 0]
    roles = ["Data Analyst", "Data Scientist", "Analytics Engineer", "Other"]
    role_vals = [576, 308, 237, 1191]
    _bi_bar(ax, roles, role_vals, [BI_GOLD]*4, "Data Roles (London)")
    ax = axes[1, 1]
    modes = ["Remote", "Hybrid", "On-Site"]
    mode_vals = [1541, 632, 139]
    _bi_bar(ax, modes, mode_vals, [BI_GOLD, "#4A4A4A", "#7A7A7A"], "Work Mode")
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    ax_last = fig.add_axes([0.0, 0.01, 1.0, 0.03])
    ax_last.set_facecolor(BI_DARK)
    ax_last.axis("off")
    ax_last.text(
        0.5, 0.5,
        "Slicers: Location Group \u2022 Role Category"
        "  \u2022  Drill-down: London \u2192 boroughs",
        ha="center", va="center", fontsize=7, color=BI_SECONDARY,
    )
    _save(fig, "bi_05_london.png")


def chart_bi_career():
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.patch.set_facecolor(BI_DARK)
    fig.suptitle("Career Intelligence", fontsize=14, fontweight="bold", color=BI_GOLD, y=0.99)
    fig.text(0.5, 0.94, "Market-derived skill profiles  \u2022  Select role and market to explore",
             ha="center", fontsize=8, color=BI_SECONDARY)
    roles_data = [
        ("Data Analyst", ["SQL", "Python", "Reporting", "Excel", "Tableau"],
         [34.5, 29.0, 23.1, 19.6, 15.6]),
        ("Analytics Engineer", ["SQL", "Python", "dbt", "Airflow", "Data Modeling"],
         [45.7, 36.3, 17.3, 14.2, 12.8]),
        ("Data Scientist", ["Python", "Machine Learning", "SQL", "TensorFlow", "Deep Learning"],
         [48.2, 41.9, 25.7, 14.7, 12.6]),
    ]
    for ax, (role, skills, vals) in zip(axes, roles_data, strict=True):
        ax.set_facecolor(BI_CARD)
        _bi_bar(ax, skills, vals, [BI_GOLD]*5, role)
        for i, v in enumerate(vals):
            ax.text(vals[i] + 1.5, i, f"{v}%", va="center", fontsize=7, color=BI_GOLD)
    fig.tight_layout(rect=[0, 0.06, 1, 0.91])
    ax_last = fig.add_axes([0.0, 0.01, 1.0, 0.04])
    ax_last.set_facecolor(BI_DARK)
    ax_last.axis("off")
    ax_last.text(
        0.5, 0.5,
        "Slicers: Target Role \u2022 Country (UK/PK)"
        " \u2022 Seniority  \u2022  Explore:"
        " Skills \u2192 Salary \u2192 Demand",
        ha="center", va="center", fontsize=7, color=BI_SECONDARY,
    )
    _save(fig, "bi_06_career.png")


ALL_CHARTS = [
    ("Skill Comparison (Top 20)", chart_skill_comparison),
    ("Role Distribution", chart_role_distribution),
    ("London Intelligence", chart_london_comparison),
    ("Salary Distribution", chart_salary_distribution),
    ("Skill Categories", chart_skill_categories),
    ("Co-occurrence", chart_cooccurrence),
    ("Temporal Trends", chart_temporal),
    ("Career Progression", chart_career_progression),
    ("Skill-Salary", chart_skill_salary),
    ("UK Employers", chart_employers),
    ("PK Employers", chart_pk_employers),
    ("PK Cities", chart_pk_cities),
    ("PK Skills", chart_pk_skills),
    ("PK Seniority", chart_pk_seniority),
    ("PK Skill Categories", chart_pk_skill_categories),
    ("PK Co-occurrence", chart_pk_cooccurrence),
    ("PK Data Analyst Career", chart_pk_career_da),
    ("BI: Executive Overview", chart_bi_executive_overview),
    ("BI: UK Market", chart_bi_uk_market),
    ("BI: Pakistan Market", chart_bi_pk_market),
    ("BI: Comparison", chart_bi_comparison),
    ("BI: London", chart_bi_london),
    ("BI: Career Intelligence", chart_bi_career),
]


def main() -> None:
    print("Generating complementary analytical charts...")
    print(f"  Output: {OUTPUT_DIR}\n")
    for name, fn in ALL_CHARTS:
        print(f"  [{name}]")
        try:
            fn()
        except Exception as exc:
            print(f"    FAILED: {exc}")
    chart_count = len(list(OUTPUT_DIR.glob("*.png")))
    print(f"\nDone. {chart_count} charts generated.")


if __name__ == "__main__":
    main()
