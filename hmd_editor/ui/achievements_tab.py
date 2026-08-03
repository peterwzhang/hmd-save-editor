"""Achievements tab: progress, playtime, and best-run editing over global.json."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..model import achievements as achievements_model
from .widgets import count_spinbox, fraction_spinbox, money_spinbox

ACHIEVEMENT_COLUMNS = ["Name", "Progress", "Complete"]
BEST_RUN_COLUMNS = ["Roster", "Best round", "Money earned", "Money spent", "Pinned", ""]


class AchievementsTab(QWidget):
    def __init__(self, catalog, on_changed: Callable[[], None]):
        super().__init__()
        self.catalog = catalog
        self.on_changed = on_changed
        self.bundle = None

        layout = QVBoxLayout(self)

        self.placeholder = QLabel(
            "Open a save folder with global.json to edit achievements."
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        content_layout.addLayout(self._build_playtime_row())

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search achievements...")
        self.search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(QLabel("Achievements"))
        search_row.addWidget(self.search_edit, 1)
        content_layout.addLayout(search_row)

        self.achievements_table = QTableWidget()
        self.achievements_table.setColumnCount(len(ACHIEVEMENT_COLUMNS))
        self.achievements_table.setHorizontalHeaderLabels(ACHIEVEMENT_COLUMNS)
        self.achievements_table.setSortingEnabled(True)
        self.achievements_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.achievements_table.verticalHeader().setVisible(False)
        content_layout.addWidget(self.achievements_table, 2)

        content_layout.addWidget(QLabel("Best runs"))
        self.best_runs_table = QTableWidget()
        self.best_runs_table.setColumnCount(len(BEST_RUN_COLUMNS))
        self.best_runs_table.setHorizontalHeaderLabels(BEST_RUN_COLUMNS)
        self.best_runs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.best_runs_table.verticalHeader().setVisible(False)
        content_layout.addWidget(self.best_runs_table, 1)

        layout.addWidget(self.content)
        self.content.hide()

    def set_bundle(self, bundle) -> None:
        self.bundle = bundle
        if bundle is None:
            self.content.hide()
            self.placeholder.show()
            return
        self.placeholder.hide()
        self.content.show()
        self._rebuild_playtime()
        self._rebuild_achievements_table()
        self._rebuild_best_runs_table()

    def _notify_changed(self) -> None:
        self.on_changed()

    # -- playtime -----------------------------------------------------------------

    def _build_playtime_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Minutes played"))
        self.minutes_box = count_spinbox(0, maximum=10_000_000)
        self.minutes_box.valueChanged.connect(self._set_minutes_played)
        row.addWidget(self.minutes_box)
        row.addStretch(1)
        return row

    def _rebuild_playtime(self) -> None:
        self.minutes_box.blockSignals(True)
        self.minutes_box.setValue(int(self.bundle.global_data["minutes_played"]))
        self.minutes_box.blockSignals(False)

    def _set_minutes_played(self, value) -> None:
        achievements_model.set_minutes_played(self.bundle, value)
        self._notify_changed()

    # -- achievements ---------------------------------------------------------------

    def _rebuild_achievements_table(self) -> None:
        self.achievements_table.setSortingEnabled(False)
        achievements = sorted(self.bundle.global_data["achievement_progress"].items())
        self.achievements_table.clearContents()
        self.achievements_table.setRowCount(len(achievements))

        for row, (achievement_id, entry) in enumerate(achievements):
            name_item = QTableWidgetItem(_display_name(achievement_id))
            name_item.setData(Qt.ItemDataRole.UserRole, achievement_id)
            self.achievements_table.setItem(row, 0, name_item)

            progress_box = fraction_spinbox(entry["progress"])
            progress_box.valueChanged.connect(
                lambda v, aid=achievement_id: self._set_progress(aid, v)
            )
            self.achievements_table.setCellWidget(row, 1, progress_box)

            complete_box = QCheckBox()
            complete_box.setChecked(entry["complete"])
            complete_box.stateChanged.connect(
                lambda _state=0, aid=achievement_id, box=complete_box: self._set_complete(
                    aid, box.isChecked()
                )
            )
            self.achievements_table.setCellWidget(row, 2, complete_box)

        self.achievements_table.setSortingEnabled(True)
        self.achievements_table.resizeColumnsToContents()
        self._apply_filter()

    def _apply_filter(self) -> None:
        search = self.search_edit.text().strip().lower()
        for row in range(self.achievements_table.rowCount()):
            name = self.achievements_table.item(row, 0).text().lower()
            self.achievements_table.setRowHidden(row, bool(search) and search not in name)

    def _set_progress(self, achievement_id, value) -> None:
        achievements_model.set_progress(self.bundle, achievement_id, value)
        self._notify_changed()

    def _set_complete(self, achievement_id, complete) -> None:
        achievements_model.set_complete(self.bundle, achievement_id, complete)
        self._rebuild_achievements_table()
        self._notify_changed()

    # -- best runs ------------------------------------------------------------------------

    def _rebuild_best_runs_table(self) -> None:
        runs = achievements_model.list_best_runs(self.bundle)
        self.best_runs_table.clearContents()
        self.best_runs_table.setRowCount(len(runs))

        for row, (run_id, run) in enumerate(runs):
            roster = ", ".join(
                self.catalog.name_for(t) for t in run.get("dude_type_roster", [])
            )
            self.best_runs_table.setItem(row, 0, QTableWidgetItem(roster))

            round_box = count_spinbox(int(run.get("best_round", 0)), maximum=100_000)
            round_box.valueChanged.connect(
                lambda v, rid=run_id: self._set_best_run_field(rid, "best_round", v)
            )
            self.best_runs_table.setCellWidget(row, 1, round_box)

            earned_box = money_spinbox(run.get("money_earned", 0.0))
            earned_box.valueChanged.connect(
                lambda v, rid=run_id: self._set_best_run_field(rid, "money_earned", v)
            )
            self.best_runs_table.setCellWidget(row, 2, earned_box)

            spent_box = money_spinbox(run.get("money_spent", 0.0))
            spent_box.valueChanged.connect(
                lambda v, rid=run_id: self._set_best_run_field(rid, "money_spent", v)
            )
            self.best_runs_table.setCellWidget(row, 3, spent_box)

            pinned_box = QCheckBox()
            pinned_box.setChecked(run.get("pinned", False))
            pinned_box.stateChanged.connect(
                lambda _state=0, rid=run_id, box=pinned_box: self._set_pinned(
                    rid, box.isChecked()
                )
            )
            self.best_runs_table.setCellWidget(row, 4, pinned_box)

            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(
                lambda checked=False, rid=run_id: self._delete_run(rid)
            )
            self.best_runs_table.setCellWidget(row, 5, delete_button)

        self.best_runs_table.resizeColumnsToContents()

    def _set_best_run_field(self, run_id, field, value) -> None:
        achievements_model.set_best_run_field(self.bundle, run_id, field, value)
        self._notify_changed()

    def _set_pinned(self, run_id, pinned) -> None:
        achievements_model.set_best_run_pinned(self.bundle, run_id, pinned)
        self._notify_changed()

    def _delete_run(self, run_id) -> None:
        reply = QMessageBox.question(
            self,
            "Delete best run",
            "Delete this saved run permanently? This cannot be undone once saved.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        achievements_model.delete_best_run(self.bundle, run_id)
        self._rebuild_best_runs_table()
        self._notify_changed()


def _display_name(achievement_id: str) -> str:
    return achievement_id.replace("_", " ").title()
