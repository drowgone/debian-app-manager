"""
Linux desktop estetikasi — Adwaita/GNOME rang palitasi va tizim mavzusi.

Tizimning yorug'/qorong'u rejimini avtomatik aniqlaydi va
GNOME, KDE va boshqa Linux desktop muhitlariga mos ko'rinish beradi.
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication, QPalette, QFont, QFontDatabase
from PySide6.QtCore import Qt


# ── Rang palitralari ───────────────────────────────────────────────────────

LIGHT = {
    "window_bg":      "#f6f5f4",
    "surface":        "#ffffff",
    "surface_alt":    "#f3f2f1",
    "border":         "#cdc7c2",
    "border_light":   "#e0deda",
    "text":           "#2e3436",
    "text_secondary": "#5e5c64",
    "text_muted":     "#77767b",
    "accent":         "#3584e4",       # Adwaita ko'k
    "accent_hover":   "#1c71d8",
    "accent_pressed": "#1a5fb4",
    "accent_subtle":  "#c0d6f0",
    "success":        "#2ec27e",
    "success_bg":     "#d4edda",
    "success_text":   "#1a7f37",
    "warning":        "#e5a50a",
    "warning_bg":     "#fef3cd",
    "danger":         "#c01c28",
    "danger_hover":   "#a51d2d",
    "danger_bg":      "#fce8e6",
    "debian":         "#a80030",
    "selection":      "#c0d6f0",
    "header_bg":      "#ebeae8",
    "terminal_bg":    "#241f31",
    "terminal_fg":    "#33d17a",
    "terminal_border":"#3d3846",
    "overlay_bg":     "rgba(246, 245, 244, 0.92)",
    "shadow":         "rgba(0, 0, 0, 0.08)",
}

DARK = {
    "window_bg":      "#242424",
    "surface":        "#303030",
    "surface_alt":    "#383838",
    "border":         "#4d4d4d",
    "border_light":   "#404040",
    "text":           "#ffffff",
    "text_secondary": "#c0bfbc",
    "text_muted":     "#9a9996",
    "accent":         "#3584e4",
    "accent_hover":   "#62a0ea",
    "accent_pressed": "#1c71d8",
    "accent_subtle":  "#1c3f6e",
    "success":        "#2ec27e",
    "success_bg":     "#1a3d2e",
    "success_text":   "#57e389",
    "warning":        "#f5c211",
    "warning_bg":     "#3d3500",
    "danger":         "#ed333b",
    "danger_hover":   "#ff6b6b",
    "danger_bg":      "#3d1f1f",
    "debian":         "#d70751",
    "selection":      "#1c3f6e",
    "header_bg":      "#1e1e1e",
    "terminal_bg":    "#0d1117",
    "terminal_fg":    "#3fb950",
    "terminal_border":"#30363d",
    "overlay_bg":     "rgba(36, 36, 36, 0.92)",
    "shadow":         "rgba(0, 0, 0, 0.35)",
}


def configure_display_quality() -> None:
    """High-DPI ekranlarda matn va ikonlarni tiniq chizishga tayyorlaydi."""
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def is_dark_mode() -> bool:
    """Tizim yorug'/qorong'u rejimini aniqlaydi."""
    app = QApplication.instance()
    if app is None:
        return False
    palette = app.palette()
    window = palette.color(QPalette.ColorRole.Window)
    return window.lightness() < 128


def colors() -> dict[str, str]:
    """Joriy mavzu ranglarini qaytaradi."""
    return DARK if is_dark_mode() else LIGHT


def system_ui_font(size: int = 10, bold: bool = False) -> QFont:
    """Tizim UI shriftini qaytaradi (Cantarell, Ubuntu, Noto Sans)."""
    preferred = ("Cantarell", "Ubuntu", "Noto Sans", "DejaVu Sans", "Sans Serif")
    families = QFontDatabase.families()
    for name in preferred:
        if name in families:
            font = QFont(name, size)
            font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
            if bold:
                font.setWeight(QFont.Weight.Bold)
            return font
    font = QFont()
    font.setPointSize(size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    if bold:
        font.setWeight(QFont.Weight.Bold)
    return font


def monospace_font(size: int = 11) -> QFont:
    """Terminal uchun monospace shrift."""
    preferred = ("JetBrains Mono", "Fira Code", "Ubuntu Mono", "DejaVu Sans Mono", "Monospace")
    families = QFontDatabase.families()
    for name in preferred:
        if name in families:
            font = QFont(name, size)
            font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
            return font
    font = QFont("Monospace", size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    return font


# ── Tizim ikonkalari ─────────────────────────────────────────────────────────

TAB_ICONS = {
    "apps":      "view-grid-symbolic",
    "autostart": "system-run-symbolic",
    "cleaner":   "edit-clear-all-symbolic",
    "errors":    "dialog-warning-symbolic",
}

ACTION_ICONS = {
    "refresh":   "view-refresh-symbolic",
    "search":    "system-search-symbolic",
    "install":   "package-x-generic-symbolic",
    "remove":    "user-trash-symbolic",
    "update":    "software-update-available-symbolic",
    "settings":  "emblem-system-symbolic",
}


def build_stylesheet() -> str:
    """To'liq ilova stylesheet'ini yaratadi."""
    c = colors()
    return f"""
