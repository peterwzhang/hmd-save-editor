"""Picks a Qt platform plugin (QT_QPA_PLATFORM) for entry-point setup.

WSLg's Wayland compositor has known popup-positioning bugs: a combo box
dropdown can get stranded on screen even after the window that opened it
moves. XCB (X11, via WSLg's XWayland) doesn't have this problem, so
hmd_editor.__main__ prefers it under WSL - but only once the xcb plugin's
runtime libraries are confirmed loadable, since a missing one there aborts
the whole process (qFatal) instead of falling back cleanly.
"""

from __future__ import annotations

import ctypes
from pathlib import Path

PROC_VERSION_PATH = Path("/proc/version")

XCB_REQUIRED_LIBS = (
    "libxcb-cursor.so.0",
    "libxkbcommon-x11.so.0",
    "libxcb-icccm.so.4",
    "libxcb-keysyms.so.1",
    "libxcb-xkb.so.1",
)


def is_wsl() -> bool:
    try:
        return "microsoft" in PROC_VERSION_PATH.read_text().lower()
    except OSError:
        return False


def xcb_runtime_available() -> bool:
    try:
        for lib in XCB_REQUIRED_LIBS:
            ctypes.CDLL(lib)
    except OSError:
        return False
    return True


def preferred_qpa_platform() -> str | None:
    """The QT_QPA_PLATFORM value hmd_editor should force, or None to leave
    Qt's own platform auto-detection alone."""
    if is_wsl() and xcb_runtime_available():
        return "xcb"
    return None
