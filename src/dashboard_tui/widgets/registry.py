from __future__ import annotations

from dataclasses import dataclass

from dashboard_tui.config.settings import Settings
from dashboard_tui.widgets.base import DashboardWidget, WidgetContext
from dashboard_tui.widgets.github import GitHubWidget
from dashboard_tui.widgets.notes import NotesWidget
from dashboard_tui.widgets.school import SchoolWidget
from dashboard_tui.widgets.system import SystemWidget
from dashboard_tui.widgets.todo import TodoWidget


@dataclass(slots=True)
class WidgetDefinition:
    key: str
    factory: type[DashboardWidget]


WIDGETS: dict[str, WidgetDefinition] = {
    "system": WidgetDefinition("system", SystemWidget),
    "school": WidgetDefinition("school", SchoolWidget),
    "todo": WidgetDefinition("todo", TodoWidget),
    "notes": WidgetDefinition("notes", NotesWidget),
    "github": WidgetDefinition("github", GitHubWidget),
}


def load_enabled_widgets(settings: Settings) -> list[DashboardWidget]:
    items: list[DashboardWidget] = []
    for key, definition in WIDGETS.items():
        cfg = settings.widgets.get(key)
        if cfg and not cfg.enabled:
            continue

        title = cfg.title if cfg and cfg.title else key.title()
        source_path = cfg.path if cfg else None
        source_url = cfg.url if cfg else None
        open_url = cfg.open_url if cfg else None
        days = cfg.days if cfg else None
        username = cfg.username if cfg else None
        repo = cfg.repo if cfg else None
        token_env = cfg.token_env if cfg else None
        context = WidgetContext(
            title=title,
            source_path=source_path,
            source_url=source_url,
            open_url=open_url,
            days=days,
            username=username,
            repo=repo,
            token_env=token_env,
            backup_enabled=settings.backup.enabled,
            backup_directory=settings.backup.directory,
            backup_keep_latest=settings.backup.keep_latest,
        )
        items.append(definition.factory(context))

    return items
