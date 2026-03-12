from __future__ import annotations

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Header, Input, Static, TextArea

from dashboard_tui.config.settings import Settings, load_settings, save_ui_theme
from dashboard_tui.core.paths import ensure_app_dirs
from dashboard_tui.widgets.base import DashboardWidget
from dashboard_tui.widgets.notes import NotesWidget
from dashboard_tui.widgets.registry import load_enabled_widgets
from dashboard_tui.widgets.school import SchoolWidget
from dashboard_tui.widgets.system import SystemWidget
from dashboard_tui.widgets.todo import TodoWidget

# Textual 8.1.x can ship default CSS with a hatch declaration that fails parsing
# in some environments. Patch the base App CSS before subclass composition.
App.DEFAULT_CSS = App.DEFAULT_CSS.replace("hatch: right $panel;", "hatch: none;")


class DashboardPanel(Static):
    can_focus = True

    def __init__(self, widget: DashboardWidget, panel_id: str, panel_index: int) -> None:
        super().__init__(id=panel_id)
        self.widget = widget
        self.panel_index = panel_index
        self._sync_focus_indicator()

    def refresh_content(self) -> None:
        self._sync_focus_indicator()
        self.widget.set_active(self.has_focus)
        try:
            self.update(self.widget.render_text())
        except Exception as exc:  # pragma: no cover
            self.update(f"[b]{self.widget.title}[/b]\\nError: {exc}")

    def on_focus(self, event: events.Focus) -> None:
        self.refresh_content()

    def on_blur(self, event: events.Blur) -> None:
        self.refresh_content()

    def _sync_focus_indicator(self) -> None:
        self.border_title = f" {self.panel_index}. {self.widget.title} "
        self.border_subtitle = ""


