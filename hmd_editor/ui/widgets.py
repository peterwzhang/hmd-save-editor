"""Small reusable UI pieces shared across tabs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QSpinBox, QWidget

ICON_SIZE = 32


def icon_pixmap(catalog, item_id: str, size: int = ICON_SIZE):
    pixmap = catalog.icon_for(item_id)
    if pixmap is None:
        return None
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def icon_label(catalog, item_id: str, size: int = ICON_SIZE) -> QLabel:
    label = QLabel()
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    pixmap = icon_pixmap(catalog, item_id, size)
    if pixmap is not None:
        label.setPixmap(pixmap)
    else:
        label.setText("?")
        label.setObjectName("missingIcon")
    return label


def icon_name_widget(catalog, item_id: str, size: int = ICON_SIZE) -> QWidget:
    """A small icon + display name row, for lists and forms."""
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(icon_label(catalog, item_id, size))
    layout.addWidget(QLabel(catalog.name_for(item_id)))
    layout.addStretch(1)
    return widget


def money_spinbox(value: float = 0.0) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(0.0, 100_000_000.0)
    box.setDecimals(2)
    box.setSingleStep(10.0)
    box.setValue(value)
    return box


def fraction_spinbox(value: float = 1.0) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(0.0, 1.0)
    box.setSingleStep(0.05)
    box.setDecimals(3)
    box.setValue(value)
    return box


def count_spinbox(value: int = 0, maximum: int = 9999) -> QSpinBox:
    box = QSpinBox()
    box.setRange(0, maximum)
    box.setValue(value)
    return box
