"""Application configuration loaded from ~/.studentflow/config.json."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Config:
    canonical_repo_path: str = str(Path.home() / ".studentflow" / "canonical")
    template_dir: str = str(Path.home() / "studentflow-templates")
    default_branch: str = "main"
    sync_timeout_seconds: int = 60
    max_sync_retries: int = 2
    enable_auto_sync: bool = False
    auto_sync_interval_minutes: int = 30
    log_level: str = "INFO"

    @classmethod
    def load(cls, path: Path) -> "Config":
        if not path.exists():
            config = cls()
            config.save(path)
            return config
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
