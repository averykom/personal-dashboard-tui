from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.markup import escape

from dashboard_tui.core.backup import backup_file
from dashboard_tui.widgets.base import DashboardWidget


@dataclass(slots=True)
class NoteItem:
    title: str
    body: str = ""


class NotesWidget(DashboardWidget):
    empty_hint = "No notes yet. Press 'a' to add one."

    def __init__(self, context) -> None:
        super().__init__(context)
        self.selected_index = 0
        self.expanded_index: int | None = None

    def render_text(self) -> str:
        file_path = self._file_path()
        if file_path is None:
            return f"[b]{self.title}[/b]\nNo file configured."

        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("", encoding="utf-8")
            return f"[b]{self.title}[/b]\nCreated: {file_path}\n{self.empty_hint}"

        notes = self._load_notes(file_path)
        if not notes:
            self.selected_index = 0
            self.expanded_index = None
            return f"[b]{self.title}[/b]\n{self.empty_hint}"

        self.selected_index = min(self.selected_index, len(notes) - 1)
        if self.expanded_index is not None and self.expanded_index >= len(notes):
            self.expanded_index = None

        start = max(0, self.selected_index - 4)
        end = min(len(notes), start + 8)
        start = max(0, end - 8)
        visible = notes[start:end]

        lines = [f"[b]{self.title}[/b]"]
        for offset, note in enumerate(visible):
            index = start + offset
            pointer = ">" if self.is_active and index == self.selected_index else " "
            lines.append(f"{pointer} {escape(note.title)}")

            if index == self.expanded_index:
                body_lines = note.body.splitlines() if note.body.strip() else ["(No details)"]
                for body_line in body_lines:
                    lines.append(f"    {escape(body_line)}")

        if len(notes) > end:
            lines.append(f"... +{len(notes) - end} more")

        return "\n".join(lines)

    def move_selection(self, delta: int) -> bool:
        file_path = self._file_path()
        if file_path is None:
            return False
        notes = self._load_notes(file_path)
        if not notes:
            self.selected_index = 0
            return False
        self.selected_index = max(0, min(self.selected_index + delta, len(notes) - 1))
        return True

    def toggle_selected(self) -> bool:
        file_path = self._file_path()
        if file_path is None:
            return False
        notes = self._load_notes(file_path)
        if not notes:
            return False
        self.selected_index = min(self.selected_index, len(notes) - 1)
        if self.expanded_index == self.selected_index:
            self.expanded_index = None
        else:
            self.expanded_index = self.selected_index
        return True

    def add_note(self, title: str, body: str) -> bool:
        clean_title = title.strip()
        if not clean_title:
            return False
        file_path = self._file_path()
        if file_path is None:
            return False
        notes = self._load_notes(file_path)
        notes.append(NoteItem(title=clean_title, body=body.rstrip()))
        self.selected_index = len(notes) - 1
        self.expanded_index = self.selected_index
        self._save_notes(file_path, notes)
        return True

    def edit_selected(self, title: str, body: str) -> bool:
        clean_title = title.strip()
        if not clean_title:
            return False
        file_path = self._file_path()
        if file_path is None:
            return False
        notes = self._load_notes(file_path)
        if not notes:
            return False
        self.selected_index = min(self.selected_index, len(notes) - 1)
        notes[self.selected_index].title = clean_title
        notes[self.selected_index].body = body.rstrip()
        self._save_notes(file_path, notes)
        return True

    def delete_selected(self) -> bool:
        file_path = self._file_path()
        if file_path is None:
            return False
        notes = self._load_notes(file_path)
        if not notes:
            return False
        self.selected_index = min(self.selected_index, len(notes) - 1)
        notes.pop(self.selected_index)
        if notes:
            self.selected_index = min(self.selected_index, len(notes) - 1)
            if self.expanded_index is not None:
                if self.expanded_index == len(notes):
                    self.expanded_index = len(notes) - 1
                elif self.expanded_index > self.selected_index:
                    self.expanded_index = max(0, self.expanded_index - 1)
        else:
            self.selected_index = 0
            self.expanded_index = None
        self._save_notes(file_path, notes)
        return True

    def get_selected_note(self) -> tuple[str, str] | None:
        file_path = self._file_path()
        if file_path is None:
            return None
        notes = self._load_notes(file_path)
        if not notes:
            return None
        self.selected_index = min(self.selected_index, len(notes) - 1)
        selected = notes[self.selected_index]
        return selected.title, selected.body

    def _file_path(self) -> Path | None:
        if not self.context.source_path:
            return None
        return Path(self.context.source_path).expanduser()

    def _load_notes(self, path: Path) -> list[NoteItem]:
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8")
        lines = raw.splitlines()
        if not lines:
            return []

        if any(line.startswith("## ") for line in lines):
            notes: list[NoteItem] = []
            current_title: str | None = None
            current_body: list[str] = []
            for line in lines:
                if line.startswith("## "):
                    if current_title is not None:
                        notes.append(NoteItem(title=current_title, body="\n".join(current_body).strip()))
                    current_title = line[3:].strip() or "Untitled"
                    current_body = []
                    continue
                if line.strip() == "---":
                    continue
                if current_title is not None:
                    current_body.append(line)
            if current_title is not None:
                notes.append(NoteItem(title=current_title, body="\n".join(current_body).strip()))
            return notes

        # Backward compatibility: treat each non-empty line as a note title.
        return [NoteItem(title=line.strip(), body="") for line in lines if line.strip()]

    def _save_notes(self, path: Path, notes: list[NoteItem]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        backup_file(
            path,
            enabled=self.context.backup_enabled,
            backup_directory=self.context.backup_directory,
            keep_latest=self.context.backup_keep_latest,
        )
        output: list[str] = []
        for i, note in enumerate(notes):
            output.append(f"## {note.title}")
            if note.body:
                output.extend(note.body.splitlines())
            if i < len(notes) - 1:
                output.append("---")
        path.write_text("\n".join(output) + ("\n" if output else ""), encoding="utf-8")
