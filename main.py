"""Debian Tashqi Dastur Boshqaruvchisi — ilova kirish nuqtasi."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.main_window import MainWindow
from gui.theme import configure_display_quality, system_ui_font


def main() -> None:
    """Ilovani ishga tushiradi."""
    configure_display_quality()

    app = QApplication(sys.argv)
    app.setApplicationName("Tashqi Dastur Boshqaruvchisi")
    app.setApplicationDisplayName("Tashqi Dastur Boshqaruvchisi")
    app.setDesktopFileName("debian-app-manager")
    app.setWindowIcon(
        QIcon.fromTheme("system-software-install", QIcon.fromTheme("applications-system"))
    )
    app.setFont(system_ui_font(10))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