QMainWindow {{
    background-color: {c['window_bg']};
}}

/* ── Header panel ── */
QFrame#headerBar {{
    background-color: {c['header_bg']};
    border-bottom: 1px solid {c['border']};
    border-radius: 0px;
}}

QLabel#appTitle {{
    color: {c['text']};
    font-size: 15px;
    font-weight: bold;
    padding: 0px;
}}

QLabel#appSubtitle {{
    color: {c['text_muted']};
    font-size: 11px;
    padding: 0px;
}}

/* ── Tablar ── */
QTabWidget::pane {{
    border: none;
    background-color: transparent;
    top: 0px;
}}

QTabBar {{
    background-color: transparent;
    border-bottom: 1px solid {c['border']};
}}

QTabBar::tab {{
    background-color: transparent;
    color: {c['text_secondary']};
    padding: 10px 18px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    font-weight: 600;
    min-height: 22px;
}}

QTabBar::tab:selected {{
    color: {c['accent']};
    border-bottom: 2px solid {c['accent']};
    background-color: transparent;
}}

QTabBar::tab:hover:!selected {{
    color: {c['text']};
    background-color: {c['surface_alt']};
    border-radius: 6px 6px 0px 0px;
}}

/* ── Kartochka va panel ── */
QFrame#card {{
    background-color: {c['surface']};
    border: 1px solid {c['border']};
    border-radius: 8px;
}}

QFrame#toolbar {{
    background-color: {c['surface']};
    border: 1px solid {c['border']};
    border-radius: 8px;
}}

QLabel#sectionTitle {{
    color: {c['text']};
    font-size: 13px;
    font-weight: bold;
}}

QLabel#sectionSubtitle {{
    color: {c['text_secondary']};
    font-size: 11px;
}}

QLabel#countBadge {{
    color: {c['text_secondary']};
}}

/* ── Jadval ── */
QTableWidget {{
    background-color: {c['surface']};
    alternate-background-color: {c['surface_alt']};
    border: none;
    gridline-color: {c['border_light']};
    font-size: 13px;
    selection-background-color: {c['selection']};
    selection-color: {c['text']};
    outline: none;
}}

QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {c['border_light']};
}}

QTableWidget::item:selected {{
    background-color: {c['selection']};
}}

QHeaderView::section {{
    background-color: {c['surface_alt']};
    color: {c['text_secondary']};
    border: none;
    border-bottom: 1px solid {c['border']};
    border-right: 1px solid {c['border_light']};
    padding: 8px 10px;
    font-weight: 600;
    font-size: 11px;
}}

QHeaderView::section:last {{
    border-right: none;
}}

/* ── Kiritish maydonlari ── */
QLineEdit {{
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 7px 12px;
    font-size: 13px;
    background-color: {c['surface']};
    color: {c['text']};
    selection-background-color: {c['accent']};
}}

QLineEdit:focus {{
    border: 2px solid {c['accent']};
    padding: 6px 11px;
}}

QComboBox {{
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 7px 12px;
    font-size: 13px;
    background-color: {c['surface']};
    color: {c['text']};
    min-width: 120px;
}}

QComboBox:focus {{
    border: 2px solid {c['accent']};
    padding: 6px 11px;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {c['surface']};
    color: {c['text']};
    border: 1px solid {c['border']};
    selection-background-color: {c['selection']};
}}

