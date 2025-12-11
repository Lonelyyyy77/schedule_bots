from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)
# print("TOKEN:", settings.telegram_token)


# Определение путей проекта
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
SRC_DIR: Path = PROJECT_ROOT / "src"
CORE_DIR: Path = SRC_DIR / "core"
DATA_DIR: Path = CORE_DIR / "data"


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _get_str(name: str, default: Optional[str] = None) -> Optional[str]:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    return value if value else default


@dataclass(frozen=True)
class Settings:
    discord_token: Optional[str]
    telegram_token: Optional[str]

    debug: bool

    project_root: Path
    src_dir: Path
    core_dir: Path
    data_dir: Path

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            discord_token=_get_str("DISCORD_TOKEN"),
            telegram_token=_get_str("TELEGRAM_TOKEN"),
            debug=_get_bool("DEBUG", default=False),
            project_root=PROJECT_ROOT,
            src_dir=SRC_DIR,
            core_dir=CORE_DIR,
            data_dir=DATA_DIR,
        )

    def require_discord(self) -> str:
        if not self.discord_token:
            raise RuntimeError(
                "DISCORD_TOKEN не задан. Добавь его в .env или переменные окружения."
            )
        return self.discord_token

    def require_telegram(self) -> str:
        if not self.telegram_token:
            raise RuntimeError(
                "TELEGRAM_TOKEN не задан. Добавь его в .env или переменные окружения."
            )
        return self.telegram_token


settings: Settings = Settings.from_env()


def setup_logging(debug: bool | None = None) -> None:
    if debug is None:
        debug = settings.debug

    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    if not debug:
        logging.getLogger("aiogram").setLevel(logging.INFO)
        logging.getLogger("discord").setLevel(logging.INFO)


def safe_json_read(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            import json
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        logging.getLogger(__name__).warning(
            "Не удалось прочитать %s", path, exc_info=True
        )
    return {}


def ensure_data_dir() -> Path:
    """
    Гарантирует существование каталога данных (src/core/data).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
