from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

import requests
from rich.markup import escape

from dashboard_tui.core.paths import cache_dir
from dashboard_tui.widgets.base import DashboardWidget


@dataclass(slots=True)
class ContributionDay:
    day: date
    count: int
    level: int


@dataclass(slots=True)
class CommitSummary:
    repo: str
    message: str
    sha: str
    committed_at: datetime


class GitHubWidget(DashboardWidget):
    cache_ttl_seconds = 900.0
    _day_tag_pattern = re.compile(r"<[^>]*data-date\s*=\s*['\"][^'\"]+['\"][^>]*>")
    _attr_pattern = re.compile(r"([a-zA-Z_:.-]+)\s*=\s*(['\"])(.*?)\2")

    def __init__(self, context) -> None:
        super().__init__(context)
        self._contrib_days: list[ContributionDay] = []
        self._recent_commit: CommitSummary | None = None
        self._last_error: str | None = None
        self._last_fetch_at = 0.0
        self._cache_path = self._build_cache_path((context.username or "").strip().lower())
        self._load_persisted_cache()

    def render_text(self) -> str:
        lines = [f"[b]{self.title}[/b]"]
        username = (self.context.username or "").strip()
        if not username:
            lines.append("Set [widgets.github].username in config.toml")
            return "\n".join(lines)

        self._refresh_if_needed(username)
        lines.append(f"User: {escape(username)}")
        if self._last_error:
            lines.append(f"Error: {escape(self._last_error)}")
            return "\n".join(lines)

        lines.append(self._render_commit_line())
        lines.append("")
        lines.append("Contributions (last ~53 weeks)")
        lines.extend(self._render_heatmap_lines())
        return "\n".join(lines)

    def _refresh_if_needed(self, username: str) -> None:
        now = time.time()
        if now - self._last_fetch_at < self.cache_ttl_seconds and self._contrib_days:
            return

        try:
            token = self._token_value()
            self._contrib_days = self._fetch_contribution_days(username, token)
            self._recent_commit = self._fetch_recent_commit(username, token)
            self._last_error = None
            self._last_fetch_at = now
            self._persist_cache()
        except Exception as exc:
            self._last_error = str(exc)
            self._last_fetch_at = now

    def _fetch_contribution_days(self, username: str, token: str | None) -> list[ContributionDay]:
        headers = {"Accept": "text/html"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.get(
            f"https://github.com/users/{username}/contributions",
            headers=headers,
            timeout=10,
        )
        if response.status_code == 404:
            raise RuntimeError(f"GitHub user not found: {username}")
        response.raise_for_status()
        raw = response.text

        out: list[ContributionDay] = []
        for tag in self._day_tag_pattern.findall(raw):
            attrs = {name: value for name, _, value in self._attr_pattern.findall(tag)}
            raw_day = attrs.get("data-date")
            if not raw_day:
                continue
            try:
                parsed_day = date.fromisoformat(raw_day)
                count = int(attrs.get("data-count", "0"))
                level = int(attrs.get("data-level", "0"))
            except ValueError:
                continue
            out.append(ContributionDay(day=parsed_day, count=max(0, count), level=max(0, min(level, 4))))

        out.sort(key=lambda item: item.day)
        if not out:
            raise RuntimeError("No contribution data available.")
        return out[-371:]

    def _fetch_recent_commit(self, username: str, token: str | None) -> CommitSummary | None:
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.get(
            f"https://api.github.com/users/{username}/events/public?per_page=50",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        events = response.json()
        if not isinstance(events, list):
            return None

        repo_filter = (self.context.repo or "").strip()
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "PushEvent":
                continue

            repo_name = str((event.get("repo") or {}).get("name") or "")
            if repo_filter and not self._repo_matches(repo_filter, repo_name):
                continue

            payload = event.get("payload") or {}
            commits = payload.get("commits") or []
            if not isinstance(commits, list) or not commits:
                continue
            commit = commits[-1]
            if not isinstance(commit, dict):
                continue

            message = str(commit.get("message") or "").strip()
            sha = str(commit.get("sha") or "")
            created_at = str(event.get("created_at") or "")
            if not message or not sha or not created_at:
                continue

            try:
                committed_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            return CommitSummary(
                repo=repo_name or "(unknown repo)",
                message=message.splitlines()[0].strip(),
                sha=sha[:7],
                committed_at=committed_at,
            )
        return None

    def _repo_matches(self, configured: str, actual: str) -> bool:
        expected = configured.strip().lower()
        value = actual.strip().lower()
        if expected == value:
            return True
        if "/" in expected and expected.split("/", 1)[1] == value.split("/", 1)[-1]:
            return True
        return False

    def _render_commit_line(self) -> str:
        commit = self._recent_commit
        if commit is None:
            return "Recent commit: none found."
        when = self._format_age(commit.committed_at)
        msg = escape(commit.message)
        repo = escape(commit.repo)
        return f"Recent commit: {msg} ({repo} {commit.sha}, {when})"

    def _render_heatmap_lines(self) -> list[str]:
        if not self._contrib_days:
            return ["No contribution data."]

        by_day = {item.day: item for item in self._contrib_days}
        start = self._contrib_days[0].day
        end = self._contrib_days[-1].day
        total_days = (end - start).days + 1
        timeline: list[ContributionDay] = []
        for index in range(total_days):
            day = start + timedelta(days=index)
            item = by_day.get(day)
            if item is None:
                timeline.append(ContributionDay(day=day, count=0, level=0))
            else:
                timeline.append(item)
        timeline = timeline[-371:]

        # Keep zero-days visible so the heatmap has a stable shape.
        chars = "·░▒▓█"
        columns = [timeline[i : i + 7] for i in range(0, len(timeline), 7)]
        lines: list[str] = []
        for row in range(7):
            row_cells: list[str] = []
            for col in columns:
                if row >= len(col):
                    row_cells.append("·")
                    continue
                level = max(0, min(col[row].level, 4))
                row_cells.append(chars[level])
            lines.append("".join(row_cells))

        total = sum(item.count for item in timeline)
        lines.append(f"Total: {total} contributions")
        return lines

    def _format_age(self, when: datetime) -> str:
        now = datetime.now(timezone.utc)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        delta = now - when.astimezone(timezone.utc)
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return f"{seconds}s ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"

    def _token_value(self) -> str | None:
        token_env = (self.context.token_env or "").strip() or "GITHUB_TOKEN"
        token = os.environ.get(token_env, "").strip()
        return token or None

    def _build_cache_path(self, username: str) -> Path:
        key = username or "unknown"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        root = cache_dir()
        root.mkdir(parents=True, exist_ok=True)
        return root / f"github-{digest}.json"

    def _persist_cache(self) -> None:
        payload: dict[str, object] = {
            "fetched_at": self._last_fetch_at,
            "contrib_days": [
                {"day": item.day.isoformat(), "count": item.count, "level": item.level}
                for item in self._contrib_days
            ],
        }
        if self._recent_commit is not None:
            payload["recent_commit"] = {
                "repo": self._recent_commit.repo,
                "message": self._recent_commit.message,
                "sha": self._recent_commit.sha,
                "committed_at": self._recent_commit.committed_at.isoformat(),
            }
        self._cache_path.write_text(json.dumps(payload), encoding="utf-8")

    def _load_persisted_cache(self) -> None:
        if not self._cache_path.exists():
            return
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            self._last_fetch_at = float(payload.get("fetched_at", 0.0))

            contrib_days_raw = payload.get("contrib_days", [])
            days: list[ContributionDay] = []
            if isinstance(contrib_days_raw, list):
                for row in contrib_days_raw:
                    if not isinstance(row, dict):
                        continue
                    days.append(
                        ContributionDay(
                            day=date.fromisoformat(str(row.get("day"))),
                            count=max(0, int(row.get("count", 0))),
                            level=max(0, min(int(row.get("level", 0)), 4)),
                        )
                    )
            self._contrib_days = days

            commit_raw = payload.get("recent_commit")
            if isinstance(commit_raw, dict):
                self._recent_commit = CommitSummary(
                    repo=str(commit_raw.get("repo", "(unknown repo)")),
                    message=str(commit_raw.get("message", "")).strip(),
                    sha=str(commit_raw.get("sha", ""))[:7],
                    committed_at=datetime.fromisoformat(str(commit_raw.get("committed_at"))),
                )
        except Exception:
            self._contrib_days = []
            self._recent_commit = None
            self._last_fetch_at = 0.0
