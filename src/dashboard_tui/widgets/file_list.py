from __future__ import annotations

from pathlib import Path

from dashboard_tui.widgets.base import DashboardWidget


class FileListWidget(DashboardWidget):
    empty_hint = "No entries yet. Add lines to the configured file."

    def render_text(self) -> str:
        path = self.context.source_path
        if not path:
            return f"[b]{self.title}[/b]\nNo file configured."

        file_path = Path(path).expanduser()
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("", encoding="utf-8")
            return (
                f"[b]{self.title}[/b]\n"
                f"Created: {file_path}\n"
                f"{self.empty_hint}"
            )

        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            return f"[b]{self.title}[/b]\n{self.empty_hint}"

        visible = lines[:8]
        body = "\n".join(f"- {line}" for line in visible)
        suffix = ""
        if len(lines) > len(visible):
            suffix = f"\n... +{len(lines) - len(visible)} more"

        return f"[b]{self.title}[/b]\n{body}{suffix}"
