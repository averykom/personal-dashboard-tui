from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.markup import escape

from dashboard_tui.core.backup import backup_file
from dashboard_tui.widgets.base import DashboardWidget


@dataclass(slots=True)
class TodoItem:
    text: str
    done: bool = False


class TodoWidget(DashboardWidget):
    empty_hint = "No tasks yet. Add lines to the todo file."

    def __init__(self, context) -> None:
        super().__init__(context)
        self.selected_index = 0

    def render_text(self) -> str:
        file_path = self._file_path()
        if file_path is None:
            return f"[b]{self.title}[/b]\nNo file configured."

        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("", encoding="utf-8")
            return f"[b]{self.title}[/b]\nCreated: {file_path}\n{self.empty_hint}"

        items = self._load_items(file_path)
        if not items:
            self.selected_index = 0
            return f"[b]{self.title}[/b]\n{self.empty_hint}"

        self.selected_index = min(self.selected_index, len(items) - 1)
        start = max(0, self.selected_index - 4)
        end = min(len(items), start + 8)
        start = max(0, end - 8)
        visible = items[start:end]

        body_lines: list[str] = []
        for offset, item in enumerate(visible):
            index = start + offset
            pointer = ">" if self.is_active and index == self.selected_index else " "
            task_text = escape(item.text)
            if item.done:
                task_text = f"[strike]{task_text}[/strike]"
            body_lines.append(f"{pointer} {task_text}")

        suffix = ""
        if len(items) > end:
            suffix = f"\n... +{len(items) - end} more"
        return f"[b]{self.title}[/b]\n" + "\n".join(body_lines) + suffix

    def move_selection(self, delta: int) -> bool:
        path = self.context.source_path
        if not path:
            return False

        items = self._load_items(Path(path).expanduser())
        if not items:
            self.selected_index = 0
            return False

        self.selected_index = max(0, min(self.selected_index + delta, len(items) - 1))
        return True

    def toggle_selected(self) -> bool:
        file_path = self._file_path()
        if file_path is None:
            return False

        items = self._load_items(file_path)
        if not items:
            return False

        self.selected_index = min(self.selected_index, len(items) - 1)
        items[self.selected_index].done = not items[self.selected_index].done
        self._save_items(file_path, items)
        return True

    def add_task(self, text: str) -> bool:
        clean_text = text.strip()
        if not clean_text:
            return False

        file_path = self._file_path()
        if file_path is None:
            return False

        items = self._load_items(file_path)
        items.append(TodoItem(text=clean_text, done=False))
        self.selected_index = len(items) - 1
        self._save_items(file_path, items)
        return True

    def edit_selected(self, text: str) -> bool:
        clean_text = text.strip()
        if not clean_text:
            return False

        file_path = self._file_path()
        if file_path is None:
            return False

        items = self._load_items(file_path)
        if not items:
            return False

        self.selected_index = min(self.selected_index, len(items) - 1)
        items[self.selected_index].text = clean_text
        self._save_items(file_path, items)
        return True

    def delete_selected(self) -> bool:
        file_path = self._file_path()
        if file_path is None:
            return False

        items = self._load_items(file_path)
        if not items:
            return False

        self.selected_index = min(self.selected_index, len(items) - 1)
        items.pop(self.selected_index)
        if items:
            self.selected_index = min(self.selected_index, len(items) - 1)
        else:
            self.selected_index = 0
        self._save_items(file_path, items)
        return True

    def get_selected_text(self) -> str | None:
        file_path = self._file_path()
        if file_path is None:
            return None

        items = self._load_items(file_path)
        if not items:
            return None

        self.selected_index = min(self.selected_index, len(items) - 1)
        return items[self.selected_index].text

    def _load_items(self, path: Path) -> list[TodoItem]:
        if not path.exists():
            return []

        items: list[TodoItem] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue

            if line.startswith("- [ ] "):
                items.append(TodoItem(text=line[6:].strip(), done=False))
            elif line.startswith("- [x] ") or line.startswith("- [X] "):
                items.append(TodoItem(text=line[6:].strip(), done=True))
            elif line.startswith("[ ] "):
                items.append(TodoItem(text=line[4:].strip(), done=False))
            elif line.startswith("[x] ") or line.startswith("[X] "):
                items.append(TodoItem(text=line[4:].strip(), done=True))
            else:
                items.append(TodoItem(text=line, done=False))
        return items

    def _save_items(self, path: Path, items: list[TodoItem]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        backup_file(
            path,
            enabled=self.context.backup_enabled,
            backup_directory=self.context.backup_directory,
            keep_latest=self.context.backup_keep_latest,
        )
        lines = [f"- [{'x' if item.done else ' '}] {item.text}" for item in items]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _file_path(self) -> Path | None:
        path = self.context.source_path
        if not path:
            return None
        return Path(path).expanduser()
