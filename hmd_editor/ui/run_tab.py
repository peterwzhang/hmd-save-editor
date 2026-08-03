"""Run tab: editing the active run (save_data.json)."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..model import run as run_model
from .widgets import combo_box, count_spinbox, icon_label, money_spinbox

# (raw save value, display label). The game doesn't expose readable names
# for these anywhere - "custom" and "daily_challenge" are what the save
# format calls the Ensemble and Daily modes in its own UI.
GAME_MODES = (
    ("classic", "Classic mode"),
    ("custom", "Ensemble mode"),
    ("daily_challenge", "Daily mode"),
)


class RunTab(QWidget):
    def __init__(self, catalog, on_changed: Callable[[], None]):
        super().__init__()
        self.catalog = catalog
        self.on_changed = on_changed
        self.bundle = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        outer.addWidget(self.scroll)

        self.placeholder = QLabel(
            "Open a save folder with save_data.json to edit the current run."
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.placeholder)

    def set_bundle(self, bundle) -> None:
        self.bundle = bundle
        if bundle is None:
            self.scroll.setWidget(self.placeholder)
            return
        self._rebuild()

    def _notify_changed(self) -> None:
        self.on_changed()

    # -- building -------------------------------------------------------------

    def _rebuild(self) -> None:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        layout.addWidget(self._build_header_group())
        layout.addWidget(self._build_roster_group())
        layout.addWidget(self._build_items_group())
        layout.addWidget(self._build_consumables_group())
        layout.addWidget(self._build_food_group())
        layout.addStretch(1)

        self.scroll.setWidget(content)

    def _build_header_group(self) -> QGroupBox:
        run = self.bundle.run_data
        box = QGroupBox("Run")
        form = QFormLayout(box)

        cash_box = money_spinbox(run["cash"])
        cash_box.valueChanged.connect(lambda v: self._set_scalar(run_model.set_cash, v))
        form.addRow("Cash", cash_box)

        week_box = count_spinbox(int(run["week"]), maximum=9999)
        week_box.valueChanged.connect(lambda v: self._set_scalar(run_model.set_week, v))
        form.addRow("Week", week_box)

        rank_box = count_spinbox(int(run["rank"]), maximum=9999)
        rank_box.valueChanged.connect(lambda v: self._set_scalar(run_model.set_rank, v))
        form.addRow("Rank", rank_box)

        mode_combo = combo_box()
        for raw, label in GAME_MODES:
            mode_combo.addItem(label, raw)
        current_mode = run.get("game_mode", "")
        index = mode_combo.findData(current_mode)
        if index == -1:
            # Unknown mode (e.g. a future game update) - show it verbatim
            # rather than silently switching the save to a different one.
            mode_combo.addItem(current_mode, current_mode)
            index = mode_combo.count() - 1
        mode_combo.setCurrentIndex(index)
        mode_combo.currentIndexChanged.connect(
            lambda _i: self._set_scalar(run_model.set_game_mode, mode_combo.currentData())
        )
        form.addRow("Game mode", mode_combo)

        return box

    def _set_scalar(self, setter, value) -> None:
        setter(self.bundle, value)
        self._notify_changed()

    # -- roster -----------------------------------------------------------------

    def _build_roster_group(self) -> QGroupBox:
        box = QGroupBox("Roster")
        layout = QVBoxLayout(box)
        summary = run_model.roster_summary(self.bundle)

        for dude_type in self.bundle.run_data["roster_order"]:
            stats = summary.get(dude_type, {"count": 0, "avg_hp_percent": 1.0})
            layout.addWidget(self._build_dude_card(dude_type, stats))

        add_row = QHBoxLayout()
        new_dude_combo = combo_box()
        for dude_id in sorted(self.catalog.ids_of_kind("dude"), key=self.catalog.name_for):
            new_dude_combo.addItem(self.catalog.name_for(dude_id), dude_id)
        add_button = QPushButton("Add to roster")
        add_button.clicked.connect(lambda: self._add_dude(new_dude_combo.currentData(), 1))
        add_row.addWidget(new_dude_combo, 1)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

        return box

    def _build_dude_card(self, dude_type: str, stats: dict) -> QWidget:
        card = QWidget()
        row = QHBoxLayout(card)
        row.setContentsMargins(4, 4, 4, 4)

        row.addWidget(icon_label(self.catalog, dude_type))
        name_label = QLabel(self.catalog.name_for(dude_type))
        name_label.setMinimumWidth(140)
        row.addWidget(name_label)

        row.addWidget(QLabel(f"x{stats['count']}"))
        row.addWidget(QLabel(f"avg HP {stats['avg_hp_percent'] * 100:.0f}%"))

        heal_button = QPushButton("Heal all")
        heal_button.clicked.connect(lambda: self._heal_type(dude_type))
        row.addWidget(heal_button)

        add1_button = QPushButton("+1")
        add1_button.clicked.connect(lambda: self._add_dude(dude_type, 1))
        row.addWidget(add1_button)

        add5_button = QPushButton("+5")
        add5_button.clicked.connect(lambda: self._add_dude(dude_type, 5))
        row.addWidget(add5_button)

        row.addWidget(self._build_trinket_slot(dude_type))
        row.addStretch(1)
        return card

    def _build_trinket_slot(self, dude_type: str) -> QWidget:
        equipped_id = None
        for tr_id, dtype in self.bundle.run_data["trinkets_equipped"].items():
            if dtype == dude_type:
                equipped_id = tr_id
                break

        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)

        if equipped_id:
            row.addWidget(icon_label(self.catalog, equipped_id, size=24))
            row.addWidget(QLabel(self.catalog.name_for(equipped_id)))
            remove_button = QPushButton("Unequip")
            remove_button.clicked.connect(lambda: self._unequip_trinket(equipped_id))
            row.addWidget(remove_button)
        else:
            combo = combo_box()
            for tr_id in sorted(self.catalog.ids_of_kind("trinket"), key=self.catalog.name_for):
                combo.addItem(self.catalog.name_for(tr_id), tr_id)
            equip_button = QPushButton("Equip trinket")
            equip_button.clicked.connect(
                lambda: self._equip_trinket(combo.currentData(), dude_type)
            )
            row.addWidget(combo)
            row.addWidget(equip_button)

        return widget

    def _heal_type(self, dude_type: str) -> None:
        run_model.heal_type(self.bundle, dude_type)
        self._rebuild()
        self._notify_changed()

    def _add_dude(self, dude_type, count: int) -> None:
        if not dude_type:
            return
        run_model.add_dude(self.bundle, dude_type, count)
        self._rebuild()
        self._notify_changed()

    def _equip_trinket(self, trinket_id, dude_type: str) -> None:
        if not trinket_id:
            return
        run_model.equip_trinket(self.bundle, trinket_id, dude_type)
        self._rebuild()
        self._notify_changed()

    def _unequip_trinket(self, trinket_id: str) -> None:
        run_model.unequip_trinket(self.bundle, trinket_id)
        self._rebuild()
        self._notify_changed()

    # -- relics ---------------------------------------------------------------------

    def _build_items_group(self) -> QGroupBox:
        # Trinkets are not relics and never appear in relics_owned/relic_order
        # in real save data - they're managed entirely through each roster
        # card's equip/unequip slot above, not here.
        box = QGroupBox("Relics")
        layout = QVBoxLayout(box)

        relics = list(self.bundle.run_data["relic_order"])
        layout.addWidget(QLabel(f"Relics owned: {len(relics)}"))
        layout.addWidget(self._build_owned_item_list(relics))
        layout.addLayout(self._build_add_item_row("relic", relics))

        return box

    def _build_owned_item_list(self, item_ids) -> QListWidget:
        list_widget = QListWidget()
        list_widget.setMaximumHeight(160)
        for item_id in sorted(item_ids, key=self.catalog.name_for):
            entry = QListWidgetItem(self.catalog.name_for(item_id))
            entry.setData(Qt.ItemDataRole.UserRole, item_id)
            list_widget.addItem(entry)
        list_widget.itemDoubleClicked.connect(
            lambda item: self._remove_relic(item.data(Qt.ItemDataRole.UserRole))
        )
        list_widget.setToolTip("Double-click an item to remove it")
        return list_widget

    def _build_add_item_row(self, kind: str, already_owned) -> QHBoxLayout:
        row = QHBoxLayout()
        combo = combo_box()
        owned_set = set(already_owned)
        for item_id in sorted(self.catalog.ids_of_kind(kind), key=self.catalog.name_for):
            if item_id not in owned_set:
                combo.addItem(self.catalog.name_for(item_id), item_id)
        add_button = QPushButton(f"Add {kind}")
        add_button.clicked.connect(lambda: self._add_relic(combo.currentData()))
        row.addWidget(combo, 1)
        row.addWidget(add_button)
        return row

    def _add_relic(self, item_id) -> None:
        if not item_id:
            return
        run_model.add_relic(self.bundle, item_id)
        self._rebuild()
        self._notify_changed()

    def _remove_relic(self, item_id) -> None:
        run_model.remove_relic(self.bundle, item_id)
        self._rebuild()
        self._notify_changed()

    # -- consumables ----------------------------------------------------------------

    def _build_consumables_group(self) -> QGroupBox:
        box = QGroupBox("Consumables")
        form = QFormLayout(box)

        for cons_id, count in sorted(self.bundle.run_data["consumables_owned"].items()):
            spin = count_spinbox(int(count), maximum=999)
            spin.valueChanged.connect(lambda v, cid=cons_id: self._set_consumable(cid, v))
            form.addRow(self.catalog.name_for(cons_id), spin)

        add_row = QHBoxLayout()
        combo = combo_box()
        owned = set(self.bundle.run_data["consumables_owned"])
        for cons_id in sorted(self.catalog.ids_of_kind("consumable"), key=self.catalog.name_for):
            if cons_id not in owned:
                combo.addItem(self.catalog.name_for(cons_id), cons_id)
        add_button = QPushButton("Add consumable")
        add_button.clicked.connect(lambda: self._add_consumable(combo.currentData()))
        add_row.addWidget(combo, 1)
        add_row.addWidget(add_button)
        form.addRow(add_row)

        return box

    def _set_consumable(self, cons_id: str, value) -> None:
        run_model.set_consumable(self.bundle, cons_id, value)
        self._notify_changed()

    def _add_consumable(self, cons_id) -> None:
        if not cons_id:
            return
        run_model.set_consumable(self.bundle, cons_id, 1)
        self._rebuild()
        self._notify_changed()

    # -- food -------------------------------------------------------------------------

    def _build_food_group(self) -> QGroupBox:
        box = QGroupBox("Food")
        layout = QVBoxLayout(box)

        for food_id, food in sorted(self.bundle.run_data["food"].items()):
            row = QHBoxLayout()
            row.addWidget(icon_label(self.catalog, food["type"], size=24))
            row.addWidget(QLabel(self.catalog.name_for(food["type"])))
            row.addWidget(QLabel(f"for {self.catalog.name_for(food['dude_type'])}"))
            row.addWidget(QLabel(f"({self.catalog.name_for(food['secondary_stat'])})"))
            remove_button = QPushButton("Remove")
            remove_button.clicked.connect(
                lambda checked=False, fid=food_id: self._remove_food(fid)
            )
            row.addWidget(remove_button)
            row.addStretch(1)
            layout.addLayout(row)

        if not self.bundle.run_data["roster_order"]:
            layout.addWidget(QLabel("Add a Dude to the roster before adding food."))
            return box

        add_row = QHBoxLayout()
        food_type_combo = combo_box()
        for food_id in sorted(self.catalog.ids_of_kind("food"), key=self.catalog.name_for):
            food_type_combo.addItem(self.catalog.name_for(food_id), food_id)
        stat_combo = combo_box()
        for stat_id in sorted(self.catalog.ids_of_kind("stat"), key=self.catalog.name_for):
            stat_combo.addItem(self.catalog.name_for(stat_id), stat_id)
        dude_combo = combo_box()
        for dude_type in self.bundle.run_data["roster_order"]:
            dude_combo.addItem(self.catalog.name_for(dude_type), dude_type)
        add_button = QPushButton("Add food")
        add_button.clicked.connect(
            lambda: self._add_food(
                food_type_combo.currentData(), stat_combo.currentData(), dude_combo.currentData()
            )
        )
        add_row.addWidget(food_type_combo)
        add_row.addWidget(stat_combo)
        add_row.addWidget(dude_combo)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

        return box

    def _add_food(self, food_type, stat, dude_type) -> None:
        if not (food_type and stat and dude_type):
            return
        run_model.add_food(self.bundle, food_type, stat, dude_type)
        self._rebuild()
        self._notify_changed()

    def _remove_food(self, food_id: str) -> None:
        run_model.remove_food(self.bundle, food_id)
        self._rebuild()
        self._notify_changed()
