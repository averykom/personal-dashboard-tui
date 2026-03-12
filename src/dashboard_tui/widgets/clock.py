from __future__ import annotations

from datetime import datetime

from dashboard_tui.widgets.base import DashboardWidget


class ClockWidget(DashboardWidget):
    def render_text(self) -> str:
        now = datetime.now()
        return (
            f"[b]{self.title}[/b]\n"
            f"{now:%A, %B %d, %Y}\n"
            f"{now:%-I:%H:%M:%S %p}"
        )
