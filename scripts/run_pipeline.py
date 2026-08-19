"""
Pipeline orchestrator — runs ingestion stages sequentially.

Usage:
    python scripts/run_pipeline.py --stage all
    python scripts/run_pipeline.py --stage ingest --source adzuna_uk
    python scripts/run_pipeline.py --stage stage
    python scripts/run_pipeline.py --stage validate
"""

import argparse
import sys
from pathlib import Path

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    RunManifest,
)


def run_ingest(manifest: RunManifest, source: str | None = None) -> None:
    """Run data ingestion from configured sources."""
    manifest.logger.info("=== STAGE: INGEST ===")

    from ingestion.adzuna_collector import AdzunaCollector
    from ingestion.kaggle_importer import KaggleImporter

    if source in (None, "adzuna_uk"):
        if ADZUNA_APP_ID and ADZUNA_APP_KEY:
            collector = AdzunaCollector(manifest)
            collector.collect()
        else:
            manifest.logger.warning(
                "Skipping Adzuna: ADZUNA_APP_ID/ADZUNA_APP_KEY not set in .env"
            )
            manifest.add_error("ingest", "Adzuna keys missing, skipped")

    if source in (None, "kaggle_rozee_pk"):
        importer = KaggleImporter(manifest)
        importer.import_dataset()

    manifest.logger.info("Ingestion stage complete")


def run_stage(manifest: RunManifest) -> None:
    """Convert raw files → staging parquet."""
    manifest.logger.info("=== STAGE: STAGE ===")

    from ingestion.staging_converter import StagingConverter

    converter = StagingConverter(manifest)
    converter.convert_all()

    manifest.logger.info("Staging stage complete")


def run_validate(manifest: RunManifest) -> None:
    """Run data quality validation on staging files."""
    manifest.logger.info("=== STAGE: VALIDATE ===")
    manifest.logger.info("Validation stage — implementing in Phase 3")
    # Placeholder: quality checks will be implemented in src/validation/


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Job Market Pipeline")
    parser.add_argument(
        "--stage",
        choices=["all", "ingest", "stage", "validate"],
        default="all",
        help="Pipeline stage to run (default: all)",
    )
    parser.add_argument(
        "--source",
        choices=["adzuna_uk", "kaggle_rozee_pk"],
        default=None,
        help="Limit ingestion to a single source",
    )
    args = parser.parse_args()

    manifest = RunManifest(
        run_type="incremental",
        source=args.source or "all",
        config={"stage": args.stage, "source": args.source},
    )
    manifest.logger.info(f"Pipeline started: run_id={manifest.run_id}, stage={args.stage}")

    stages = {
        "ingest":  lambda: run_ingest(manifest, args.source),
        "stage":   lambda: run_stage(manifest),
        "validate": lambda: run_validate(manifest),
    }

    try:
        if args.stage == "all":
            for _name, fn in stages.items():
                fn()
        else:
            stages[args.stage]()
        manifest.finish("completed")
    except Exception as exc:
        manifest.add_error("pipeline", str(exc))
        manifest.finish("failed")
        raise


if __name__ == "__main__":
    main()
