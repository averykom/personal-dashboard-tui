from __future__ import annotations

from dashboard_tui.app import build_app


def run() -> None:
    build_app().run()


if __name__ == "__main__":
    run()
