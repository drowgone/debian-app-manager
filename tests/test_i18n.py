import pytest
from PySide6.QtWidgets import QApplication

from gui.i18n import set_language, tr
from gui.main_window import MainWindow


@pytest.fixture(scope="module")
def app() -> QApplication:
    qt_app = QApplication.instance()
    if qt_app is None:
        qt_app = QApplication([])
    return qt_app


def test_main_window_retranslates_ui_on_language_change(app: QApplication) -> None:
    set_language("uz")
    window = MainWindow()
    window.show()

    assert window.windowTitle() == tr("app.title")
    assert window._refresh_btn.text().strip() == "Yangilash"

    set_language("en")
    window._apply_language()

    assert window.windowTitle() == tr("app.title")
    assert window._refresh_btn.text().strip() == "Refresh"

    window.close()
