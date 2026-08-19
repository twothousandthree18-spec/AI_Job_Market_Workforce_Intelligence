"""
Base collector — abstract interface for all data-source collectors.
"""

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeline.config import RAW_DIR, RunManifest


class BaseCollector(ABC):
    """Abstract base class for data-source collectors.

    Subclasses must implement:
      - source_name: str
      - collect(): fetch/save logic
    """

    def __init__(self, manifest: RunManifest):
        self.manifest = manifest
        self.logger = manifest.logger
        self.raw_dir: Path = RAW_DIR / self.source_name
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @abstractmethod
    def collect(self) -> None:
        ...

    def _raw_path(self, tag: str = "") -> Path:
        date_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        suffix = f"_{tag}" if tag else ""
        return self.raw_dir / f"{date_str}{suffix}.json"

    def _save_raw(self, records: list[dict[str, Any]], tag: str = "") -> Path:
        path = self._raw_path(tag)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)
        self.logger.info(f"Saved {len(records)} raw records -> {path}")
        return path
