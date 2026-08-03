"""Entry point: `python -m hmd_editor` or the `hmd-save-editor` console script."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .platform_select import preferred_qpa_platform
from .ui.main_window import MainWindow

THEME_PATH = Path(__file__).parent / "ui" / "theme.qss"


def main() -> int:
    if "QT_QPA_PLATFORM" not in os.environ:
        platform = preferred_qpa_platform()
        if platform is not None:
            os.environ["QT_QPA_PLATFORM"] = platform

    app = QApplication(sys.argv)
    app.setApplicationName("HMD Save Editor")
    # Windows 11's native style has a popup-positioning bug on Qt 6.7+
    # (QTBUG-124235) that detaches combo box dropdowns from their widget.
    # Fusion renders consistently across platforms and isn't affected.
    app.setStyle("Fusion")
    if THEME_PATH.is_file():
        app.setStyleSheet(THEME_PATH.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
