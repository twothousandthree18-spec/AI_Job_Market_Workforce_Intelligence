"""
Pipeline orchestrator — runs ingestion stages sequentially.

Usage:
    python scripts/run_pipeline.py --stage all
    python scripts/run_pipeline.py --stage ingest --source adzuna_uk
    python scripts/run_pipeline.py --stage stage
    python scripts/run_pipeline.py --stage validate
    python scripts/run_pipeline.py --stage process
    python scripts/run_pipeline.py --stage load
    python scripts/run_pipeline.py --stage db_validate
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    PROCESSED_DIR,
    RunManifest,
)


def _timed(manifest: RunManifest, name: str, fn) -> None:
    """Run *fn* and log wall-clock time."""
    t0 = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - t0
    manifest.logger.info(f"Stage '{name}' finished in {elapsed:.1f}s")


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
    """Convert raw files -> staging parquet."""
    manifest.logger.info("=== STAGE: STAGE ===")

    from ingestion.staging_converter import StagingConverter

    converter = StagingConverter(manifest)
    converter.convert_all()

    manifest.logger.info("Staging stage complete")


def run_validate(manifest: RunManifest, source: str | None = None) -> None:
    """Run data quality validation on staging files via PipelineProcessor."""
    manifest.logger.info("=== STAGE: VALIDATE ===")

    from pipeline.processor import PipelineProcessor

    processor = PipelineProcessor(manifest)
    processor._validate(processor._load_staging(source))

    manifest.logger.info("Validation stage complete")


def run_process(manifest: RunManifest, source: str | None = None) -> None:
    """Run the full processing pipeline: validate -> clean -> normalise -> NLP."""
    manifest.logger.info("=== STAGE: PROCESS ===")

    from pipeline.processor import PipelineProcessor

    processor = PipelineProcessor(manifest)
    processor.process(source)

    manifest.logger.info("Processing stage complete")


def run_load(manifest: RunManifest) -> None:
    """Load processed parquet into PostgreSQL."""
    manifest.logger.info("=== STAGE: LOAD ===")

    import pandas as pd

    from pipeline.db_loader import DatabaseLoader

    processed_path = PROCESSED_DIR / "processed.parquet"
    if not processed_path.exists():
        manifest.add_error("load", f"Processed file not found: {processed_path}")
        manifest.logger.error(f"No processed data at {processed_path}")
        return

    df = pd.read_parquet(processed_path)
    manifest.logger.info(f"Loaded {len(df)} processed records for DB load")

    loader = DatabaseLoader(manifest)
    loader.load(df)
    loader.validate_load()

    manifest.logger.info("Load stage complete")


def run_db_validate(manifest: RunManifest) -> None:
    """Validate database referential integrity and completeness."""
    manifest.logger.info("=== STAGE: DB_VALIDATE ===")

    from pipeline.db_validator import DatabaseValidator

    validator = DatabaseValidator(manifest)
    results = validator.validate()

    if not results.get("all_passed"):
        manifest.add_error("db_validate", "Referential integrity issues detected", results)

    manifest.logger.info("DB validation stage complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Job Market Pipeline")
    parser.add_argument(
        "--stage",
        choices=["all", "ingest", "stage", "validate", "process", "load", "db_validate"],
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
        "ingest":      lambda: run_ingest(manifest, args.source),
        "stage":       lambda: run_stage(manifest),
        "validate":    lambda: run_validate(manifest, args.source),
        "process":     lambda: run_process(manifest, args.source),
        "load":        lambda: run_load(manifest),
        "db_validate": lambda: run_db_validate(manifest),
    }

    try:
        if args.stage == "all":
            for name, fn in stages.items():
                if name in ("validate",):
                    continue  # validate is subsumed by process
                _timed(manifest, name, fn)
        else:
            _timed(manifest, args.stage, stages[args.stage])
        manifest.finish("completed")
    except Exception as exc:
        manifest.add_error("pipeline", str(exc))
        manifest.finish("failed")
        raise


if __name__ == "__main__":
    main()
