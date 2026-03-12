from __future__ import annotations

from pathlib import Path

APP_NAME = "dashboard-tui"


def config_dir() -> Path:
    return Path.home() / ".config" / APP_NAME


def cache_dir() -> Path:
    return Path.home() / ".cache" / APP_NAME


def ensure_app_dirs() -> tuple[Path, Path]:
    cdir = config_dir()
    adir = cache_dir()
    cdir.mkdir(parents=True, exist_ok=True)
    adir.mkdir(parents=True, exist_ok=True)
    return cdir, adir
