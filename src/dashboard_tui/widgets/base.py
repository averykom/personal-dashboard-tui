from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class WidgetContext:
    title: str
    source_path: str | None = None
    source_url: str | None = None
    open_url: str | None = None
    days: int | None = None
    username: str | None = None
    repo: str | None = None
    token_env: str | None = None
    backup_enabled: bool = True
    backup_directory: str | None = None
    backup_keep_latest: int = 30


class DashboardWidget(ABC):
    def __init__(self, context: WidgetContext) -> None:
        self.context = context
        self.is_active = False

    @property
    def title(self) -> str:
        return self.context.title

    @abstractmethod
    def render_text(self) -> str:
        raise NotImplementedError

    def move_selection(self, delta: int) -> bool:
        return False

    def toggle_selected(self) -> bool:
        return False

    def set_active(self, active: bool) -> None:
        self.is_active = active
