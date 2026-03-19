"""Application bootstrap: initialize DB, logging, config, and filesystem directories."""
import sys
from pathlib import Path

APP_DIR = Path.home() / ".studentflow"
LOG_DIR = APP_DIR / "logs"
CANONICAL_DIR = APP_DIR / "canonical"
DB_PATH = APP_DIR / "studentflow.db"
CONFIG_PATH = APP_DIR / "config.json"


def create_app_dirs() -> None:
    APP_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    CANONICAL_DIR.mkdir(exist_ok=True)


def get_config():
    from app.config import Config
    return Config.load(CONFIG_PATH)


def init_logging(debug: bool = False) -> None:
    import logging
    import logging.handlers
    import structlog

    level = logging.DEBUG if debug else logging.INFO
    handler = logging.handlers.RotatingFileHandler(
        filename=LOG_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    logging.basicConfig(
        format="%(message)s",
        handlers=[handler, logging.StreamHandler(sys.stdout)],
        level=level,
    )
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def init_db() -> None:
    import app.db.models  # noqa: F401
    from app.db.base import Base, engine
    Base.metadata.create_all(bind=engine)
    _seed_default_settings()


def _seed_default_settings() -> None:
    from app.db.base import SessionLocal
    defaults = {
        "canonical_repo_path": str(CANONICAL_DIR),
        "default_branch": "main",
        "template_dir": str(Path.home() / "studentflow-templates"),
        "sync_timeout_seconds": "60",
        "max_sync_retries": "2",
        "enable_auto_sync": "false",
        "auto_sync_interval_minutes": "30",
        "canonical_remote_url": "",
    }
    descriptions = {
        "canonical_repo_path": "Absolute path to the canonical bare git repository",
        "default_branch": "Default git branch name for new repositories",
        "template_dir": "Default directory to search for project templates",
        "sync_timeout_seconds": "Seconds before a git operation is killed",
        "max_sync_retries": "How many times to retry a failed sync",
        "enable_auto_sync": "Whether SchedulerService runs periodic sync (true/false)",
        "auto_sync_interval_minutes": "Interval for auto sync if enabled",
        "canonical_remote_url": "Optional remote URL to push canonical repo after each sync",
    }
    with SessionLocal() as session:
        from app.db.models import AppSetting
        from datetime import datetime
        for key, value in defaults.items():
            existing = session.get(AppSetting, key)
            if existing is None:
                session.add(AppSetting(
                    key=key,
                    value=value,
                    description=descriptions.get(key),
                    updated_at=datetime.utcnow(),
                ))
        session.commit()
