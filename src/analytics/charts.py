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
    ("Employer Concentration", chart_employers),
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
