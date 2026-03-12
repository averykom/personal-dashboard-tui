from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil


def backup_file(
    source: Path,
    *,
    enabled: bool,
    backup_directory: str | None,
    keep_latest: int,
) -> None:
    if not enabled or not backup_directory or not source.exists():
        return

    backup_dir = Path(backup_directory).expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_name = f"{source.name}.{timestamp}.bak"
    backup_path = backup_dir / backup_name
    shutil.copy2(source, backup_path)

    _prune_backups(backup_dir, source.name, keep_latest)


def _prune_backups(backup_dir: Path, source_name: str, keep_latest: int) -> None:
    if keep_latest <= 0:
        keep_latest = 1

    backups = sorted(
        backup_dir.glob(f"{source_name}.*.bak"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old_path in backups[keep_latest:]:
        try:
            old_path.unlink()
        except OSError:
            continue
