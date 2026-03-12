# Personal Dashboard TUI Starter

A starter project for a personal terminal dashboard using [Textual](https://textual.textualize.io/).

## Features

- Multi-panel dashboard layout (2x2 grid)
- Pluggable widget architecture
- Built-in widgets: system stats, school due dates, tasks, notes
- Check off tasks directly in the Tasks panel (`Up`/`Down` + `Enter`)
- Notes panel supports title selection and expandable full note content
- Config file in `~/.config/dashboard-tui/config.toml`
- Theme file for color/style customization: `src/dashboard_tui/theme.tcss`
- Cache/config directory bootstrapping
- Keybindings for refresh, focus, dense mode, and quit

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
dashboard-tui
```

## Keybindings

Global:

- `q`: quit
- `r`: refresh all panels
- `d`: toggle dense mode
- `1` to `9`: focus panel (hidden from footer hint)

Tasks pane only (shown while Tasks is focused):

- `Up`, `Down`: move task selection (focused Tasks panel)
- `Enter`: toggle selected task done/undone
- `a`: add a new task (in dashboard)
- `e`: edit selected task text (in dashboard)
- `Delete`: remove selected task

System pane only (shown while System is focused):

- `Up`, `Down`: select CPU / RAM / Disk
- `Enter`: expand or collapse top 5 processes for the selected metric

School pane:

- Shows due items from Canvas iCal feed for the next 10 days by default
- Configure feed URL under `[widgets.school].url`
- `Enter`: open Canvas in your browser

Notes pane only (shown while Notes is focused):

- `Up`, `Down`: move note selection
- `Enter`: expand or collapse full selected note
- `a`: add a note (title + body)
- `e`: edit selected note
- `Delete`: remove selected note

Each panel title includes its pane number (for example `1. System`, `3. Tasks`).

## Project Layout

- `src/dashboard_tui/app.py`: app and screen composition
- `src/dashboard_tui/main.py`: CLI entrypoint
- `src/dashboard_tui/theme.tcss`: editable color/style tokens
- `src/dashboard_tui/config/settings.py`: config loading/defaults
- `src/dashboard_tui/core/paths.py`: config/cache paths
- `src/dashboard_tui/widgets/`: widget base + built-in widgets

## Config

On first run, this file is created:

- `~/.config/dashboard-tui/config.toml`

You can enable/disable widgets and change titles/paths there.
The current Textual theme is also stored there under `[ui].theme` and restored on startup.

School pane config example:

```toml
[widgets.school]
enabled = true
title = "School"
url = "https://<your-canvas-host>/feeds/calendars/user_<token>.ics"
open_url = "https://<your-canvas-host>/"
days = 10
```

Automatic backups for tasks and notes are configured under `[backup]`:

- `enabled`: turn backups on/off
- `directory`: folder where backups are written
- `keep_latest`: how many backup files to keep per source file

Example:

```toml
[backup]
enabled = true
directory = "/home/avery/my-dashboard-backups"
keep_latest = 50
```

## Notes

In the Notes panel:

1. Use `Up` / `Down` to select a note title.
2. Press `Enter` to expand or collapse the full note body.
3. Press `a` to add a note, `e` to edit, or `Delete` to remove.

Notes are stored in the configured notes file (`~/.config/dashboard-tui/notes.txt` by default)
using a simple section format (`## title` blocks).

## Tasks with Checkboxes

The todo file supports plain lines and markdown-style checkboxes:

- `Buy groceries`
- `- [ ] Write report`
- `- [x] Pay internet bill`

In the dashboard:

1. Focus the Tasks panel (`1`-`4`).
2. Move selection with `Up` / `Down`.
3. Press `Enter` to check or uncheck the selected task.
4. Press `a` to add, `e` to edit, or `Delete` to remove tasks directly.

## Theme Customization

Edit:

- `src/dashboard_tui/theme.tcss`

By default, this file does not hardcode colors, so command palette `Change Theme`
applies across the entire dashboard.

If you want fixed brand colors, uncomment token overrides in `theme.tcss`
(for example `$surface`, `$panel`, `$accent`, `$success`).

## Extending with Widgets

1. Add a widget class in `src/dashboard_tui/widgets/` implementing `DashboardWidget`.
2. Register it in `src/dashboard_tui/widgets/registry.py`.
3. Add config for it in default config text if desired.
