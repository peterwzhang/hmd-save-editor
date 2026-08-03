"""First-run "download icons?" prompt and the background fetch behind it.

The site's robots.txt explicitly disallows AI crawlers from /sprites/ and
*.webp, on top of its general allow-all rule for ordinary clients. So this
never fetches anything on its own: SpriteDownloadPrompt.maybe_show() only
ever pops a dialog asking permission, and a download only starts after the
user clicks "Download" - the same action as running
`tools/fetch_catalog.py --sprites` by hand, just surfaced as a button.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QMessageBox, QProgressDialog, QWidget

from .. import sprite_fetch
from ..catalog import SPRITES_DIR, Catalog

SETTINGS_KEY_DECLINED = "sprites_download_declined"


class _DownloadWorker(QThread):
    progress = Signal(int, int)
    finished_with_failures = Signal(list)

    def __init__(self, sprite_paths: list):
        super().__init__()
        self._sprite_paths = sprite_paths
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        failed = sprite_fetch.download_sprites(
            self._sprite_paths,
            SPRITES_DIR,
            on_progress=lambda done, total: self.progress.emit(done, total),
            should_cancel=lambda: self._cancelled,
        )
        self.finished_with_failures.emit(failed)


class SpriteDownloadPrompt:
    """Owned by MainWindow. Call maybe_show() once at startup; it no-ops if
    icons are already cached or the user previously declined."""

    def __init__(self, parent: QWidget, catalog: Catalog, settings, on_done: Callable[[], None]):
        self._parent = parent
        self._catalog = catalog
        self._settings = settings
        self._on_done = on_done
        self._worker: Optional[_DownloadWorker] = None
        self._progress: Optional[QProgressDialog] = None
        self._total = 0

    def maybe_show(self) -> None:
        if self._settings.value(SETTINGS_KEY_DECLINED, False, type=bool):
            return
        missing = sprite_fetch.missing_sprite_paths(self._catalog.sprite_urls(), SPRITES_DIR)
        if not missing:
            return

        reply = QMessageBox.question(
            self._parent,
            "Download icons?",
            "HMD Save Editor can show real icons for dudes, relics, trinkets, "
            "and more, but they aren't bundled with the app.\n\n"
            f"Download {len(missing)} icons now from howmanydudes.com (a fan "
            "wiki)? They're cached locally in cache/sprites/ and nothing is "
            "uploaded. You can decline and items will show with a placeholder "
            "instead.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._settings.setValue(SETTINGS_KEY_DECLINED, True)
            return

        self._start_download(missing)

    def _start_download(self, missing: list) -> None:
        self._total = len(missing)
        self._progress = QProgressDialog(
            "Downloading icons...", "Cancel", 0, self._total, self._parent
        )
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.setValue(0)

        self._worker = _DownloadWorker(missing)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_with_failures.connect(self._on_finished)
        self._progress.canceled.connect(self._worker.cancel)
        self._worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        if self._progress is not None:
            self._progress.setValue(done)

    def _on_finished(self, failed: list) -> None:
        if self._progress is not None:
            self._progress.close()
            self._progress = None
        if failed:
            QMessageBox.warning(
                self._parent,
                "Some icons failed to download",
                f"{len(failed)} of {self._total} icons could not be downloaded "
                "(network issue?). You can try again by restarting the app, or "
                "run `uv run python tools/fetch_catalog.py --sprites` later.",
            )
        self._worker = None
        self._on_done()

    def shutdown(self) -> None:
        """Cancel and join the download thread. Must be called before the
        app quits - QThread aborts the process if its C++ object is
        destroyed while still running."""
        if self._worker is None:
            return
        self._worker.cancel()
        if not self._worker.wait(5000):
            self._worker.terminate()
            self._worker.wait()
