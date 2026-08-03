"""Entry point: `python -m hmd_editor` or the `hmd-save-editor` console script."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow

THEME_PATH = Path(__file__).parent / "ui" / "theme.qss"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("HMD Save Editor")
    if THEME_PATH.is_file():
        app.setStyleSheet(THEME_PATH.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
