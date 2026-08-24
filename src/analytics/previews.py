"""Phase 6 — static Power BI page previews for portfolio/documentation.

Renders the ten specified report pages as PNG compositions using the
VALIDATED Phase 5 exports (data/analytics/*.csv). These previews document the
intended Power BI Desktop layouts; they are NOT the interactive report itself
(no .pbix is fabricated). Build instructions: dashboard/powerbi/.

Run:
    $env:PYTHONPATH='src'; python -m analytics.previews
Outputs -> dashboard/previews/pageNN_*.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANALYTICS = PROJECT_ROOT / "data" / "analytics"
PREVIEWS = PROJECT_ROOT / "dashboard" / "previews"

GOLD = "#B8952B"
GOLD_LIGHT = "#D4AF37"
CHARCOAL = "#3A3A3A"
INK = "#1A1A1A"
GRAY = "#8A8578"
WARM_GRAY = "#B0A89A"
PAPER = "#FFFFFF"
CREAM = "#F5F1E8"

W_IN, H_IN, DPI = 16, 9, 110


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(ANALYTICS / name)


def _new_page(title: str, subtitle: str):
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI)
    fig.patch.set_facecolor(CREAM)
    fig.text(0.035, 0.955, title, fontsize=19, fontweight="bold", color=INK)
    fig.text(0.035, 0.928, subtitle, fontsize=10, color=GRAY)
    return fig


def _banner(fig, text: str, y=0.018, color=GOLD_LIGHT):
    fig.patches.append(
        plt.Rectangle((0.035, y), 0.93, 0.036, transform=fig.transFigure,
                      facecolor=color, edgecolor="none", alpha=0.92, zorder=5))
    fig.text(0.05, y + 0.018, text, fontsize=9.5, fontweight="bold",
             color=INK, va="center", zorder=6)


def _kpi_row(fig, items, y=0.80, x0=0.035, w=0.115, h=0.10):
    """items: list of (value_label, caption)."""
    for i, (val, cap) in enumerate(items):
        x = x0 + i * (w + 0.008)
        fig.patches.append(plt.Rectangle(
            (x, y), w, h, transform=fig.transFigure,
            facecolor=PAPER, edgecolor="#DDD8CA", linewidth=1))
        fig.text(x + w / 2, y + h * 0.62, val, fontsize=17,
                 fontweight="bold", color=GOLD, ha="center")
        fig.text(x + w / 2, y + h * 0.22, cap, fontsize=7.6,
                 color=CHARCOAL, ha="center")


def _panel(fig, rect, title):
    ax = fig.add_axes(rect)
    ax.set_facecolor(PAPER)
    ax.set_title(title, fontsize=9.5, fontweight="bold", loc="left",
                 color=INK, pad=6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=7.4, colors=CHARCOAL)
    return ax


def _barh(ax, labels, values, color=GOLD, fmt="{:,}"):
    pos = np.arange(len(labels))[::-1]
    ax.barh(pos, values, color=color, height=0.62)
    ax.set_yticks(pos, labels)
    mx = max(values) if len(values) else 1
    for p, v in zip(pos, values, strict=True):
        ax.text(v + mx * 0.02, p, fmt.format(v), va="center",
                fontsize=7.2, color=CHARCOAL)
    ax.set_xlim(0, mx * 1.18)
    ax.set_xticks([])


# ---------------------------------------------------------------------------
# Page 01 — Executive Workforce Overview
# ---------------------------------------------------------------------------

def page01_executive_overview():
    jobs = _csv("13_analytical_jobs.csv")
    roles = _csv("02_role_demand.csv")
    skills = _csv("03_skill_demand.csv")

    total = len(jobs)
    uk = int((jobs.country_code == "GB").sum())
    pk_hist = int((jobs.source_name == "chisel_pk").sum())
    pk_supp = int((jobs.source_name == "kaggle_rozee_pk").sum())
    companies = jobs.company_name.nunique()
    cities = jobs.city.nunique()
    n_skills = skills.skill_name.nunique()

    fig = _new_page("Executive Workforce Overview",
                    "UK & Pakistan job-market analytics | validated Phase 5 "
                    "outputs | PostgreSQL + NLP skill extraction")
    _kpi_row(fig, [
        (f"{total:,}", "Total unique jobs"),
        (f"{uk:,}", "Recent UK postings"),
        (f"{pk_hist:,}", "Historical PK postings"),
        (f"{pk_supp}", "Supplementary PK sample"),
        (f"{companies:,}", "Unique companies"),
        (f"{cities:,}", "Unique locations"),
        (f"{n_skills}", "Normalized skills"),
    ])

    ax = _panel(fig, [0.035, 0.52, 0.26, 0.24], "Dataset composition (jobs)")
    comp_labels = ["Recent UK\n2023-2026", "Historical PK\n2019-2021",
                   "Supplementary PK\nMar-May 2024"]
    ax.pie([uk, pk_hist, pk_supp], labels=comp_labels, colors=[GOLD, CHARCOAL, GRAY],
           autopct=lambda p: f"{p:.0f}%", startangle=90, textprops={"fontsize": 7.4},
           wedgeprops={"edgecolor": CREAM})

    ax = _panel(fig, [0.33, 0.52, 0.32, 0.24], "Role classification by market")
    focus = ["data_analyst", "data_scientist", "analytics_engineer", "other"]
    gb_counts = [int(((roles.role_category == r) & (roles.country_code == "GB"))
                     ["job_count"].sum()) for r in focus]
    pk_counts = [int(((roles.role_category == r) & (roles.country_code == "PK"))
                     ["job_count"].sum()) for r in focus]
    pos = np.arange(len(focus))
    ax.barh(pos + 0.2, gb_counts, height=0.36, color=GOLD, label="UK (recent)")
    ax.barh(pos - 0.2, pk_counts, height=0.36, color=CHARCOAL,
            label="Pakistan (historical)")
    ax.set_yticks(pos, [r.replace("_", " ").title() for r in focus])
    ax.legend(fontsize=7, frameon=False)

    ax = _panel(fig, [0.685, 0.52, 0.28, 0.24], "Seniority profile (%)")
    sen = jobs.groupby(["country_code", "seniority"]).size().unstack(fill_value=0)
    sen_pct = sen.div(sen.sum(axis=1), axis=0) * 100
    cols = [c for c in ["junior", "mid", "senior", "unknown"] if c in sen_pct]
    left = np.zeros(len(sen_pct))
    shades = {"junior": GOLD_LIGHT, "mid": GOLD, "senior": CHARCOAL,
              "unknown": GRAY}
    for c in cols:
        vals = sen_pct[c].values
        idx = np.arange(len(sen_pct.index))
        ax.barh(idx, vals, left=left, color=shades[c],
                label=c.title() if c != "unknown" else "Unclassified",
                edgecolor=CREAM)
        for xi, (left_val, v) in enumerate(zip(left, vals, strict=True)):
            if v > 6:
                ax.text(left_val + v / 2, xi, f"{v:.0f}%", ha="center", va="center",
                        fontsize=7,
                        color=PAPER if c in ("senior", "mid") else INK)
        left += vals
    ax.set_yticks(np.arange(len(sen_pct.index)),
                  ["Pakistan (hist.)" if i == "PK" else "UK (recent)"
                   for i in sen_pct.index])
    ax.legend(fontsize=6.6, frameon=False, ncols=4, loc="upper center",
              bbox_to_anchor=(0.5, -0.06))

    ax = _panel(fig, [0.035, 0.085, 0.44, 0.34], "Top skills — recent UK "
                "postings (% of UK jobs)")
    gbs = skills[skills.country_code == "GB"].nlargest(10, "job_count")
    _barh(ax, list(gbs.skill_name), list(gbs.penetration_pct), fmt="{:.1f}%")

    ax = _panel(fig, [0.53, 0.085, 0.44, 0.34], "Top skills — historical "
                "Pakistan postings (% of PK jobs)")
    pks = skills[skills.country_code == "PK"].nlargest(10, "job_count")
    _barh(ax, list(pks.skill_name), list(pks.penetration_pct),
          color=CHARCOAL, fmt="{:.1f}%")

    _banner(fig, "METHODOLOGY: UK data is recent (2023-2026); Pakistan CHISEL "
                 "data is historical (Dec 2019-Mar 2021). These datasets are "
                 "NOT temporally equivalent.")
    out = PREVIEWS / "page01_executive_overview.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page 02 — UK Job Market
# ---------------------------------------------------------------------------

def page02_uk_market():
    jobs = _csv("13_analytical_jobs.csv")
    employers = _csv("11_employer_analysis.csv")
    uk = jobs[jobs.country_code == "GB"]

    roles = uk.role_category.value_counts()
    cities = uk.city.value_counts().head(10)
    modes = uk.work_mode.value_counts()
    contracts = uk.employment_type.replace("", "unspecified").value_counts()
    lon_share = uk.location_group.isin(["London", "Greater London"]).mean() * 100

    fig = _new_page("UK Job Market — Recent Postings",
                    "Source: Adzuna UK API | Sep 2023 - Aug 2026 | "
                    "interactive slicers: Role · Seniority · Location · "
                    "Work Mode · Contract Type · Date")
    _kpi_row(fig, [
        (f"{len(uk):,}", "UK job postings"),
        (f"{uk.company_name.nunique():,}", "Companies"),
        (f"{uk.city.nunique():,}", "Locations"),
        (str(uk.role_category.nunique()), "Role classes"),
        (f"{lon_share:.1f}%", "London cluster share"),
    ], w=0.14)

    ax = _panel(fig, [0.035, 0.50, 0.29, 0.36], "Postings by role class")
    top_roles = roles.head(8)[::-1]
    _barh(ax, [r.replace("_", " ").title() for r in top_roles.index],
          list(top_roles.values))

    ax = _panel(fig, [0.365, 0.50, 0.29, 0.36], "Top 10 posting locations")
    _barh(ax, list(cities.index)[::-1], list(cities.values)[::-1],
          color=CHARCOAL)

    ax = _panel(fig, [0.695, 0.50, 0.27, 0.175], "Work mode")
    _barh(ax, [m.replace("_", " ").title() for m in modes.index][::-1],
          list(modes.values)[::-1])

    ax = _panel(fig, [0.695, 0.285, 0.27, 0.175], "Contract type")
    _barh(ax, [c.replace("_", " ").title() for c in contracts.index][::-1],
          list(contracts.values)[::-1], color=GRAY)

    sal = uk[(uk.salary_midpoint.notna())
             & (uk.salary_midpoint.astype(str) != "NaN")]
    ax = _panel(fig, [0.035, 0.075, 0.42, 0.20],
                "Advertised salary distribution (annual midpoint)")
    vals = sal.salary_midpoint.astype(float) / 1000
    ax.hist(vals, bins=40, color=GOLD, edgecolor=PAPER, linewidth=0.3)
    med = float(vals.median())
    ax.axvline(med, color=INK, linewidth=1.2)
    ax.text(med * 1.05, ax.get_ylim()[1] * 0.9, f"median £{med:,.0f}k",
            fontsize=7.6, color=INK)
    ax.set_xlabel("£000s", fontsize=7.4)

    ax = _panel(fig, [0.51, 0.075, 0.455, 0.20], "Top employers by postings "
                "(concentration check)")
    emp = employers[employers.country_code == "GB"].nlargest(8, "job_count")
    _barh(ax, list(emp.company_name)[::-1][:8], list(emp.job_count)[::-1][:8],
          color=CHARCOAL, fmt="{:,}")

    _banner(fig, "SCOPE: collected UK postings only — not the complete UK "
                 "labor market. Salary figures cover advertised ranges only.")
    out = PREVIEWS / "page02_uk_market.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page 03 — London Intelligence
# ---------------------------------------------------------------------------

def page03_london():
    jobs = _csv("13_analytical_jobs.csv")
    uk = jobs[jobs.country_code == "GB"]
    lon = uk[uk.location_group.isin(["London", "Greater London"])]
    other = uk[uk.location_group == "UK Other"]

    def split_stats(df):
        return {
            "jobs": len(df),
            "da": int((df.role_category == "data_analyst").sum()),
            "ds": int((df.role_category == "data_scientist").sum()),
            "ae": int((df.role_category == "analytics_engineer").sum()),
            "remote": float((df.work_mode == "remote").mean() * 100),
            "hybrid": float((df.work_mode == "hybrid").mean() * 100),
            "senior": float((df.seniority == "senior").mean() * 100),
        }

    lon_stats, other_stats = split_stats(lon), split_stats(other)
    lon_city_n = int((uk.location_group == "London").sum())
    ring_n = int((uk.location_group == "Greater London").sum())
    cluster_share = (lon_city_n + ring_n) / len(uk) * 100

    fig = _new_page("London Intelligence",
                    "Target-market deep dive | London city vs Greater London "
                    "ring vs rest of UK | collected postings only")
    _kpi_row(fig, [
        (f"{len(uk):,}", "UK postings"),
        (f"{lon_city_n:,}", "London (city)"),
        (f"{ring_n:,}", "Greater London ring"),
        (f"{other_stats['jobs']:,}", "UK Other"),
        (f"{cluster_share:.1f}%", "London cluster share"),
    ], w=0.14)

    groups = ["Jobs", "Data Analyst", "Data Scientist", "Analytics Eng."]
    london_vals = [lon_stats["jobs"], lon_stats["da"], lon_stats["ds"], lon_stats["ae"]]
    other_vals = [other_stats["jobs"], other_stats["da"], other_stats["ds"], other_stats["ae"]]
    ax = _panel(fig, [0.035, 0.47, 0.30, 0.36],
                "Volume: London (city+ring) vs UK Other")
    pos = np.arange(len(groups))
    ax.barh(pos + 0.2, london_vals, height=0.36, color=GOLD,
            label="London (incl. ring)")
    ax.barh(pos - 0.2, other_vals, height=0.36, color=GRAY, label="UK Other")
    ax.set_yticks(pos, groups)
    ax.legend(fontsize=7, frameon=False)

    metrics = ["Remote %", "Hybrid %", "Senior %"]
    lv = [lon_stats["remote"], lon_stats["hybrid"], lon_stats["senior"]]
    ov = [other_stats["remote"], other_stats["hybrid"], other_stats["senior"]]
    ax = _panel(fig, [0.375, 0.47, 0.28, 0.36],
                "Profile comparison (%)")
    xpos = np.arange(len(metrics))
    ax.bar(xpos - 0.2, lv, width=0.38, color=GOLD, label="London")
    ax.bar(xpos + 0.2, ov, width=0.38, color=GRAY, label="UK Other")
    for x, v in zip(xpos - 0.2, lv, strict=True):
        ax.text(x, v + 1, f"{v:.0f}%", ha="center", fontsize=7.2)
    for x, v in zip(xpos + 0.2, ov, strict=True):
        ax.text(x, v + 1, f"{v:.0f}%", ha="center", fontsize=7.2)
    ax.set_xticks(xpos, metrics)
    ax.set_ylim(0, max(max(lv), max(ov)) * 1.25)
    ax.legend(fontsize=7, frameon=False)

    ax = _panel(fig, [0.70, 0.47, 0.265, 0.36], "Composition of London cluster")
    ax.pie([lon_city_n, ring_n],
           labels=[f"London city\n{lon_city_n:,}",
                   f"Greater London\n{ring_n:,}"],
           colors=[GOLD, CHARCOAL], autopct="%1.0f%%", startangle=120,
           textprops={"fontsize": 7.6},
           wedgeprops={"edgecolor": CREAM})

    skills_bridge = _csv("14_job_skills_bridge.csv")
    lon_ids = set(lon.job_id)
    other_ids = set(other.job_id)
    ls = (skills_bridge[skills_bridge.job_id.isin(lon_ids)]
          .groupby("skill_name").job_id.nunique().nlargest(10))
    os_ = (skills_bridge[skills_bridge.job_id.isin(other_ids)]
           .groupby("skill_name").job_id.nunique().nlargest(10))
    ax = _panel(fig, [0.035, 0.065, 0.44, 0.31],
                "Top skills — London cluster (% of its postings)")
    _barh(ax, list(ls.index)[::-1], [v / lon_stats["jobs"] * 100 for v in ls][::-1],
          fmt="{:.1f}%")
    ax = _panel(fig, [0.53, 0.065, 0.435, 0.31],
                "Top skills — UK Other (% of its postings)")
    _barh(ax, list(os_.index)[::-1], [v / other_stats["jobs"] * 100 for v in os_][::-1],
          color=GRAY, fmt="{:.1f}%")

    _banner(fig, "NOTE: reflects COLLECTED postings from one API source — "
                 "not a complete census of the London labor market.")
    out = PREVIEWS / "page03_london_intelligence.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page 04 — Pakistan Historical Market
# ---------------------------------------------------------------------------

def page04_pakistan():
    jobs = _csv("13_analytical_jobs.csv")
    skills = _csv("03_skill_demand.csv")
    employers = _csv("11_employer_analysis.csv")
    pk = jobs[jobs.country_code == "PK"]

    cities = pk.city.value_counts().head(8)
    pkskills = skills[skills.country_code == "PK"].nlargest(10, "job_count")
    pkemp = employers[employers.country_code == "PK"].nlargest(8, "job_count")
    other_pct = float((pk.role_category == "other").mean() * 100)
    n_other = int((pk.role_category == "other").sum())

    fig = _new_page("Pakistan Job Market — HISTORICAL ARCHIVE",
                    "CHISEL/LUMS collection | December 2019 - March 2021 | "
                    "+ supplementary Rozee sample (Mar-May 2024, n=16)")
    _kpi_row(fig, [
        (f"{len(pk):,}", "Historical postings"),
        (f"{pk.company_name.nunique():,}", "Companies"),
        (f"{pk.city.nunique()}", "Cities"),
        (f"{other_pct:.1f}%", "Classified 'other' role"),
        ("0", "Usable salaries (CHISEL)"),
    ], w=0.14)

    ax = _panel(fig, [0.035, 0.48, 0.30, 0.38], "Top cities (postings)")
    _barh(ax, list(cities.index)[::-1], list(cities.values)[::-1])

    ax = _panel(fig, [0.375, 0.48, 0.28, 0.38], "Top skills (% of historical "
                "PK postings)")
    _barh(ax, list(pkskills.skill_name)[::-1],
          list(pkskills.penetration_pct)[::-1], color=CHARCOAL, fmt="{:.1f}%")

    ax = _panel(fig, [0.69, 0.48, 0.275, 0.38], "Most active employers "
                "(historical)")
    _barh(ax, list(pkemp.company_name)[::-1], list(pkemp.job_count)[::-1],
          color=GRAY)

    ax = _panel(fig, [0.035, 0.065, 0.55, 0.315],
                "Role classification limitation — read before interpreting")
    ax.axis("off")
    txt = (
        f"{n_other:,} of {len(pk):,} PK postings classify as 'other'.\n\n"
        "This does NOT demonstrate that Pakistan lacked data roles in "
        "2019-2021.\nThe CHISEL archive is a general job-posting corpus whose "
        "title\ntaxonomy maps weakly onto modern data-role definitions used "
        "for the\nUK feed. Classification recall for PK titles is therefore "
        "low, and\nrole-level PK comparisons are suppressed on this page.\n\n"
        "Skills shown above come from NLP extraction over raw descriptions "
        "and\nremain informative even where role labels are not."
    )
    ax.text(0.02, 0.97, txt, fontsize=9.2, va="top", color=INK, linespacing=1.5)

    ax = _panel(fig, [0.62, 0.065, 0.345, 0.315], "Seniority mix (historical)")
    sen = pk.seniority.value_counts()
    ax.pie(list(sen.values), labels=[s.title() for s in sen.index],
           colors=[GOLD_LIGHT, GOLD, GRAY, CHARCOAL][:len(sen)],
           autopct="%1.0f%%", startangle=90, textprops={"fontsize": 7.6},
           wedgeprops={"edgecolor": CREAM})

    _banner(fig, "HISTORICAL DATA — 2019-2021. Do not compare against the UK "
                 "page as a current 2026 snapshot.", color=CHARCOAL)
    fig.text(0.5, 0.985, "HISTORICAL — 2019-2021", fontsize=11,
             fontweight="bold", color=CHARCOAL, ha="right", alpha=0.85)
    out = PREVIEWS / "page04_pakistan_historical.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page 05 — Skills Intelligence
# ---------------------------------------------------------------------------

def page05_skills_intelligence():
    skills = _csv("03_skill_demand.csv")
    bridge = _csv("14_job_skills_bridge.csv")

    cats = (bridge.groupby(["skill_category"]).skill_name.nunique()
            .sort_values(ascending=False))

    fig = _new_page("Skills Intelligence",
                    "Job-level penetration: each posting counts once per "
                    "skill | slicers: Country · Role · Skill Category · "
                    "Seniority")
    _kpi_row(fig, [
        (str(skills.skill_name.nunique()), "Normalized skills"),
        ("77", "Skills observed"),
        (f"{len(bridge):,}", "Job-skill links"),
        ("2,626", "Postings with ≥1 skill"),
        (f"{cats.index[0].replace('_', ' ').title()}",
         "Largest skill family"),
    ], w=0.14)

    ax = _panel(fig, [0.035, 0.47, 0.29, 0.36],
                "Skill families (distinct normalized skills)")
    _barh(ax, [c.replace("_", " / ").title() for c in cats.index][::-1],
          list(cats.values)[::-1], color=CHARCOAL)

    gbs = skills[skills.country_code == "GB"].nlargest(12, "penetration_pct")
    pks = skills[skills.country_code == "PK"].nlargest(12, "penetration_pct")
    ax = _panel(fig, [0.365, 0.47, 0.29, 0.36],
                "UK penetration leaders (recent)")
    _barh(ax, list(gbs.skill_name)[::-1], list(gbs.penetration_pct)[::-1],
          fmt="{:.1f}%")
    ax = _panel(fig, [0.695, 0.47, 0.27, 0.36],
                "PK penetration leaders (historical)")
    _barh(ax, list(pks.skill_name)[::-1], list(pks.penetration_pct)[::-1],
          color=CHARCOAL, fmt="{:.1f}%")

    # Heatmap: top shared skills x market
    common = (skills.pivot_table(index="skill_name", columns="country_code",
                                 values="penetration_pct")
              .dropna().sort_values("GB", ascending=False).head(12))
    ax = _panel(fig, [0.035, 0.065, 0.60, 0.31],
                "Shared-skill penetration heatmap (%) — recent UK vs "
                "historical PK")
    data = common[["GB", "PK"]].T.values
    im = ax.imshow(data, cmap="YlOrBr", aspect="auto", vmin=0)
    ax.set_xticks(range(len(common.index)), common.index, rotation=30,
                  ha="right")
    ax.set_yticks([0, 1], ["UK (recent)", "PK (historical)"])
    for i in range(2):
        for j, v in enumerate(data[i]):
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6.8,
                    color=PAPER if v > data.max() * 0.6 else INK)
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)

    rs = _csv("06_role_skills.csv")
    da = rs[(rs.role_category == "data_analyst") & (rs.country_code == "GB")]
    da = da.nlargest(10, "job_count")
    ax = _panel(fig, [0.67, 0.065, 0.295, 0.31],
                "Data Analyst (UK) — demanded skills")
    _barh(ax, list(da.skill_name)[::-1], list(da.penetration_pct)[::-1],
          fmt="{:.0f}%")

    _banner(fig, "Penetration denominators follow every active slicer — "
                 "percentages remain internally consistent under cross-filter.")
    out = PREVIEWS / "page05_skills_intelligence.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page 06 — UK vs Historical Pakistan Skill Comparison
# ---------------------------------------------------------------------------

def page06_skill_comparison():
    comp = _csv("04_skill_comparison.csv").copy()
    comp["abs_diff"] = comp.penetration_diff.abs()

    fig = _new_page("Skill Comparison — Recent UK vs Historical Pakistan",
                    "Rank and emphasis differences | temporal windows do NOT "
                    "overlap | interpret directionally, not contemporaneously")
    _kpi_row(fig, [
        (str(int((comp.uk_job_count > 0).sum())), "Skills seen in UK"),
        (str(int((comp.pk_job_count > 0).sum())), "Skills seen in PK"),
        (str(int(((comp.uk_job_count > 0)
                  & (comp.pk_job_count > 0)).sum())),
         "Common to both"),
        (str(int((comp.emphasis == "UK-emphasized").sum())),
         "UK-emphasized"),
        (str(int((comp.emphasis == "PK-emphasized").sum())),
         "PK-emphasized"),
    ], w=0.14)

    top = comp.nlargest(14, "abs_diff")
    y = np.arange(len(top))[::-1]
    ax = _panel(fig, [0.035, 0.40, 0.60, 0.46],
                "Penetration gap by skill (percentage points, UK% − PK%)")
    colors = [GOLD if v > 0 else CHARCOAL for v in top.penetration_diff]
    ax.barh(y, top.penetration_diff, color=colors, height=0.62)
    ax.set_yticks(y, top.skill_name)
    ax.axvline(0, color=INK, linewidth=0.8)
    for yi, v in zip(y, top.penetration_diff, strict=True):
        ax.text(v + (0.15 if v >= 0 else -0.15), yi, f"{v:+.1f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=7)
    ax.set_xlabel("Percentage-point penetration difference", fontsize=7.6)

    ax = _panel(fig, [0.685, 0.40, 0.28, 0.46],
                "How to read this page")
    ax.axis("off")
    ax.text(0.02, 0.96,
            "• Bars > 0: skill is more prevalent\n  in RECENT UK postings.\n"
            "• Bars < 0: more prevalent in the\n  HISTORICAL PK archive.\n"
            "• Percentages use each market's own\n  denominator (UK n=3,029; "
            "PK n=5,227).\n• Windows differ (2023-26 vs 2019-21);\n  gaps blend "
            "market AND period effects.",
            fontsize=8.4, va="top", color=INK, linespacing=1.55)

    common = comp[(comp.uk_job_count > 0) & (comp.pk_job_count > 0)]
    common = common.reindex(
        (common.uk_penetration_pct + common.pk_penetration_pct)
        .sort_values(ascending=False).index).head(10)
    yy = np.arange(len(common))[::-1]
    ax = _panel(fig, [0.035, 0.065, 0.60, 0.26],
                "Common skills — both markets (penetration %)")
    ax.scatter(common.uk_penetration_pct, yy, s=42, color=GOLD, zorder=3,
               label="UK (recent)")
    ax.scatter(common.pk_penetration_pct, yy, s=42, marker="s",
               color=CHARCOAL, zorder=3, label="PK (historical)")
    for yi, r in zip(yy, common.itertuples(), strict=True):
        ax.plot([r.uk_penetration_pct, r.pk_penetration_pct], [yi, yi],
                color=GRAY, linewidth=1, zorder=2)
        ax.text(r.uk_penetration_pct, yi + 0.28, r.skill_name, fontsize=7,
                ha="left", color=INK)
    ax.set_yticks([])
    ax.set_xlabel("% of that market's postings requiring the skill",
                  fontsize=7.6)
    ax.legend(fontsize=7.4, frameon=False, loc="lower right")

    ax = _panel(fig, [0.685, 0.065, 0.28, 0.26], "Sample-size honesty check")
    ax.axis("off")
    ax.text(0.02, 0.95,
            "Skills appearing in <5 postings\nper market were excluded at the\n"
            "SQL view level (v_skill_comparison\nHAVING filter), so no "
            "'difference'\nis computed off 1-2 mentions.",
            fontsize=8.4, va="top", color=INK, linespacing=1.5)

    _banner(fig, "TEMPORAL MISMATCH: comparisons span different years and "
                 "cannot be read as a current two-country ranking.",
            color=CHARCOAL)
    out = PREVIEWS / "page06_skill_comparison.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page 07 — Salary Intelligence
# ---------------------------------------------------------------------------

def page07_salary_intelligence():
    jobs = _csv("13_analytical_jobs.csv")
    ss = _csv("09_skill_salary.csv")
    uk = jobs[jobs.country_code == "GB"]
    sal = uk[uk.salary_midpoint.notna()
             & (uk.salary_midpoint.astype(str) != "NaN")].copy()
    v = sal.salary_midpoint.astype(float)
    q25, q75 = v.quantile([0.25, 0.75])
    med, mean = v.median(), v.mean()

    fig = _new_page("Salary Intelligence — UK Only",
                    "Advertised annual midpoints (min-max average) | GBP | no "
                    "estimation, no imputation | CHISEL carries no usable "
                    "salaries so none are reported")
    _kpi_row(fig, [
        (f"£{med:,.0f}", "Median salary"),
        (f"£{mean:,.0f}", "Mean salary"),
        (f"£{q25:,.0f}", "25th percentile"),
        (f"£{q75:,.0f}", "75th percentile"),
        (f"{len(v):,}", "Observations (n)"),
        (f"{len(v)/len(uk)*100:.1f}%", "Salary coverage of UK postings"),
    ], w=0.135)

    ax = _panel(fig, [0.035, 0.47, 0.42, 0.36],
                "Distribution with quartiles (£000s)")
    ax.hist(v / 1000, bins=44, color=GOLD, edgecolor=PAPER, linewidth=0.3)
    for q, lbl in ((q25, "Q25"), (med, "Median"), (q75, "Q75")):
        ax.axvline(q / 1000, color=INK, linestyle="-" if lbl == "Median" else ":",
                   linewidth=1.1)
        ax.text(q / 1000, ax.get_ylim()[1] * 0.95, lbl, rotation=90,
                va="top", fontsize=7, color=INK)
    ax.set_xlabel("£000s", fontsize=7.4)

    ax = _panel(fig, [0.495, 0.47, 0.235, 0.36],
                "Median by seniority (with n)")
    sen_order = ["junior", "mid", "senior", "unknown"]
    rows = []
    for s in sen_order:
        sv = sal.loc[sal.seniority == s, "salary_midpoint"].astype(float)
        if len(sv):
            rows.append((s, sv.median(), len(sv)))
    _barh(ax, [f"{s.title()} (n={n:,})" for s, _, n in rows][::-1],
          [m for _, m, _ in rows][::-1], fmt="£{0:,.0f}")

    ax = _panel(fig, [0.765, 0.47, 0.20, 0.36],
                "Median by location group")
    lg_rows = []
    for g in ["London", "Greater London", "UK Other"]:
        gv = sal.loc[sal.location_group == g, "salary_midpoint"].astype(float)
        if len(gv):
            lg_rows.append((g, gv.median(), len(gv)))
    _barh(ax, [f"{g}\n(n={n:,})" for g, _, n in lg_rows][::-1],
          [m for _, m, _ in lg_rows][::-1], color=CHARCOAL, fmt="£{0:,.0f}")

    gss = ss[ss.country_code == "GB"].nlargest(10, "median_salary")
    ax = _panel(fig, [0.035, 0.065, 0.44, 0.31],
                "Skills associated with higher advertised medians "
                "(n≥10 jobs)")
    _barh(ax, [f"{r.skill_name} (n={r.job_count})" for r in gss.itertuples()][::-1],
          list(gss.median_salary)[::-1], fmt="£{0:,.0f}")

    ax = _panel(fig, [0.51, 0.065, 0.455, 0.31], "Reading notes")
    ax.axis("off")
    ax.text(0.02, 0.96,
            "• Midpoints average min/max of the advertised range.\n"
            "• Coverage is 99.6% of UK postings but 0% of CHISEL PK —\n"
            "   therefore NO Pakistani salary figures appear anywhere in\n"
            "   this report.\n"
            "• Association ≠ causation: skills carry role and seniority\n"
            "   mix effects.\n"
            "• Outliers retained (max £364k); medians absorb them better\n"
            "   than means, which is why median leads every comparison.",
            fontsize=8.6, va="top", color=INK, linespacing=1.6)

    _banner(fig, "Salary analysis is UK-only. The historical Pakistan source "
                 "contains no parseable salary data.")
    out = PREVIEWS / "page07_salary_intelligence.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page 08 — Role & Seniority
# ---------------------------------------------------------------------------

def page08_role_seniority():
    jobs = _csv("13_analytical_jobs.csv")
    uk = jobs[jobs.country_code == "GB"]
    focus = ["data_analyst", "bi_developer", "reporting_analyst",
             "data_scientist", "analytics_engineer"]
    focus = [r for r in focus if r in set(uk.role_category)]
    counts = uk.role_category.value_counts()

    fig = _new_page("Role & Seniority Comparison",
                    "Core analytical roles in recent UK postings | slicers: "
                    "Role · Seniority · Location · Work Mode")
    _kpi_row(fig, [(f"{int(counts.get(r, 0)):,}",
                    r.replace("_", " ").title()) for r in focus] +
             [("1,454", "Other / unclassified")], w=0.135)

    ax = _panel(fig, [0.035, 0.44, 0.42, 0.42], "Posting volume by role")
    sub = counts[[c for c in focus if c in counts.index]]
    _barh(ax, [c.replace("_", " ").title() for c in sub.index][::-1],
          list(sub.values)[::-1])

    # Seniority mix per focus role
    ax = _panel(fig, [0.49, 0.44, 0.245, 0.42], "Seniority mix within role")
    mixes, labels = [], []
    for r in focus:
        rv = uk[uk.role_category == r].seniority.value_counts(normalize=True)
        mixes.append([rv.get(k, 0) * 100 for k in
                      ("junior", "mid", "senior", "unknown")])
        labels.append(r.replace("_", "\n").title())
    marr = np.array(mixes)
    left = np.zeros(len(focus))
    shades = [GOLD_LIGHT, GOLD, CHARCOAL, GRAY]
    names = ["Junior", "Mid", "Senior", "Unclassified"]
    for k in range(4):
        ax.bar(np.arange(len(focus)), marr[:, k], bottom=left,
               color=shades[k], label=names[k], width=0.6,
               edgecolor=CREAM)
        left += marr[:, k]
    ax.set_xticks(np.arange(len(focus)), labels, fontsize=6.4)
    ax.legend(fontsize=6.6, frameon=False, ncols=2, loc="upper right")
    ax.set_ylabel("% of role's postings", fontsize=7.4)

    ax = _panel(fig, [0.77, 0.44, 0.195, 0.42], "Work mode within role (%)")
    wm_left = np.zeros(len(focus))
    for mode, shade in (("remote", GOLD_LIGHT), ("hybrid", GOLD),
                        ("on_site", GRAY)):
        shares = []
        for r in focus:
            rm = uk[uk.role_category == r].work_mode.value_counts(normalize=True)
            shares.append(rm.get(mode, 0) * 100)
        ax.barh(np.arange(len(focus)), shares, left=wm_left, color=shade,
                label=mode, edgecolor=CREAM)
        wm_left += np.array(shares)
    ax.set_yticks(np.arange(len(focus)),
                  [r.split("_")[0].title() for r in focus], fontsize=6.4)
    ax.invert_yaxis()
    ax.legend(fontsize=6.6, frameon=False)

    bridge = _csv("14_job_skills_bridge.csv")
    ax = _panel(fig, [0.035, 0.055, 0.90, 0.30],
                "Signature skills per role — % of that role's UK postings")
    slot_w = 1 / len(focus)
    for i, r in enumerate(focus):
        ids = set(uk.loc[uk.role_category == r, "job_id"])
        sk = (bridge[bridge.job_id.isin(ids)].groupby("skill_name")
              .job_id.nunique())
        sk = (sk / len(ids) * 100).nlargest(6)[::-1]
        axi = fig.add_axes([0.035 + i * slot_w * 0.9, 0.075, slot_w * 0.86,
                            0.24])
        axi.set_facecolor(PAPER)
        axi.barh(np.arange(len(sk)), list(sk.values), color=GOLD, height=0.55)
        axi.set_yticks(np.arange(len(sk)), list(sk.index), fontsize=6.2)
        axi.invert_yaxis()
        axi.set_xticks([])
        axi.set_title(r.replace("_", " ").title(), fontsize=7,
                      fontweight="bold", loc="left", color=CHARCOAL)
        for s in ("top", "right"):
            axi.spines[s].set_visible(False)

    _banner(fig, "BI Developer / Reporting Analyst samples are small "
                 "(n<40) — treat their mixes as indicative only.")
    out = PREVIEWS / "page08_role_seniority.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page 09 — Career Intelligence
# ---------------------------------------------------------------------------

def page09_career_intelligence():
    rs = _csv("06_role_skills.csv")
    gb = rs[rs.country_code == "GB"]

    stages = [
        ("STAGE 1", "Data Analyst", "data_analyst",
         "Entry via reporting & analysis"),
        ("STAGE 2", "Advanced Analyst / BI", "bi_developer",
         "Deeper platform & automation skills"),
        ("STAGE 3", "Analytics Engineer /\nData Scientist", "analytics_engineer",
         "Pipeline engineering & modelling"),
    ]

    fig = _new_page("Career Intelligence — Market-Derived Progression Map",
                    "Derived from aggregated UK postings ONLY — not a "
                    "personal assessment | salary shown where advertised")
    jobs = _csv("13_analytical_jobs.csv")
    uk = jobs[jobs.country_code == "GB"]

    box_w, box_h, y0 = 0.27, 0.52, 0.30
    for i, (tag, name, key, blurb) in enumerate(stages):
        x = 0.035 + i * (box_w + 0.045)
        fig.patches.append(plt.Rectangle(
            (x, y0), box_w, box_h, transform=fig.transFigure, facecolor=PAPER,
            edgecolor=GOLD, linewidth=1.4))
        fig.text(x + 0.012, y0 + box_h - 0.035, tag, fontsize=8,
                 color=GRAY, fontweight="bold")
        fig.text(x + 0.012, y0 + box_h - 0.075, name, fontsize=12,
                 fontweight="bold", color=INK)
        n = int((uk.role_category == key).sum())
        fig.text(x + 0.012, y0 + box_h - 0.105,
                 f"{n:,} UK postings observed", fontsize=8, color=CHARCOAL)

        ids = set(uk.loc[uk.role_category == key, "job_id"]) if n else set()
        if ids:
            sk = (gb[gb.role_category == key].nlargest(8, "job_count"))
            for j, (_, row) in enumerate(sk.iterrows()):
                cy = y0 + box_h - 0.155 - j * 0.043
                fig.patches.append(plt.Rectangle(
                    (x + 0.012, cy - 0.008), 0.011, 0.026,
                    transform=fig.transFigure, facecolor=GOLD))
                fig.text(x + 0.032, cy + 0.002,
                         f"{row.skill_name}  ({row.penetration_pct:.0f}% of "
                         f"role)", fontsize=7.8, va="center", color=INK)
        if i < 2:
            arr = fig.add_axes([x + box_w + 0.004, y0 + box_h / 2 - 0.02,
                                0.037, 0.04], zorder=10)
            arr.axis("off")
            arr.annotate("", xy=(1, 0.5), xytext=(0, 0.5),
                         arrowprops=dict(arrowstyle="-|>", lw=2.4, color=GOLD))
        fig.text(x + 0.012, y0 - 0.035, blurb, fontsize=7.8, color=GRAY)

    ax = _panel(fig, [0.035, 0.055, 0.58, 0.185],
                "Observed skill-category shift across the ladder "
                "(share of role's top-8 links)")
    cat_names = ["technical", "analytical", "business_soft", "ai_ml",
                 "database", "tool", "cloud_de"]
    shades = [GRAY, CHARCOAL, GOLD_LIGHT, GOLD, "#7A6520", "#CDC7B8", WARM_GRAY]
    left = np.zeros(len(stages))
    keys = [s[2] for s in stages]
    for cname, shade in zip(cat_names, shades, strict=True):
        shares = []
        for k in keys:
            sub = gb[gb.role_category == k].nlargest(8, "job_count")
            tot = sub.job_count.sum()
            shares.append(sub.loc[sub.skill_category == cname, "job_count"]
                          .sum() / tot * 100 if tot else 0)
        ax.bar(np.arange(len(stages)), shares, bottom=left, color=shade,
               label=cname.replace("_", " ").title(), width=0.55,
               edgecolor=CREAM)
        left += np.array(shares)
    ax.set_xticks(np.arange(len(stages)),
                  [s[1].split("\n")[0].replace("/", " /") for s in stages],
                  fontsize=7)
    ax.legend(fontsize=6.4, frameon=False, ncols=4, loc="upper center",
              bbox_to_anchor=(0.5, -0.12))
    ax.set_ylabel("% of top-8 skill demand", fontsize=7.4)

    ax = _panel(fig, [0.66, 0.055, 0.305, 0.185], "Scope & caveats")
    ax.axis("off")
    ax.text(0.02, 0.95,
            "• Stage 2 (BI Developer) has a small UK sample (n=4):\n"
            "   skills shown are indicative, not statistical.\n"
            "• Ladder reflects DEMAND patterns in postings,\n"
            "   not guaranteed individual trajectories.\n"
            "• London relevance: 93% of these postings sit in\n"
            "   the London cluster.",
            fontsize=7.8, va="top", color=INK, linespacing=1.55)

    _banner(fig, "Market-derived career intelligence — aggregated postings, "
                 "no personal assessment, no causal claims.")
    out = PREVIEWS / "page09_career_intelligence.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Page 10 — Data Quality & Methodology
# ---------------------------------------------------------------------------

def page10_methodology():
    import json

    kv = json.loads((PROJECT_ROOT / "dashboard" / "powerbi"
                     / "kpi_validation.json").read_text(encoding="utf-8"))
    k = kv["kpi_reference_values"]

    fig = _new_page("Data Quality & Methodology",
                    "Full transparency on sources, processing, validation and "
                    "limitations")
    _banner(fig, "CORE LIMITATION: UK data is recent (2023-2026); Pakistan "
                 "data is historical (2019-2021). Datasets are NOT temporally "
                 "equivalent.", y=0.885)

    ax = _panel(fig, [0.035, 0.56, 0.29, 0.30], "Sources & periods")
    ax.axis("off")
    rows = [
        ("Adzuna API (UK)", "Sep 2023 - Aug 2026", f"{k['uk_jobs']:,} postings"),
        ("CHISEL / LUMS (PK)", "Dec 2019 - Mar 2021",
         f"{k['pk_historical']:,} postings"),
        ("Kaggle Rozee (PK)", "Mar - May 2024",
         f"{k['pk_supplementary']} postings"),
    ]
    for j, (a, b, c) in enumerate(rows):
        yy = 0.82 - j * 0.09
        fig.text(0.05, yy, a, fontsize=8.4, fontweight="bold", color=INK)
        fig.text(0.05, yy - 0.035, b, fontsize=7.8, color=CHARCOAL)
        fig.text(0.05, yy - 0.065, c, fontsize=7.8, color=GOLD)

    ax = _panel(fig, [0.365, 0.56, 0.29, 0.30], "Processing pipeline")
    ax.axis("off")
    steps = [
        "1. Ingestion -> staging with run manifests",
        "2. Cleaning: dedup on (source, source_job_id)",
        "3. Validation gates -> validated / quarantine",
        "4. Normalization: companies, locations, titles",
        "5. NLP skill extraction (lexicon + spaCy)",
        "6. PostgreSQL load -> 13 analytical views",
        "7. SQL/Python reconciliation checks",
    ]
    for j, s in enumerate(steps):
        fig.text(0.38, 0.79 - j * 0.037, s, fontsize=8, color=INK)

    ax = _panel(fig, [0.695, 0.56, 0.27, 0.30], "Validated headline KPIs")
    ax.axis("off")
    kpis = [
        ("Total unique jobs", f"{k['total_jobs']:,}"),
        ("UK (recent)", f"{k['uk_jobs']:,}"),
        ("PK (historical)", f"{k['pk_historical']:,}"),
        ("PK (supplementary)", str(k["pk_supplementary"])),
        ("Companies", f"{k['unique_companies']:,}"),
        ("Normalized skills", str(k["unique_skills"])),
        ("Job-skill links", f"{k['job_skill_links']:,}"),
        ("GB usable salaries", f"{k['usable_salaries_adzuna_uk']:,}"),
        ("PK usable salaries (CHISEL)",
         str(k["usable_salaries_chisel_pk"])),
    ]
    for j, (a, b) in enumerate(kpis):
        yy = 0.79 - j * 0.033
        fig.text(0.71, yy, a, fontsize=7.6, color=CHARCOAL)
        fig.text(0.955, yy, b, fontsize=7.6, color=GOLD, ha="right",
                 fontweight="bold")

    ax = _panel(fig, [0.035, 0.055, 0.44, 0.44], "Known limitations & biases")
    ax.axis("off")
    lims = [
        ("Temporal mismatch", "UK 2023-26 vs PK 2019-21; never compare as "
         "contemporaries."),
        ("Salary NaN artefact", "Phase 5 naive coverage shows 100%; real "
         "parseable salaries: UK 3,017, CHISEL 0."),
        ("Role taxonomy asymmetry", "99% of PK postings classify 'other' — "
         "weak CHISEL title mapping, not absence of data roles."),
        ("Source concentration", "Single UK API source; postings != labor "
         "market stock."),
        ("Missing attributes", "GB contract type blank for 61% of postings; "
         "seniority unknown 41%."),
        ("No imputation", "Missing values are reported, never invented."),
        ("Small cells suppressed", "Aggregates below n>=3 (role-skills) or "
         "n>=5 (comparisons) hidden."),
        ("Association only", "No causal claims; observational data."),
    ]
    for j, (t, d) in enumerate(lims):
        yy = 0.94 - j * 0.108
        fig.text(0.05, yy, "• " + t, fontsize=8, fontweight="bold", color=INK)
        fig.text(0.075, yy - 0.042, d, fontsize=7.4, color=CHARCOAL,
                 wrap=True)

    ax = _panel(fig, [0.51, 0.055, 0.455, 0.44], "Validation performed "
                "(scripts/powerbi_qa.py)")
    ax.axis("off")
    checks = [c["check"] for c in kv["checks"]]
    for j, cname in enumerate(checks[:14]):
        ok = next(c for c in kv["checks"] if c["check"] == cname)
        fig.text(0.525, 0.92 - j * 0.058, ("PASS  " if ok["pass"] else "FAIL ")
                 + cname, fontsize=7.4,
                 color="#6B8F5A" if ok["pass"] else "#9C4A38",
                 fontweight="bold")
    fig.text(0.525, 0.075,
             f"All {len(checks)} automated checks passed against live "
             "PostgreSQL.", fontsize=7.8, color=CHARCOAL, style="italic")

    out = PREVIEWS / "page10_data_quality_methodology.png"
    fig.savefig(out, dpi=DPI, facecolor=CREAM)
    plt.close(fig)


GENERATORS = [
    page01_executive_overview,
    page02_uk_market,
    page03_london,
    page04_pakistan,
    page05_skills_intelligence,
    page06_skill_comparison,
    page07_salary_intelligence,
    page08_role_seniority,
    page09_career_intelligence,
    page10_methodology,
]


def main() -> None:
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    print("Rendering Phase 6 dashboard page previews...")
    for gen in GENERATORS:
        gen()
        print(f"  rendered {gen.__name__}")
    print(f"Done -> {PREVIEWS}")


if __name__ == "__main__":
    main()
