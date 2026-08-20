from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DQReport:
    """Collects data-quality results and outputs JSON / Markdown reports."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.summary: dict[str, Any] = {}

    def add_record_result(
        self,
        record_id: str,
        issues: list[dict[str, str]],
        score: float,
    ) -> None:
        self.records[record_id] = {
            "score": score,
            "issues": issues,
            "issue_count": len(issues),
        }

    def generate_summary(
        self,
        total: int,
        valid: int,
        invalid: int,
        flagged: int,
        duplicates: int,
        by_severity_count: dict[str, int],
        by_check_count: dict[str, int],
    ) -> dict[str, Any]:
        self.summary = {
            "total_records": total,
            "valid_records": valid,
            "invalid_records": invalid,
            "flagged_records": flagged,
            "duplicate_records": duplicates,
            "pass_rate": round(valid / total * 100, 2) if total else 0.0,
            "avg_score": round(
                sum(r["score"] for r in self.records.values()) / len(self.records), 2
            ) if self.records else 0.0,
            "by_severity": by_severity_count,
            "by_check": by_check_count,
        }
        return self.summary

    def save_json(self, path: str | Path) -> None:
        payload = {
            "summary": self.summary,
            "records": self.records,
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

    def save_markdown(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = ["# Data Quality Report\n"]

        s = self.summary
        if s:
            lines.append("## Summary\n")
            lines.append("| Metric | Value |")
            lines.append("|--------|-------|")
            lines.append(f"| Total records | {s.get('total_records', 0)} |")
            lines.append(f"| Valid records | {s.get('valid_records', 0)} |")
            lines.append(f"| Invalid records | {s.get('invalid_records', 0)} |")
            lines.append(f"| Flagged records | {s.get('flagged_records', 0)} |")
            lines.append(f"| Duplicate records | {s.get('duplicate_records', 0)} |")
            lines.append(f"| Pass rate | {s.get('pass_rate', 0)}% |")
            lines.append(f"| Avg DQ score | {s.get('avg_score', 0)} |")
            lines.append("")

            by_sev = s.get("by_severity", {})
            if by_sev:
                lines.append("### Issues by Severity\n")
                lines.append("| Severity | Count |")
                lines.append("|----------|-------|")
                for sev, count in sorted(by_sev.items()):
                    lines.append(f"| {sev} | {count} |")
                lines.append("")

            by_chk = s.get("by_check", {})
            if by_chk:
                lines.append("### Issues by Check Type\n")
                lines.append("| Check | Count |")
                lines.append("|-------|-------|")
                for chk, count in sorted(by_chk.items(), key=lambda x: -x[1]):
                    lines.append(f"| {chk} | {count} |")
                lines.append("")

        if self.records:
            lines.append("## Per-Record Details\n")
            lines.append("| Record ID | Score | Issues | Top Issue |")
            lines.append("|-----------|-------|--------|-----------|")
            for rid, r in sorted(self.records.items(), key=lambda x: x[1]["score"]):
                top = ""
                if r["issues"]:
                    top_issue = r["issues"][0]
                    sev = top_issue["severity"]
                    fld = top_issue["field"]
                    msg = top_issue["message"]
                    top = f"**{sev}** {fld}: {msg}"
                lines.append(f"| `{rid}` | {r['score']:.0f} | {r['issue_count']} | {top} |")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
