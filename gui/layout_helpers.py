"""Tablar va bo'limlar uchun qayta ishlatiladigan layout komponentlari."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from gui.theme import colors, system_ui_font, info_banner_stylesheet


class CardFrame(QFrame):
    """Kontentni ajratib ko'rsatuvchi kartochka."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._layout = layout

    def add_widget(self, widget: QWidget, *, stretch: int = 0) -> None:
        self._layout.addWidget(widget, stretch)


class SectionHeader(QWidget):
    """Bo'lim sarlavhasi va qisqa tavsif."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        icon_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        c = colors()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        if icon_name:
            icon_label = QLabel()
            icon = QIcon.fromTheme(icon_name)
            icon_label.setPixmap(icon.pixmap(20, 20))
            icon_label.setFixedSize(20, 20)
            layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        title_label = QLabel(title)
        self._title_label = title_label
        title_label.setObjectName("sectionTitle")
        title_label.setFont(system_ui_font(13, bold=True))
        title_label.setStyleSheet(f"color: {c['text']};")
        text_col.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            self._sub_label = sub_label
            sub_label.setObjectName("sectionSubtitle")
            sub_label.setWordWrap(True)
            sub_label.setFont(system_ui_font(11))
            sub_label.setStyleSheet(f"color: {c['text_secondary']};")
            text_col.addWidget(sub_label)
        else:
            self._sub_label = None

        layout.addLayout(text_col, stretch=1)

    def set_text(self, title: str, subtitle: str = "") -> None:
        self._title_label.setText(title)
        if self._sub_label is not None:
            self._sub_label.setText(subtitle)


class InfoBanner(QFrame):
    """Ma'lumot banneri."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("infoBanner")
        self.setStyleSheet(info_banner_stylesheet())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(QIcon.fromTheme("dialog-information-symbolic").pixmap(18, 18))
        icon_label.setFixedSize(18, 18)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        label = QLabel(text)
        label.setObjectName("infoBannerText")
        label.setWordWrap(True)
        label.setFont(system_ui_font(12))
        layout.addWidget(label, stretch=1)


class TabToolbar(QFrame):
    """Tab ichidagi qidiruv/filtr/tugmalar paneli."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbar")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(10)

    def add_widget(
        self,
        widget: QWidget,
        *,
        stretch: int = 0,
        alignment: Qt.AlignmentFlag | None = None,
    ) -> None:
        if alignment is not None:
            self._layout.addWidget(widget, stretch, alignment)
        else:
            self._layout.addWidget(widget, stretch)

    def add_stretch(self) -> None:
        self._layout.addStretch()


class CountBadge(QLabel):
    """Soni ko'rsatuvchi badge."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        c = colors()
        self.setObjectName("countBadge")
        self.setFont(system_ui_font(11, bold=True))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"background-color: {c['surface_alt']};"
            f"color: {c['text_secondary']};"
            f"border: 1px solid {c['border']};"
            "border-radius: 12px;"
            "padding: 4px 12px;"
        )
        self.setMinimumHeight(28)


class EmptyStateWidget(QWidget):
    """Bo'sh ro'yxat holati."""

    def __init__(
        self,
        icon_name: str,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        c = colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 48, 24, 48)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        icon = QIcon.fromTheme(icon_name)
        icon_label.setPixmap(icon.pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setFont(system_ui_font(14, bold=True))
        title_label.setStyleSheet(f"color: {c['text_secondary']};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setFont(system_ui_font(11))
            sub_label.setStyleSheet(f"color: {c['text_muted']};")
            sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub_label.setWordWrap(True)
            layout.addWidget(sub_label)


def padded_tab_layout(widget: QWidget) -> QVBoxLayout:
    """Tab ichidagi standart padding bilan layout."""
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    return layout


def table_card(table: QWidget) -> CardFrame:
    """Jadvalni kartochka ichiga joylashtiradi."""
    card = CardFrame()
    card._layout.setContentsMargins(1, 1, 1, 1)
    card.add_widget(table, stretch=1)
    return card
