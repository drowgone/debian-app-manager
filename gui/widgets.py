"""
Qayta ishlatiladigan GUI komponentlar (widgetlar).
Manba badge'lari, stillar va yordamchi widgetlar.
"""

from PySide6.QtWidgets import (
    QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

from gui.theme import colors, system_ui_font, build_stylesheet


class AppInfoWidget(QWidget):
    """Dastur nomi, ikonkasi va tafsilotlarini ko'rsatuvchi widget."""

    def __init__(
        self,
        name: str,
        icon: QIcon,
        version: str = "",
        size: str = "",
        date: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        c = colors()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(36, 36)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(QSize(36, 36)))
        main_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setFont(system_ui_font(12, bold=True))
        name_label.setStyleSheet(f"color: {c['text']};")
        text_layout.addWidget(name_label)

        details_parts: list[str] = []
        if version:
            details_parts.append(f"v{version}")
        if size:
            details_parts.append(size)
        if date:
            details_parts.append(date)

        if details_parts:
            details_label = QLabel(" · ".join(details_parts))
            details_label.setFont(system_ui_font(9))
            details_label.setStyleSheet(f"color: {c['text_muted']};")
            text_layout.addWidget(details_label)

        main_layout.addLayout(text_layout, 1)


# ── Manba ranglari (Linux distributiv ranglari) ──────────────────────────────
SOURCE_COLORS = {
    "apt":      {"bg": "#a80030", "text": "#ffffff", "label": "APT"},
    "snap":     {"bg": "#e95420", "text": "#ffffff", "label": "Snap"},
    "flatpak":  {"bg": "#4a86cf", "text": "#ffffff", "label": "Flatpak"},
    "appimage": {"bg": "#555555", "text": "#ffffff", "label": "AppImage"},
    "manual":   {"bg": "#77767b", "text": "#ffffff", "label": "Qo'lda"},
}


class SourceBadge(QLabel):
    """Manba turini ko'rsatuvchi rangli badge widget."""

    def __init__(self, source: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        src = SOURCE_COLORS.get(source, SOURCE_COLORS["manual"])
        self.setText(f" {src['label']} ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(system_ui_font(9, bold=True))
        self.setStyleSheet(
            f"background-color: {src['bg']};"
            f"color: {src['text']};"
            "border-radius: 4px;"
            "padding: 2px 8px;"
        )
        self.setFixedHeight(22)


class RemoveButton(QPushButton):
    """O'chirish tugmasi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("O'chirish", parent)
        self.setFixedSize(90, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        c = colors()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['danger']};
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: {c['danger_hover']};
            }}
            QPushButton:pressed {{
                background-color: {c['debian']};
            }}
        """)


class AutostartRemoveButton(QPushButton):
    """Avtoishga tushish yozuvini o'chirish tugmasi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Olib tashlash", parent)
        self.setFixedSize(110, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        c = colors()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['danger']};
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: {c['danger_hover']};
            }}
            QPushButton:pressed {{
                background-color: {c['debian']};
            }}
        """)


class StatusLabel(QLabel):
    """Holat ko'rsatuvchi yorliq."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(system_ui_font(10))

    def show_success(self, message: str) -> None:
        c = colors()
        self.setText(f"✓ {message}")
        self.setStyleSheet(f"color: {c['success']}; font-weight: 600; padding: 4px;")

    def show_error(self, message: str) -> None:
        c = colors()
        self.setText(f"✗ {message}")
        self.setStyleSheet(f"color: {c['danger']}; font-weight: 600; padding: 4px;")

    def clear_status(self) -> None:
        self.setText("")
        self.setStyleSheet("")


# Umumiy stylesheet — theme modulidan
APP_STYLESHEET = build_stylesheet()


class UpdateBadge(QLabel):
    """Yangilanish mavjudligini ko'rsatuvchi badge."""

    def __init__(self, new_version: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        c = colors()
        self.setText(" Yangilanish ")
        if new_version:
            self.setToolTip(f"Yangi versiya:\n{new_version}")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(system_ui_font(9, bold=True))
        self.setStyleSheet(
            f"background-color: {c['success_bg']};"
            f"color: {c['success_text']};"
            f"border: 1px solid {c['success']};"
            "border-radius: 4px;"
            "padding: 2px 8px;"
        )
        self.setFixedHeight(22)


class LaunchButton(QPushButton):
    """Dasturni ishga tushirish tugmasi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Ishga tushirish", parent)
        self.setFixedSize(120, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        c = colors()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent']};
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {c['debian']};
            }}
            QPushButton:disabled {{
                background-color: {c['border']};
                color: {c['text_muted']};
            }}
        """)


class UpdateButton(QPushButton):
    """Yangilash tugmasi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Yangilash", parent)
        self.setFixedSize(90, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        c = colors()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['success']};
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: #26a269;
            }}
            QPushButton:pressed {{
                background-color: #1a7f37;
            }}
        """)
