"""Collection tab: discovery and star editing over global.json (the Dudex)."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..model import collection as collection_model
from .widgets import combo_box, icon_label

TIER_COUNT = 4
COLLECTIBLE_KINDS = ("dude", "relic", "trinket")
COLUMNS = ["Icon", "Name", "Kind", "Discovered", "Silver", "Gold", "Rounds", "Best round"]


class CollectionTab(QWidget):
    def __init__(self, catalog, on_changed: Callable[[], None]):
        super().__init__()
        self.catalog = catalog
        self.on_changed = on_changed
        self.bundle = None
        self.tier = 1

        layout = QVBoxLayout(self)

        self.placeholder = QLabel(
            "Open a save folder with global.json to edit your collection."
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addLayout(self._build_filter_bar())

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        content_layout.addWidget(self.table, 1)

        content_layout.addLayout(self._build_bulk_bar())

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
        self._refresh_tier_buttons()
        self._rebuild_table()

    def _notify_changed(self) -> None:
        self.on_changed()

    # -- filter bar ---------------------------------------------------------------

    def _build_filter_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()

        # Plain toggle buttons rather than a combo box: there are only 3
        # tiers, and a dropdown popup here would float directly over the
        # table below, making it easy to mis-click a row's star checkboxes
        # while dismissing the popup.
        row.addWidget(QLabel("Tier"))
        self.tier_button_group = QButtonGroup(self)
        self.tier_button_group.setExclusive(True)
        self.tier_button_group.idClicked.connect(self._on_tier_changed)
        for tier in range(1, TIER_COUNT):
            button = QPushButton(f"Tier {tier}")
            button.setCheckable(True)
            self.tier_button_group.addButton(button, tier)
            row.addWidget(button)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name...")
        self.search_edit.textChanged.connect(self._apply_filter)
        row.addWidget(self.search_edit, 1)

        self.kind_combo = combo_box()
        self.kind_combo.addItem("All kinds", None)
        for kind in COLLECTIBLE_KINDS:
            self.kind_combo.addItem(kind.capitalize(), kind)
        self.kind_combo.currentIndexChanged.connect(self._apply_filter)
        row.addWidget(self.kind_combo)

        self.hide_discovered_checkbox = QCheckBox("Hide discovered")
        self.hide_discovered_checkbox.stateChanged.connect(self._apply_filter)
        row.addWidget(self.hide_discovered_checkbox)

        return row

    def _refresh_tier_buttons(self) -> None:
        # Tier 0 isn't a real in-game tier (the game only has 1, 2, 3) - the
        # save file just carries an unused slot 0 in collectibles_by_tier.
        for tier in range(1, TIER_COUNT):
            button = self.tier_button_group.button(tier)
            count = len(self.bundle.global_data["collectibles_by_tier"][tier])
            button.setText(f"Tier {tier} ({count})")
            button.blockSignals(True)
            button.setChecked(tier == self.tier)
            button.blockSignals(False)

    def _on_tier_changed(self, tier: int) -> None:
        self.tier = tier
        self._rebuild_table()

    def _apply_filter(self) -> None:
        search = self.search_edit.text().strip().lower()
        kind_filter = self.kind_combo.currentData()
        hide_discovered = self.hide_discovered_checkbox.isChecked()

        for row in range(self.table.rowCount()):
            item_id = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
            name = self.catalog.name_for(item_id)
            kind = self.catalog.kind_for(item_id)
            level = collection_model.star_level(self.bundle, self.tier, item_id)

            visible = True
            if search and search not in name.lower():
                visible = False
            if kind_filter and kind != kind_filter:
                visible = False
            if hide_discovered and level != "none":
                visible = False

            self.table.setRowHidden(row, not visible)

    # -- table ------------------------------------------------------------------------

    def _collectible_ids(self) -> list:
        ids = set()
        for kind in COLLECTIBLE_KINDS:
            ids |= set(self.catalog.ids_of_kind(kind))
        # Include any ids present in the save but missing from the catalog,
        # so something already-earned never silently disappears from view.
        for tier in range(1, TIER_COUNT):
            ids |= set(self.bundle.global_data["collectibles_by_tier"][tier])
        return sorted(ids, key=self.catalog.name_for)

    def _rebuild_table(self) -> None:
        self.table.setSortingEnabled(False)
        ids = self._collectible_ids()
        self.table.clearContents()
        self.table.setRowCount(len(ids))

        for row, item_id in enumerate(ids):
            self.table.setCellWidget(row, 0, icon_label(self.catalog, item_id, size=24))

            name_item = QTableWidgetItem(self.catalog.name_for(item_id))
            name_item.setData(Qt.ItemDataRole.UserRole, item_id)
            self.table.setItem(row, 1, name_item)

            self.table.setItem(row, 2, QTableWidgetItem(self.catalog.kind_for(item_id) or "?"))

            self._set_star_checkboxes(row, item_id)

            entry = self.bundle.global_data["collectibles_by_tier"][self.tier].get(item_id)
            rounds = entry["rounds_played"] if entry else 0.0
            best = entry["best_round"] if entry else 0.0
            self.table.setItem(row, 6, _numeric_item(rounds))
            self.table.setItem(row, 7, _numeric_item(best))

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self._apply_filter()

    def _set_star_checkboxes(self, row: int, item_id: str) -> None:
        level = collection_model.star_level(self.bundle, self.tier, item_id)

        discovered_box = QCheckBox()
        silver_box = QCheckBox()
        gold_box = QCheckBox()
        discovered_box.setChecked(level != "none")
        silver_box.setChecked(level in ("silver", "gold"))
        gold_box.setChecked(level == "gold")

        def on_toggle(_state=0):
            self._on_star_toggled(item_id, discovered_box, silver_box, gold_box)

        for box in (discovered_box, silver_box, gold_box):
            box.stateChanged.connect(on_toggle)

        self.table.setCellWidget(row, 3, _centered(discovered_box))
        self.table.setCellWidget(row, 4, _centered(silver_box))
        self.table.setCellWidget(row, 5, _centered(gold_box))

    def _on_star_toggled(self, item_id, discovered_box, silver_box, gold_box) -> None:
        if gold_box.isChecked():
            level = "gold"
        elif silver_box.isChecked():
            level = "silver"
        elif discovered_box.isChecked():
            level = "discovered"
        else:
            level = "none"

        collection_model.set_star(self.bundle, self.tier, item_id, level)

        for box in (discovered_box, silver_box, gold_box):
            box.blockSignals(True)
        discovered_box.setChecked(level != "none")
        silver_box.setChecked(level in ("silver", "gold"))
        gold_box.setChecked(level == "gold")
        for box in (discovered_box, silver_box, gold_box):
            box.blockSignals(False)

        self._refresh_tier_buttons()
        self._notify_changed()

    # -- bulk actions -------------------------------------------------------------------

    def _build_bulk_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Bulk (applies to currently visible rows):"))
        for label, level in (
            ("Discover all", "discovered"),
            ("Silver-star all", "silver"),
            ("Gold-star all", "gold"),
            ("Clear stars", "none"),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, lvl=level: self._bulk_set(lvl))
            row.addWidget(button)
        row.addStretch(1)
        return row

    def _bulk_set(self, level: str) -> None:
        visible_ids = [
            self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
            for row in range(self.table.rowCount())
            if not self.table.isRowHidden(row)
        ]
        collection_model.set_star_bulk(self.bundle, self.tier, visible_ids, level)
        self._rebuild_table()
        self._notify_changed()


def _numeric_item(value) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setData(Qt.ItemDataRole.DisplayRole, f"{float(value):g}")
    item.setData(Qt.ItemDataRole.EditRole, float(value))
    return item


def _centered(widget: QWidget) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(widget)
    return container
