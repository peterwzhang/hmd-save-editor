"""Application entry point, callable as `main()`.

Kept out of __main__.py (which just re-exports it) because PyInstaller
reserves the name `__main__` for its own bootstrap and won't bundle any
submodule also called `__main__` - `from hmd_editor.__main__ import main`
fails at runtime in a frozen build with "No module named 'hmd_editor.__main__'"
even though the same import works fine from source. See
packaging/pyinstaller_entry.py, which imports this module instead.
"""

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
