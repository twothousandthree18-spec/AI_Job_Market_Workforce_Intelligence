"""
Pipeline framework — run manifests, logging, configuration loading.

Every pipeline run produces:
  - A run_id (UUID)
  - A manifest JSON (config, counts, timestamps, status)
  - A log file in logs/runs/<run_id>/
  - A quality report (after DQ stage)
"""

import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR      = PROJECT_ROOT / "data"
RAW_DIR       = DATA_DIR / "raw"
STAGING_DIR   = DATA_DIR / "staging"
VALIDATED_DIR = DATA_DIR / "validated"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR  = DATA_DIR / "external"
QUARANTINE_DIR = DATA_DIR / "quarantine"
SAMPLES_DIR   = DATA_DIR / "samples"

LOG_DIR       = PROJECT_ROOT / "logs"
RUNS_DIR      = LOG_DIR / "runs"
CONFIGS_DIR   = PROJECT_ROOT / "configs"

for d in [RAW_DIR, STAGING_DIR, VALIDATED_DIR, PROCESSED_DIR,
          QUARANTINE_DIR, RUNS_DIR, SAMPLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

DATABASE_URL       = os.getenv("DATABASE_URL", "postgresql://jobmarket:changeme@localhost:5432/job_market_analytics")
ADZUNA_APP_ID      = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY     = os.getenv("ADZUNA_APP_KEY", "")
DQ_PASS_THRESHOLD  = int(os.getenv("DQ_PASS_THRESHOLD", "70"))
PRIMARY_MARKET     = os.getenv("PRIMARY_MARKET", "gb")
SECONDARY_MARKETS  = os.getenv("SECONDARY_MARKETS", "pk").split(",")

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(run_id: str, level: int = logging.INFO) -> logging.Logger:
    """Configure logging to both console and run-specific file."""
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"pipeline.{run_id}")
    logger.setLevel(level)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File
    fh = logging.FileHandler(run_dir / "pipeline.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger

# ---------------------------------------------------------------------------
# Run manifest
# ---------------------------------------------------------------------------

class RunManifest:
    """Tracks a single pipeline run: config, counts, status, errors."""

    def __init__(self, run_type: str = "incremental", source: str = "", config: dict | None = None):
        self.run_id: str = uuid.uuid4().hex[:12]
        self.run_type: str = run_type
        self.source: str = source
        self.started_at: datetime = datetime.now(UTC)
        self.finished_at: datetime | None = None
        self.status: str = "running"
        self.records_read: int = 0
        self.records_accepted: int = 0
        self.records_rejected: int = 0
        self.errors: list[dict[str, Any]] = []
        self.config_snapshot: dict[str, Any] = config or {}
        self.logger = setup_logging(self.run_id)
        self.run_dir = RUNS_DIR / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def add_error(self, stage: str, message: str, details: Any = None) -> None:
        self.errors.append({
            "stage": stage,
            "message": message,
            "details": details,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        self.logger.error(f"[{stage}] {message}")

    def increment(self, field: str, count: int = 1) -> None:
        if hasattr(self, field):
            setattr(self, field, getattr(self, field) + count)

    def finish(self, status: str = "completed") -> None:
        self.status = status
        self.finished_at = datetime.now(UTC)
        self.logger.info(
            f"Run {self.run_id} {status}: "
            f"read={self.records_read}, accepted={self.records_accepted}, "
            f"rejected={self.records_rejected}, errors={len(self.errors)}"
        )
        self.save()

    def save(self) -> None:
        manifest = {
            "run_id": self.run_id,
            "run_type": self.run_type,
            "source": self.source,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "records_read": self.records_read,
            "records_accepted": self.records_accepted,
            "records_rejected": self.records_rejected,
            "errors": self.errors,
            "config_snapshot": self.config_snapshot,
        }
        manifest_path = self.run_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)
        self.logger.info(f"Manifest saved to {manifest_path}")

    def quality_report_path(self) -> Path:
        return self.run_dir / "quality_report.json"

    def quality_report_md_path(self) -> Path:
        return self.run_dir / "quality_report.md"

# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict:
    """Load a YAML config file."""
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_source_config() -> dict:
    return load_yaml(CONFIGS_DIR / "source_config.yaml")

def load_skill_lexicon() -> dict:
    return load_yaml(CONFIGS_DIR / "skill_lexicon.yaml")

def load_title_map() -> dict:
    return load_yaml(CONFIGS_DIR / "title_map.yaml")

def load_schema_manifest() -> dict:
    with open(CONFIGS_DIR / "schema_manifest.json", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# Convenience: quick test that framework loads
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    m = RunManifest(run_type="test", source="framework_check")
    m.logger.info("Pipeline framework loaded successfully")
    m.finish("completed")
    print(f"Run ID: {m.run_id}")
    print(f"Log:    {m.run_dir / 'pipeline.log'}")
    print(f"JSON:   {m.run_dir / 'manifest.json'}")
