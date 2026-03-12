from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlparse
import webbrowser

import requests
from rich.markup import escape

from dashboard_tui.core.paths import cache_dir
from dashboard_tui.widgets.base import DashboardWidget


@dataclass(slots=True)
class DueItem:
    due_at: datetime
    summary: str
    all_day: bool = False


class SchoolWidget(DashboardWidget):
    cache_ttl_seconds = 3600.0

    def __init__(self, context) -> None:
        super().__init__(context)
        self._cached_items: list[DueItem] = []
        self._last_error: str | None = None
        self._last_fetch_at = 0.0
        self._cache_path = self._build_cache_path(context.source_url or "")
        self._load_persisted_cache()

    def render_text(self) -> str:
        days = self.context.days if self.context.days and self.context.days > 0 else 10
        source = self.context.source_url or ""
        lines = [f"[b]{self.title}[/b]"]

        if not source.strip():
            lines.append("Set [widgets.school].url in config.toml")
            lines.append("Paste your Canvas iCal feed URL.")
            return "\n".join(lines)

        self._refresh_if_needed(source)
        if self._last_error:
            lines.append(f"Error: {escape(self._last_error)}")
            return "\n".join(lines)

        now = datetime.now()
        until = now + timedelta(days=days)
        items = [item for item in self._cached_items if now <= item.due_at <= until]

        if not items:
            lines.append(f"No due items in next {days} days.")
            return "\n".join(lines)

        visible = items[:10]
        for item in visible:
            if item.all_day:
                when = item.due_at.strftime("%a %b %d (all day)")
            else:
                when = item.due_at.strftime("%a %b %d %I:%M %p")
            lines.append(f"- {when}  {escape(item.summary)}")

        if len(items) > len(visible):
            lines.append(f"... +{len(items) - len(visible)} more")

        return "\n".join(lines)

    def _refresh_if_needed(self, source: str) -> None:
        now = time.time()
        if self._cached_items and now - self._last_fetch_at < self.cache_ttl_seconds:
            return

        try:
            ics_text = self._load_ics(source)
            self._cached_items = self._parse_ics(ics_text)
            self._last_error = None
            self._last_fetch_at = now
            self._persist_cache()
        except Exception as exc:
            self._last_error = str(exc)
            self._last_fetch_at = now

    def open_canvas_tab(self) -> bool:
        url = self._canvas_url()
        if not url:
            return False
        return webbrowser.open(url, new=2)

    def _load_ics(self, source: str) -> str:
        if source.startswith("http://") or source.startswith("https://"):
            response = requests.get(source, timeout=10)
            response.raise_for_status()
            return response.text

        path = Path(source).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"iCal file not found: {path}")
        return path.read_text(encoding="utf-8")

    def _parse_ics(self, raw: str) -> list[DueItem]:
        lines = self._unfold_lines(raw)
        items: list[DueItem] = []

        in_event = False
        event_map: dict[str, tuple[str, str]] = {}
        for line in lines:
            if line == "BEGIN:VEVENT":
                in_event = True
                event_map = {}
                continue
            if line == "END:VEVENT":
                in_event = False
                item = self._event_to_due_item(event_map)
                if item is not None:
                    items.append(item)
                event_map = {}
                continue
            if not in_event or ":" not in line:
                continue

            key_with_params, value = line.split(":", 1)
            key = key_with_params.split(";", 1)[0]
            event_map[key] = (key_with_params, value)

        items.sort(key=lambda item: item.due_at)
        return items

    def _event_to_due_item(self, event_map: dict[str, tuple[str, str]]) -> DueItem | None:
        if "DTSTART" not in event_map:
            return None
        key, raw_dt = event_map["DTSTART"]
        parsed = self._parse_dt(key, raw_dt)
        if parsed is None:
            return None
        due_at, all_day = parsed
        summary = event_map.get("SUMMARY", ("", "Untitled item"))[1].strip() or "Untitled item"
        summary = summary.replace("\\n", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
        return DueItem(due_at=due_at, summary=summary, all_day=all_day)

    def _parse_dt(self, key: str, value: str) -> tuple[datetime, bool] | None:
        cleaned = value.strip()
        if "VALUE=DATE" in key:
            try:
                due = datetime.strptime(cleaned, "%Y%m%d")
            except ValueError:
                return None
            return due, True

        if cleaned.endswith("Z"):
            for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%MZ"):
                try:
                    due_utc = datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
                    return due_utc.astimezone().replace(tzinfo=None), False
                except ValueError:
                    continue
            return None

        for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                return datetime.strptime(cleaned, fmt), False
            except ValueError:
                continue
        return None

    def _unfold_lines(self, raw: str) -> list[str]:
        normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
        source_lines = normalized.split("\n")
        out: list[str] = []
        for line in source_lines:
            if not line:
                continue
            if line.startswith((" ", "\t")) and out:
                out[-1] += line[1:]
            else:
                out.append(line)
        return out

    def _build_cache_path(self, source: str) -> Path:
        cache_root = cache_dir()
        cache_root.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        return cache_root / f"school-{digest}.json"

    def _persist_cache(self) -> None:
        payload = {
            "fetched_at": self._last_fetch_at,
            "items": [
                {
                    "due_at": item.due_at.isoformat(),
                    "summary": item.summary,
                    "all_day": item.all_day,
                }
                for item in self._cached_items
            ],
        }
        self._cache_path.write_text(json.dumps(payload), encoding="utf-8")

    def _load_persisted_cache(self) -> None:
        if not self._cache_path.exists():
            return
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            fetched_at = float(payload.get("fetched_at", 0.0))
            items_raw = payload.get("items", [])
            items: list[DueItem] = []
            for row in items_raw:
                due_at = datetime.fromisoformat(str(row["due_at"]))
                summary = str(row.get("summary", "Untitled item"))
                all_day = bool(row.get("all_day", False))
                items.append(DueItem(due_at=due_at, summary=summary, all_day=all_day))
            self._cached_items = items
            self._last_fetch_at = fetched_at
        except Exception:
            self._cached_items = []
            self._last_fetch_at = 0.0

    def _canvas_url(self) -> str | None:
        explicit = (self.context.open_url or "").strip()
        if explicit:
            return explicit
        source = (self.context.source_url or "").strip()
        if not (source.startswith("http://") or source.startswith("https://")):
            return None
        parsed = urlparse(source)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"
