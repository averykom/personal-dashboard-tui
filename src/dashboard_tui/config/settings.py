from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dashboard_tui.core.paths import config_dir

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


DEFAULT_CONFIG = """# Dashboard TUI config
# Copy to customize panels and refresh settings.

[ui]
show_footer_help = true
refresh_seconds = 1.0
theme = "textual-dark"

[backup]
enabled = true
directory = "~/Documents/dashboard-backups"
keep_latest = 30

[widgets.system]
enabled = true
title = "System"

[widgets.school]
enabled = true
title = "School"
url = ""
open_url = ""
days = 10

[widgets.todo]
enabled = true
title = "Tasks"
path = "~/.config/dashboard-tui/todo.txt"

[widgets.notes]
enabled = true
title = "Notes"
path = "~/.config/dashboard-tui/notes.txt"

[widgets.github]
enabled = true
title = "GitHub"
username = ""
repo = ""
token_env = "GITHUB_TOKEN"
"""

DEFAULT_BACKUP_BLOCK = """[backup]
enabled = true
directory = "~/.config/dashboard-tui/backups"
keep_latest = 30
"""
DEFAULT_SCHOOL_BLOCK = """[widgets.school]
enabled = true
title = "School"
url = ""
open_url = ""
days = 10
"""
DEFAULT_CLOCK_DISABLE_BLOCK = """[widgets.clock]
enabled = false
title = "Clock"
"""
DEFAULT_GITHUB_BLOCK = """[widgets.github]
enabled = true
title = "GitHub"
username = ""
repo = ""
token_env = "GITHUB_TOKEN"
"""


@dataclass(slots=True)
class WidgetConfig:
    enabled: bool = True
    title: str = ""
    path: str | None = None
    url: str | None = None
    open_url: str | None = None
    days: int | None = None
    username: str | None = None
    repo: str | None = None
    token_env: str | None = None


@dataclass(slots=True)
class UIConfig:
    show_footer_help: bool = True
    refresh_seconds: float = 1.0
    theme: str = "textual-dark"


@dataclass(slots=True)
class BackupConfig:
    enabled: bool = True
    directory: str = "~/Documents/dashboard-backups"
    keep_latest: int = 30


@dataclass(slots=True)
class Settings:
    ui: UIConfig = field(default_factory=UIConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    widgets: dict[str, WidgetConfig] = field(default_factory=dict)


def config_path() -> Path:
    return config_dir() / "config.toml"


def write_default_config_if_missing() -> Path:
    path = config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    return path


def load_settings() -> Settings:
    path = write_default_config_if_missing()
    _ensure_config_sections(path)
    raw = tomllib.loads(path.read_text(encoding="utf-8"))

    ui_raw = raw.get("ui", {})
    ui = UIConfig(
        show_footer_help=bool(ui_raw.get("show_footer_help", True)),
        refresh_seconds=float(ui_raw.get("refresh_seconds", 1.0)),
        theme=str(ui_raw.get("theme", "textual-dark")),
    )
    backup_raw = raw.get("backup", {})
    backup = BackupConfig(
        enabled=bool(backup_raw.get("enabled", True)),
        directory=str(backup_raw.get("directory", "~/.config/dashboard-tui/backups")),
        keep_latest=max(1, int(backup_raw.get("keep_latest", 30))),
    )

    widgets_raw = raw.get("widgets", {})
    widgets: dict[str, WidgetConfig] = {}
    for name, data in widgets_raw.items():
        if not isinstance(data, dict):
            continue
        widgets[name] = WidgetConfig(
            enabled=bool(data.get("enabled", True)),
            title=str(data.get("title", name.title())),
            path=_str_or_none(data.get("path")),
            url=_str_or_none(data.get("url")),
            open_url=_str_or_none(data.get("open_url")),
            days=_int_or_none(data.get("days")),
            username=_str_or_none(data.get("username")),
            repo=_str_or_none(data.get("repo")),
            token_env=_str_or_none(data.get("token_env")),
        )

    return Settings(ui=ui, backup=backup, widgets=widgets)


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def save_ui_theme(theme_name: str) -> None:
    path = write_default_config_if_missing()
    lines = path.read_text(encoding="utf-8").splitlines()
    theme_line = f'theme = "{theme_name}"'

    ui_start = _find_section_start(lines, "ui")
    if ui_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["[ui]", theme_line])
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    ui_end = _find_next_section(lines, ui_start + 1)
    for i in range(ui_start + 1, ui_end):
        if lines[i].strip().startswith("theme"):
            lines[i] = theme_line
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return

    lines.insert(ui_start + 1, theme_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find_section_start(lines: list[str], name: str) -> int | None:
    target = f"[{name}]"
    for i, line in enumerate(lines):
        if line.strip() == target:
            return i
    return None


def _find_next_section(lines: list[str], start: int) -> int:
    for i in range(start, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            return i
    return len(lines)


def _ensure_config_sections(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    updates: list[str] = []

    if "[backup]" not in text:
        updates.append(DEFAULT_BACKUP_BLOCK.strip())
    if "[widgets.school]" not in text:
        updates.append(DEFAULT_SCHOOL_BLOCK.strip())
    if "[widgets.clock]" not in text:
        updates.append(DEFAULT_CLOCK_DISABLE_BLOCK.strip())
    if "[widgets.github]" not in text:
        updates.append(DEFAULT_GITHUB_BLOCK.strip())

    if not updates:
        return

    if text and not text.endswith("\n"):
        text += "\n"
    if text.strip():
        text += "\n"
    text += "\n\n".join(updates) + "\n"
    path.write_text(text, encoding="utf-8")
