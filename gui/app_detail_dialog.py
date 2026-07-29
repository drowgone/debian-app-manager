"""
Dastur haqida batafsil ma'lumot ko'rsatuvchi dialog oynasi.
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QScrollArea,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon

from core.scanner import App
from core.desktop_parser import parse_desktop_entry
from gui.theme import colors, system_ui_font
from gui.widgets import SourceBadge, LaunchButton, UpdateButton, RemoveButton
from gui.animations import AnimatedProgressBar, TextSpinnerLabel


_SOURCE_LABELS = {
    "apt": "APT (Debian paket menejeri)",
    "snap": "Snap",
    "flatpak": "Flatpak",
    "appimage": "AppImage",
    "manual": "Qo'lda o'rnatilgan",
}


class _DetailRow(QWidget):
    """Kalit — qiymat qatori."""

    def __init__(self, label: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        c = colors()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        key = QLabel(label)
        key.setFont(system_ui_font(10, bold=True))
        key.setStyleSheet(f"color: {c['text_muted']};")
        key.setFixedWidth(130)
        key.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        layout.addWidget(key)

        val = QLabel(value or "—")
        val.setFont(system_ui_font(10))
        val.setStyleSheet(f"color: {c['text']};")
        val.setWordWrap(True)
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(val, stretch=1)


class AppDetailDialog(QDialog):
    """Tanlangan dastur haqida to'liq ma'lumot."""

    launch_requested = Signal()
    remove_requested = Signal()
    update_requested = Signal()

    def __init__(self, app: App, icon: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app = app
        c = colors()

        self.setWindowTitle(app.name)
        self.setMinimumWidth(480)
        self.setMaximumWidth(560)
        self.setStyleSheet(f"QDialog {{ background-color: {c['surface']}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(16)

        # ── Header: ikonka + nom ──
        header = QHBoxLayout()
        header.setSpacing(16)

        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(QSize(64, 64)))
        else:
            fallback = QIcon.fromTheme("application-x-executable")
            icon_label.setPixmap(fallback.pixmap(QSize(64, 64)))
        header.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        name_label = QLabel(app.name)
        name_label.setFont(system_ui_font(16, bold=True))
        name_label.setStyleSheet(f"color: {c['text']};")
        name_label.setWordWrap(True)
        title_col.addWidget(name_label)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)
        badge_row.addWidget(SourceBadge(app.source))
        if app.has_update:
            upd = QLabel(" Yangilanish mavjud ")
            upd.setFont(system_ui_font(9, bold=True))
            upd.setStyleSheet(
                f"background-color: {c['success_bg']}; color: {c['success_text']}; "
                f"border: 1px solid {c['success']}; border-radius: 4px; padding: 2px 8px;"
            )
            badge_row.addWidget(upd)
        badge_row.addStretch()
        title_col.addLayout(badge_row)

        header.addLayout(title_col, stretch=1)
        root.addLayout(header)

        # ── Ajratuvchi ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {c['border']};")
        root.addWidget(sep)

        # ── Ma'lumotlar ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        details = QWidget()
        grid = QVBoxLayout(details)
        grid.setContentsMargins(0, 0, 4, 0)
        grid.setSpacing(2)

        desktop_meta = self._desktop_meta(app)

        rows: list[tuple[str, str]] = [
            ("Manba", _SOURCE_LABELS.get(app.source, app.source)),
            ("Identifikator", app.identifier),
        ]
        if app.version:
            rows.append(("Versiya", app.version))
        if app.has_update and app.new_version:
            rows.append(("Yangi versiya", app.new_version))
        if app.size:
            rows.append(("Hajm", app.size))
        if app.date:
            rows.append(("Sana", app.date))
        if desktop_meta.get("Comment"):
            rows.append(("Tavsif", desktop_meta["Comment"]))
        if desktop_meta.get("Categories"):
            rows.append(("Kategoriya", desktop_meta["Categories"].replace(";", " · ")))
        if app.exec_line:
            rows.append(("Ishga tushirish", app.exec_line))
        if app.desktop_path:
            rows.append(("Desktop fayl", app.desktop_path))

        for label, value in rows:
            grid.addWidget(_DetailRow(label, value))

        grid.addStretch()
        scroll.setWidget(details)
        root.addWidget(scroll, stretch=1)

        # ── Jarayon ko'rsatkichi (o'chirish/yangilash) ──
        self._progress_container = QWidget()
        progress_layout = QVBoxLayout(self._progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self._status_label = TextSpinnerLabel("")
        self._status_label.setStyleSheet(
            f"color: {c['text']}; font-size: 12px; font-weight: 600;"
        )
        progress_layout.addWidget(self._status_label)

        self._progress_bar = AnimatedProgressBar("update")
        self._progress_bar.setFixedHeight(26)
        progress_layout.addWidget(self._progress_bar)

        self._progress_container.hide()
        root.addWidget(self._progress_container)

        # ── Tugmalar ──
        self._btn_row = QHBoxLayout()
        self._btn_row.setSpacing(8)

        can_launch = bool(app.exec_line or (app.desktop_path and os.path.isfile(app.desktop_path)))
        self._launch_btn = LaunchButton()
        self._launch_btn.setEnabled(can_launch)
        if not can_launch:
            self._launch_btn.setToolTip("Ishga tushirish buyrug'i topilmadi")
        self._launch_btn.clicked.connect(self.launch_requested.emit)
        self._btn_row.addWidget(self._launch_btn)

        self._update_btn: UpdateButton | None = None
        if app.has_update and app.source in ("apt", "snap", "flatpak"):
            self._update_btn = UpdateButton()
            self._update_btn.clicked.connect(self.update_requested.emit)
            self._btn_row.addWidget(self._update_btn)

        self._remove_btn = RemoveButton()
        self._remove_btn.clicked.connect(self.remove_requested.emit)
        self._btn_row.addWidget(self._remove_btn)

        self._btn_row.addStretch()

        self._close_btn = QPushButton("Yopish")
        self._close_btn.setObjectName("primaryBtn")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.accept)
        self._btn_row.addWidget(self._close_btn)

        root.addLayout(self._btn_row)

    @staticmethod
    def _desktop_meta(app: App) -> dict[str, str]:
        if not app.desktop_path or not os.path.isfile(app.desktop_path):
            return {}
        entry = parse_desktop_entry(app.desktop_path)
        return {
            k: entry[k]
            for k in ("Comment", "Categories", "GenericName", "StartupWMClass")
            if k in entry and entry[k]
        }

    def start_operation(self, operation: str, message: str) -> None:
        """O'chirish yoki yangilash jarayonini ko'rsatadi."""
        self._launch_btn.setEnabled(False)
        self._remove_btn.setEnabled(False)
        if self._update_btn:
            self._update_btn.setEnabled(False)
        self._close_btn.setEnabled(False)

        layout = self._progress_container.layout()
        old_bar = layout.itemAt(1).widget()
        new_bar = AnimatedProgressBar(operation)
        new_bar.setFixedHeight(26)
        layout.replaceWidget(old_bar, new_bar)
        old_bar.deleteLater()
        self._progress_bar = new_bar

        self._status_label.set_text(message)
        self._status_label.start()
        self._progress_container.show()

    def finish_operation(
        self, success: bool, message: str, *, auto_close: bool = False
    ) -> None:
        """Jarayon tugaganda natijani ko'rsatadi."""
        self._status_label.stop()
        c = colors()

        if success:
            self._progress_bar.set_success()
            self._status_label.setText(f"✓ {message}")
            self._status_label.setStyleSheet(
                f"color: {c['success_text']}; font-size: 12px; font-weight: 600;"
            )
        else:
            self._progress_bar.set_error()
            self._status_label.setText(f"✗ {message}")
            self._status_label.setStyleSheet(
                f"color: {c['danger']}; font-size: 12px; font-weight: 600;"
            )

        self._close_btn.setEnabled(True)
        if auto_close and success:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, self.accept)
        elif not success:
            self._launch_btn.setEnabled(
                bool(self._app.exec_line or (
                    self._app.desktop_path and os.path.isfile(self._app.desktop_path)
                ))
            )
            self._remove_btn.setEnabled(True)
            if self._update_btn:
                self._update_btn.setEnabled(True)
