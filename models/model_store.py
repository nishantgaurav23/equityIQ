"""Model persistence -- save/load XGBoost SignalFusionModel with joblib."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib

from models.signal_fusion import SignalFusionModel

logger = logging.getLogger(__name__)

# Filename pattern: signal_fusion_{tag}_{timestamp}.joblib or signal_fusion_{timestamp}.joblib
TIMESTAMP_FMT = "%Y%m%dT%H%M%S%f"
FILENAME_PATTERN = re.compile(
    r"^signal_fusion_(?:(?P<tag>[a-zA-Z0-9_-]+)_)?(?P<ts>\d{8}T\d{6}\d+)\.joblib$"
)
TAG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


@dataclass
class ModelInfo:
    """Metadata for a saved model."""

    path: Path
    filename: str
    tag: str | None
    timestamp: datetime
    size_bytes: int


class ModelStore:
    """Saves and loads SignalFusionModel instances using joblib."""

    def __init__(self, base_dir: str | Path = "data/models"):
        self.base_dir = Path(base_dir)

    def save(self, model: SignalFusionModel, tag: str | None = None) -> Path:
        """Serialize a trained model to disk. Returns path to saved file."""
        if not model.is_trained:
            raise ValueError("Cannot save untrained model")

        if tag is not None and not TAG_PATTERN.match(tag):
            raise ValueError(f"Invalid tag '{tag}': must match [a-zA-Z0-9_-]+")

        self.base_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime(TIMESTAMP_FMT)
        if tag:
            filename = f"signal_fusion_{tag}_{ts}.joblib"
        else:
            filename = f"signal_fusion_{ts}.joblib"

        path = self.base_dir / filename
        joblib.dump(model, path)
        logger.info("Saved model to %s (%d bytes)", path, path.stat().st_size)
        return path

    def load(self, path: str | Path | None = None) -> SignalFusionModel:
        """Load a model from disk. If path is None, loads the latest."""
        if path is None:
            latest = self.get_latest_path()
            if latest is None:
                raise FileNotFoundError("No saved models found")
            path = latest

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        obj = joblib.load(path)
        if not isinstance(obj, SignalFusionModel):
            raise TypeError(f"Expected SignalFusionModel, got {type(obj).__name__}")

        logger.info("Loaded model from %s", path)
        return obj

    def list(self) -> list[ModelInfo]:
        """List all saved models, newest first."""
        if not self.base_dir.exists():
            return []

        infos: list[ModelInfo] = []
        for p in self.base_dir.glob("signal_fusion_*.joblib"):
            match = FILENAME_PATTERN.match(p.name)
            if not match:
                continue
            ts = datetime.strptime(match.group("ts"), TIMESTAMP_FMT).replace(tzinfo=timezone.utc)
            infos.append(
                ModelInfo(
                    path=p,
                    filename=p.name,
                    tag=match.group("tag"),
                    timestamp=ts,
                    size_bytes=p.stat().st_size,
                )
            )

        infos.sort(key=lambda x: x.timestamp, reverse=True)
        return infos

    def delete(self, path: str | Path) -> bool:
        """Delete a model file. Returns True if deleted, False if not found."""
        path = Path(path).resolve()
        base_resolved = self.base_dir.resolve()

        if not str(path).startswith(str(base_resolved)):
            raise ValueError(f"Can only delete models from data/models/ (got {path})")

        if not path.exists():
            return False

        path.unlink()
        logger.info("Deleted model %s", path)
        return True

    def get_latest_path(self) -> Path | None:
        """Return path to the most recently saved model, or None."""
        if not self.base_dir.exists():
            return None

        models = sorted(
            self.base_dir.glob("signal_fusion_*.joblib"),
            key=lambda p: p.stat().st_mtime,
        )
        if not models:
            return None

        return models[-1]