class TodoPanel(DashboardPanel):
    BINDINGS = [
        Binding("up", "task_up", "Task Up"),
        Binding("down", "task_down", "Task Down"),
        Binding("enter", "task_toggle", "Task Toggle"),
        Binding("a", "task_add", "Task Add"),
        Binding("e", "task_edit", "Task Edit"),
        Binding("delete", "task_delete", "Task Delete"),
    ]

    def action_task_up(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_task_up()

    def action_task_down(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_task_down()

    def action_task_toggle(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_task_toggle()

    def action_task_add(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_task_add()

    def action_task_edit(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_task_edit()

    def action_task_delete(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_task_delete()


class SystemPanel(DashboardPanel):
    BINDINGS = [
        Binding("up", "system_up", "System Up"),
        Binding("down", "system_down", "System Down"),
        Binding("enter", "system_toggle", "System Details"),
    ]

    def action_system_up(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_system_up()

    def action_system_down(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_system_down()

    def action_system_toggle(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_system_toggle()


class SchoolPanel(DashboardPanel):
    BINDINGS = [
        Binding("enter", "school_open_canvas", "Open Canvas"),
    ]

    def action_school_open_canvas(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_school_open_canvas()


class NotesPanel(DashboardPanel):
    BINDINGS = [
        Binding("up", "note_up", "Note Up"),
        Binding("down", "note_down", "Note Down"),
        Binding("enter", "note_toggle", "Open Note"),
        Binding("a", "note_add", "Note Add"),
        Binding("e", "note_edit", "Note Edit"),
        Binding("delete", "note_delete", "Note Delete"),
    ]

    def action_note_up(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_note_up()

    def action_note_down(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_note_down()

    def action_note_toggle(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_note_toggle()

    def action_note_add(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_note_add()

    def action_note_edit(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_note_edit()

    def action_note_delete(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_note_delete()


class TaskEditorModal(ModalScreen[str | None]):
    def __init__(self, title: str, initial_value: str = "") -> None:
        super().__init__()
        self._title = title
        self._initial_value = initial_value

    def compose(self) -> ComposeResult:
        with Vertical(id="task-editor"):
            yield Static(self._title, id="task-editor-title")
            yield Input(value=self._initial_value, placeholder="Type task and press Enter", id="task-editor-input")
            yield Static("Enter: save    Esc: cancel", id="task-editor-help")

    def on_mount(self) -> None:
        self.query_one("#task-editor-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        self.dismiss(text if text else None)

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)


class NoteEditorModal(ModalScreen[tuple[str, str] | None]):
    def __init__(self, title: str, initial_title: str = "", initial_body: str = "") -> None:
        super().__init__()
        self._title = title
        self._initial_title = initial_title
        self._initial_body = initial_body

    def compose(self) -> ComposeResult:
        with Vertical(id="note-editor"):
            yield Static(self._title, id="note-editor-title")
            yield Input(value=self._initial_title, placeholder="Note title", id="note-editor-note-title")
            yield TextArea(text=self._initial_body, id="note-editor-body")
            yield Static("Tab/Shift+Tab: switch field    Ctrl+S: save    Esc: cancel", id="note-editor-help")

    def on_mount(self) -> None:
        self.query_one("#note-editor-note-title", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "note-editor-note-title":
            event.stop()
            self.query_one("#note-editor-body", TextArea).focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "tab":
            if isinstance(self.focused, Input) and self.focused.id == "note-editor-note-title":
                event.stop()
                self.query_one("#note-editor-body", TextArea).focus()
                return
        if event.key == "shift+tab":
            if isinstance(self.focused, TextArea):
                event.stop()
                self.query_one("#note-editor-note-title", Input).focus()
                return
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
            return
        if event.key == "ctrl+s":
            event.stop()
            title = self.query_one("#note-editor-note-title", Input).value.strip()
            body = self.query_one("#note-editor-body", TextArea).text
            self.dismiss((title, body) if title else None)


class DashboardScreen(Screen):
    def __init__(self, settings: Settings, widgets: list[DashboardWidget]) -> None:
        super().__init__()
        self.settings = settings
        self.widgets = widgets
        self.dense = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Grid(id="dashboard-grid"):
            for i, widget in enumerate(self.widgets, start=1):
                if isinstance(widget, TodoWidget):
                    yield TodoPanel(widget, panel_id=f"panel-{i}", panel_index=i)
                elif isinstance(widget, SchoolWidget):
                    yield SchoolPanel(widget, panel_id=f"panel-{i}", panel_index=i)
                elif isinstance(widget, SystemWidget):
                    yield SystemPanel(widget, panel_id=f"panel-{i}", panel_index=i)
                elif isinstance(widget, NotesWidget):
                    yield NotesPanel(widget, panel_id=f"panel-{i}", panel_index=i)
                else:
                    yield DashboardPanel(widget, panel_id=f"panel-{i}", panel_index=i)
        yield Footer()

    def on_mount(self) -> None:
        if not self.settings.ui.show_footer_help:
            self.query_one(Footer).display = False

        self.refresh_panels()
        self.set_interval(self.settings.ui.refresh_seconds, self.refresh_panels)

    def refresh_panels(self) -> None:
        for panel in self.query(DashboardPanel):
            panel.refresh_content()

    def action_refresh(self) -> None:
        self.refresh_panels()

    def action_toggle_dense(self) -> None:
        self.dense = not self.dense
        grid = self.query_one("#dashboard-grid", Grid)
        if self.dense:
            grid.add_class("dense")
        else:
            grid.remove_class("dense")

    def action_focus_panel(self, index: int) -> None:
        panel = self.query_one(f"#panel-{index}", DashboardPanel)
        self.set_focus(panel)

    def action_task_up(self) -> None:
        self._update_focused_task_selection(-1)

    def action_task_down(self) -> None:
        self._update_focused_task_selection(1)

    def action_task_toggle(self) -> None:
        panel = self.focused
        if not isinstance(panel, DashboardPanel):
            return
        if panel.widget.toggle_selected():
            panel.refresh_content()

    def action_task_add(self) -> None:
        panel = self._focused_todo_panel()
        if panel is None:
            return
        self.app.push_screen(
            TaskEditorModal("Add Task"),
            callback=lambda value: self._apply_task_add(panel, value),
        )

    def action_task_edit(self) -> None:
        panel = self._focused_todo_panel()
        if panel is None:
            return
        selected = panel.widget.get_selected_text()
        if selected is None:
            return
        self.app.push_screen(
            TaskEditorModal("Edit Task", initial_value=selected),
            callback=lambda value: self._apply_task_edit(panel, value),
        )

    def action_task_delete(self) -> None:
        panel = self._focused_todo_panel()
        if panel is None:
            return
        if panel.widget.delete_selected():
            panel.refresh_content()

    def action_system_up(self) -> None:
        self._update_focused_system_selection(-1)

    def action_system_down(self) -> None:
        self._update_focused_system_selection(1)

    def action_system_toggle(self) -> None:
        panel = self._focused_system_panel()
        if panel is None:
            return
        if panel.widget.toggle_selected():
            panel.refresh_content()

    def action_school_open_canvas(self) -> None:
        panel = self._focused_school_panel()
        if panel is None:
            return
        panel.widget.open_canvas_tab()

    def action_note_up(self) -> None:
        self._update_focused_note_selection(-1)

    def action_note_down(self) -> None:
        self._update_focused_note_selection(1)

    def action_note_toggle(self) -> None:
        panel = self._focused_notes_panel()
        if panel is None:
            return
        if panel.widget.toggle_selected():
            panel.refresh_content()

    def action_note_add(self) -> None:
        panel = self._focused_notes_panel()
        if panel is None:
            return
        self.app.push_screen(
            NoteEditorModal("Add Note"),
            callback=lambda value: self._apply_note_add(panel, value),
        )

    def action_note_edit(self) -> None:
        panel = self._focused_notes_panel()
        if panel is None:
            return
        selected = panel.widget.get_selected_note()
        if selected is None:
            return
        title, body = selected
        self.app.push_screen(
            NoteEditorModal("Edit Note", initial_title=title, initial_body=body),
            callback=lambda value: self._apply_note_edit(panel, value),
        )

    def action_note_delete(self) -> None:
        panel = self._focused_notes_panel()
        if panel is None:
            return
        if panel.widget.delete_selected():
            panel.refresh_content()

    def _update_focused_task_selection(self, delta: int) -> None:
        panel = self.focused
        if not isinstance(panel, DashboardPanel):
            return
        if panel.widget.move_selection(delta):
            panel.refresh_content()

    def _update_focused_system_selection(self, delta: int) -> None:
        panel = self._focused_system_panel()
        if panel is None:
            return
        if panel.widget.move_selection(delta):
            panel.refresh_content()

    def _update_focused_note_selection(self, delta: int) -> None:
        panel = self._focused_notes_panel()
        if panel is None:
            return
        if panel.widget.move_selection(delta):
            panel.refresh_content()

    def _focused_todo_panel(self) -> DashboardPanel | None:
        panel = self.focused
        if not isinstance(panel, DashboardPanel):
            return None
        if not isinstance(panel.widget, TodoWidget):
            return None
        return panel

    def _focused_system_panel(self) -> DashboardPanel | None:
        panel = self.focused
        if not isinstance(panel, DashboardPanel):
            return None
        if not isinstance(panel.widget, SystemWidget):
            return None
        return panel

    def _focused_school_panel(self) -> DashboardPanel | None:
        panel = self.focused
        if not isinstance(panel, DashboardPanel):
            return None
        if not isinstance(panel.widget, SchoolWidget):
            return None
        return panel

    def _focused_notes_panel(self) -> DashboardPanel | None:
        panel = self.focused
        if not isinstance(panel, DashboardPanel):
            return None
        if not isinstance(panel.widget, NotesWidget):
            return None
        return panel

    def _apply_task_add(self, panel: DashboardPanel, value: str | None) -> None:
        if value is None:
            return
        if panel.widget.add_task(value):
            panel.refresh_content()

    def _apply_task_edit(self, panel: DashboardPanel, value: str | None) -> None:
        if value is None:
            return
        if panel.widget.edit_selected(value):
            panel.refresh_content()

    def _apply_note_add(self, panel: DashboardPanel, value: tuple[str, str] | None) -> None:
        if value is None:
            return
        title, body = value
        if panel.widget.add_note(title, body):
            panel.refresh_content()

    def _apply_note_edit(self, panel: DashboardPanel, value: tuple[str, str] | None) -> None:
        if value is None:
            return
        title, body = value
        if panel.widget.edit_selected(title, body):
            panel.refresh_content()


class DashboardApp(App[None]):
    # Load theme tokens first, then structural styles.
    CSS_PATH = ["theme.tcss", "styles.tcss"]
    TITLE = "avery dashboard"
    SUB_TITLE = ""
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "toggle_dense", "Dense"),
        Binding("1", "focus_panel(1)", "Panel 1", show=False),
        Binding("2", "focus_panel(2)", "Panel 2", show=False),
        Binding("3", "focus_panel(3)", "Panel 3", show=False),
        Binding("4", "focus_panel(4)", "Panel 4", show=False),
        Binding("5", "focus_panel(5)", "Panel 5", show=False),
        Binding("6", "focus_panel(6)", "Panel 6", show=False),
        Binding("7", "focus_panel(7)", "Panel 7", show=False),
        Binding("8", "focus_panel(8)", "Panel 8", show=False),
        Binding("9", "focus_panel(9)", "Panel 9", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        ensure_app_dirs()
        self.settings = load_settings()
        self.widgets = load_enabled_widgets(self.settings)
        self._persist_theme_changes = False
        try:
            self.theme = self.settings.ui.theme
        except Exception:
            pass

    def on_mount(self) -> None:
        self._persist_theme_changes = True
        self.push_screen(DashboardScreen(self.settings, self.widgets))

    def watch_theme(self, theme_name: str) -> None:
        if self._persist_theme_changes:
            save_ui_theme(theme_name)

    def action_refresh(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_refresh()

    def action_toggle_dense(self) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.action_toggle_dense()

    def action_focus_panel(self, index: int) -> None:
        screen = self.screen
        if isinstance(screen, DashboardScreen) and 1 <= index <= len(self.widgets):
            screen.action_focus_panel(index)

def build_app() -> DashboardApp:
    return DashboardApp()
