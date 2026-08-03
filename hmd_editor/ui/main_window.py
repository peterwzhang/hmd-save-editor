"""Main application window: file bar, tabs, and the save/revert footer."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..catalog import get_catalog
from ..model import run as run_model
from ..savefile import SaveBundle
from .achievements_tab import AchievementsTab
from .collection_tab import CollectionTab
from .run_tab import RunTab
from .sprite_download import SpriteDownloadPrompt

ORG_NAME = "hmd-save-editor"
APP_NAME = "hmd-save-editor"
MAX_RECENT = 8


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HMD Save Editor")
        self.resize(1150, 780)
        self.setAcceptDrops(True)

        self.bundle: SaveBundle | None = None
        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.catalog = get_catalog()

        self._build_ui()
        self._refresh_recent_menu()
        self._set_bundle(None)

        self.sprite_download_prompt = SpriteDownloadPrompt(
            self, self.catalog, self.settings, self._on_sprites_downloaded
        )
        # Deferred so the main window is on screen before the prompt dialog is.
        QTimer.singleShot(0, self.sprite_download_prompt.maybe_show)
        QApplication.instance().aboutToQuit.connect(self.sprite_download_prompt.shutdown)

    # -- UI construction --------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addLayout(self._build_file_bar())

        self.cloud_banner = QLabel(
            "Steam Cloud can overwrite this save while the game or Steam is running. "
            "Close both before editing, or edit a copy and paste it back."
        )
        self.cloud_banner.setObjectName("cloudBanner")
        self.cloud_banner.setWordWrap(True)
        layout.addWidget(self.cloud_banner)

        self.tabs = QTabWidget()
        self.run_tab = RunTab(self.catalog, self._on_data_changed)
        self.collection_tab = CollectionTab(self.catalog, self._on_data_changed)
        self.achievements_tab = AchievementsTab(self.catalog, self._on_data_changed)
        self.tabs.addTab(self.run_tab, "Run")
        self.tabs.addTab(self.collection_tab, "Collection")
        self.tabs.addTab(self.achievements_tab, "Achievements")
        layout.addWidget(self.tabs, 1)

        layout.addLayout(self._build_footer())

        self.setCentralWidget(central)

    def _build_file_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        self.open_button = QPushButton("Open save folder...")
        self.open_button.clicked.connect(self._choose_folder)
        bar.addWidget(self.open_button)

        self.recent_button = QPushButton("Recent ▾")
        self.recent_menu = QMenu(self.recent_button)
        self.recent_button.setMenu(self.recent_menu)
        bar.addWidget(self.recent_button)

        self.path_label = QLabel("No save folder open")
        self.path_label.setObjectName("pathLabel")
        bar.addWidget(self.path_label, 1)
        return bar

    def _build_footer(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        bar.addWidget(self.status_label, 1)

        self.backup_checkbox = QCheckBox("Backup on save")
        self.backup_checkbox.setChecked(True)
        bar.addWidget(self.backup_checkbox)

        self.revert_button = QPushButton("Revert")
        self.revert_button.clicked.connect(self._revert)
        bar.addWidget(self.revert_button)

        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("saveButton")
        self.save_button.clicked.connect(self._save)
        bar.addWidget(self.save_button)
        return bar

    # -- drag & drop ------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        if path.is_file():
            path = path.parent
        self._open_folder(path)

    # -- opening files -------------------------------------------------------------

    def _choose_folder(self) -> None:
        start_dir = self.settings.value("last_folder", str(Path.home()))
        folder = QFileDialog.getExistingDirectory(self, "Open save folder", start_dir)
        if folder:
            self._open_folder(Path(folder))

    def _open_folder(self, folder: Path) -> None:
        try:
            bundle = SaveBundle.load(folder)
        except FileNotFoundError as e:
            QMessageBox.warning(self, "No save files found", str(e))
            return
        self._set_bundle(bundle)
        self._remember_recent(folder)
        self.settings.setValue("last_folder", str(folder))

    def _remember_recent(self, folder: Path) -> None:
        recent = self._recent_list()
        folder_str = str(folder)
        recent = [f for f in recent if f != folder_str]
        recent.insert(0, folder_str)
        recent = recent[:MAX_RECENT]
        self.settings.setValue("recent_folders", recent)
        self._refresh_recent_menu()

    def _recent_list(self) -> list:
        recent = self.settings.value("recent_folders", [])
        if not isinstance(recent, list):
            recent = [recent] if recent else []
        return recent

    def _refresh_recent_menu(self) -> None:
        self.recent_menu.clear()
        recent = self._recent_list()
        if not recent:
            action = self.recent_menu.addAction("(no recent folders)")
            action.setEnabled(False)
            return
        for folder_str in recent:
            action = self.recent_menu.addAction(folder_str)
            action.triggered.connect(
                lambda checked=False, f=folder_str: self._open_folder(Path(f))
            )

    # -- bundle wiring -----------------------------------------------------------------

    def _set_bundle(self, bundle) -> None:
        self.bundle = bundle
        has_bundle = bundle is not None

        self.path_label.setText(str(bundle.directory) if bundle else "No save folder open")

        has_run = bool(bundle and bundle.has("save_data.json"))
        has_global = bool(bundle and bundle.has("global.json"))

        self.run_tab.set_bundle(bundle if has_run else None)
        self.collection_tab.set_bundle(bundle if has_global else None)
        self.achievements_tab.set_bundle(bundle if has_global else None)

        self.tabs.setTabEnabled(0, has_run)
        self.tabs.setTabEnabled(1, has_global)
        self.tabs.setTabEnabled(2, has_global)

        self.cloud_banner.setVisible(has_bundle)
        self._on_data_changed()

    def _on_data_changed(self) -> None:
        dirty = bool(self.bundle and self.bundle.is_dirty())
        self.save_button.setEnabled(dirty)
        self.revert_button.setEnabled(dirty)

        warnings = []
        if self.bundle and self.bundle.has("save_data.json"):
            warnings = run_model.validate(self.bundle)

        if not self.bundle:
            self.status_label.setText("")
        elif warnings:
            self.status_label.setText("⚠ " + "; ".join(warnings))
        elif dirty:
            self.status_label.setText("Unsaved changes")
        else:
            self.status_label.setText("Up to date")

    def _save(self) -> None:
        if not self.bundle:
            return
        try:
            written = self.bundle.save(backup=self.backup_checkbox.isChecked())
        except OSError as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return
        if written:
            QMessageBox.information(self, "Saved", "Saved: " + ", ".join(written))
        self._on_data_changed()

    def _revert(self) -> None:
        if not self.bundle:
            return
        self.bundle.revert()
        self._set_bundle(self.bundle)

    def _on_sprites_downloaded(self) -> None:
        self.catalog.clear_icon_cache()
        if self.bundle is not None:
            self._set_bundle(self.bundle)