/* ── Tugmalar ── */
QPushButton {{
    background-color: {c['surface_alt']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 600;
    min-height: 18px;
}}

QPushButton:hover {{
    background-color: {c['border_light']};
    border-color: {c['text_muted']};
}}

QPushButton:pressed {{
    background-color: {c['border']};
}}

QPushButton:disabled {{
    color: {c['text_muted']};
    background-color: {c['surface_alt']};
}}

QPushButton#refreshBtn {{
    background-color: {c['accent']};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}}

QPushButton#refreshBtn:hover {{
    background-color: {c['accent_hover']};
}}

QPushButton#refreshBtn:pressed {{
    background-color: {c['accent_pressed']};
}}

QPushButton#primaryBtn {{
    background-color: {c['accent']};
    color: #ffffff;
    border: none;
}}

QPushButton#primaryBtn:hover {{
    background-color: {c['accent_hover']};
}}

QPushButton#dangerBtn {{
    background-color: {c['danger']};
    color: #ffffff;
    border: none;
}}

QPushButton#dangerBtn:hover {{
    background-color: {c['danger_hover']};
}}

QPushButton#dangerBtn:disabled {{
    background-color: {c['text_muted']};
    color: {c['surface']};
}}

/* ── Checkbox ── */
QCheckBox {{
    spacing: 10px;
    font-size: 13px;
    color: {c['text']};
    padding: 4px 0px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {c['border']};
    background-color: {c['surface']};
}}

QCheckBox::indicator:checked {{
    background-color: {c['accent']};
    border-color: {c['accent']};
    image: none;
}}

QCheckBox::indicator:unchecked:hover {{
    border-color: {c['accent']};
}}

/* ── Info banner ── */
QFrame#infoBanner {{
    background-color: {c['accent_subtle']};
    border: 1px solid {c['accent']};
    border-radius: 6px;
    padding: 0px;
}}

QLabel#infoBannerText {{
    color: {c['text']};
    font-size: 13px;
    padding: 10px 12px;
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {c['header_bg']};
    color: {c['text_secondary']};
    border-top: 1px solid {c['border']};
    font-size: 12px;
    padding: 2px 8px;
}}

/* ── Ro'yxat ── */
QListWidget {{
    background-color: {c['surface']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}

QListWidget::item {{
    border-bottom: 1px solid {c['border_light']};
    padding: 8px 10px;
    color: {c['danger']};
    border-radius: 4px;
}}

QListWidget::item:hover {{
    background-color: {c['danger_bg']};
}}

/* ── Terminal ── */
QTextEdit#terminal {{
    background-color: {c['terminal_bg']};
    color: {c['terminal_fg']};
    font-family: "JetBrains Mono", "Ubuntu Mono", "DejaVu Sans Mono", monospace;
    font-size: 12px;
    padding: 10px;
    border: 1px solid {c['terminal_border']};
    border-radius: 6px;
    selection-background-color: {c['accent_subtle']};
}}

/* ── Progress bar ── */
QProgressBar {{
    border: 1px solid {c['border']};
    border-radius: 4px;
    background-color: {c['surface_alt']};
    text-align: center;
    font-size: 11px;
    color: {c['text']};
    min-height: 18px;
}}

QProgressBar::chunk {{
    border-radius: 3px;
    background-color: {c['accent']};
}}

/* ── Dialog ── */
QDialog {{
    background-color: {c['surface']};
}}

QMessageBox {{
    background-color: {c['surface']};
}}

QScrollBar:vertical {{
    background: {c['surface_alt']};
    width: 10px;
    border-radius: 5px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {c['border']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {c['text_muted']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {c['surface_alt']};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {c['border']};
    border-radius: 5px;
    min-width: 30px;
}}
"""


def terminal_stylesheet() -> str:
    """Terminal QTextEdit uchun alohida stil."""
    c = colors()
    return (
        f"QTextEdit {{ background-color: {c['terminal_bg']}; "
        f"color: {c['terminal_fg']}; "
        f'font-family: "JetBrains Mono", "Ubuntu Mono", "DejaVu Sans Mono", monospace; '
        f"font-size: 12px; padding: 10px; "
        f"border: 1px solid {c['terminal_border']}; border-radius: 6px; }}"
    )


def info_banner_stylesheet() -> str:
    """Info banner frame stili."""
    c = colors()
    return (
        f"QFrame#infoBanner {{ background-color: {c['accent_subtle']}; "
        f"border: 1px solid {c['accent']}; border-radius: 6px; }}"
    )
