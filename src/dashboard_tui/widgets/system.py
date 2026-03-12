from __future__ import annotations

import platform
from dataclasses import dataclass

import psutil

from dashboard_tui.widgets.base import DashboardWidget


@dataclass(slots=True)
class _Metric:
    label: str
    key: str
    value: float


class SystemWidget(DashboardWidget):
    def __init__(self, context) -> None:
        super().__init__(context)
        self.selected_index = 0
        self.show_details = False

    def render_text(self) -> str:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        host = platform.node() or "unknown"
        metrics = [
            _Metric(label="CPU", key="cpu", value=cpu),
            _Metric(label="RAM", key="ram", value=mem),
            _Metric(label="Disk", key="disk", value=disk),
        ]
        self.selected_index = max(0, min(self.selected_index, len(metrics) - 1))
        selected = metrics[self.selected_index]

        lines = [f"[b]{self.title}[/b]", f"Host: {host}"]
        for i, metric in enumerate(metrics):
            pointer = ">" if self.is_active and i == self.selected_index else " "
            lines.append(f"{pointer} {metric.label}: {metric.value:.1f}%")

        if self.show_details:
            lines.append("")
            lines.append(f"Top 5 by {selected.label}:")
            for idx, entry in enumerate(self._top_consumers(selected.key), start=1):
                lines.append(f"{idx}. {entry}")

        return "\n".join(lines)

    def move_selection(self, delta: int) -> bool:
        self.selected_index = max(0, min(self.selected_index + delta, 2))
        return True

    def toggle_selected(self) -> bool:
        self.show_details = not self.show_details
        return True

    def _top_consumers(self, metric_key: str) -> list[str]:
        rows: list[tuple[float, str]] = []

        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info.get("name") or f"pid {proc.pid}"
                if metric_key == "cpu":
                    value = proc.cpu_percent(interval=None)
                    rendered = f"{name} ({value:.1f}%)"
                elif metric_key == "ram":
                    rss = proc.memory_info().rss
                    value = float(rss)
                    rendered = f"{name} ({self._human_bytes(rss)})"
                else:
                    counters = proc.io_counters()
                    total_io = counters.read_bytes + counters.write_bytes
                    value = float(total_io)
                    rendered = f"{name} ({self._human_bytes(total_io)} I/O)"
                rows.append((value, rendered))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        rows.sort(key=lambda item: item[0], reverse=True)
        top = [row[1] for row in rows[:5] if row[0] > 0]
        if not top:
            return ["No process data available yet."]
        return top

    def _human_bytes(self, value: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        size = float(value)
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f"{size:.1f}{units[unit_index]}"
