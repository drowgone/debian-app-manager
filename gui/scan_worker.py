"""
QThread asosidagi worker klass.
build_app_list() va get_autostart_entries() ni background'da
chaqiradi — UI thread qotib qolmasligi uchun.
"""

from PySide6.QtCore import QThread, Signal

from core.scanner import App, build_app_list
from core.autostart import AutostartEntry, get_autostart_entries, get_systemd_boot_info


class ScanWorker(QThread):
    """
    Dasturlar va avtoishga tushish yozuvlarini background'da skanerlaydi.

    Signals:
        apps_ready: Dasturlar ro'yxati tayyor bo'lganda chiqariladi.
        autostart_ready: Avtoishga tushish ro'yxati tayyor bo'lganda chiqariladi.
        error_occurred: Xatolik yuz berganda chiqariladi.
    """
    apps_ready = Signal(list)           # list[App]
    autostart_ready = Signal(list)      # list[AutostartEntry]
    boot_info_ready = Signal(tuple)     # (str, list[tuple[str, str]])
    error_occurred = Signal(str)        # Xatolik xabari

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def run(self) -> None:
        """Background thread'da skanerlashni bajaradi."""
        try:
            # Dasturlar ro'yxatini yig'ish
            apps = build_app_list()
            self.apps_ready.emit(apps)
        except Exception as e:
            self.error_occurred.emit(f"Dasturlarni skanerlashda xatolik: {e}")

        try:
            # Avtoishga tushish yozuvlarini o'qish
            autostart = get_autostart_entries()
            self.autostart_ready.emit(autostart)
            
            # Systemd ma'lumotlari
            boot_info = get_systemd_boot_info()
            self.boot_info_ready.emit(boot_info)
        except Exception as e:
            self.error_occurred.emit(f"Avtoishga tushish ro'yxatini o'qishda xatolik: {e}")


class RemoveWorker(QThread):
    """
    Dasturni o'chirish jarayonini background'da bajaradi.

    Signals:
        finished: O'chirish natijasi (success, message) bilan chiqariladi.
    """
    finished = Signal(bool, str)  # (success, message)

    def __init__(
        self,
        remove_func,
        identifier: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._remove_func = remove_func
        self._identifier = identifier

    def run(self) -> None:
        """Background thread'da o'chirish funksiyasini chaqiradi."""
        try:
            success, message = self._remove_func(self._identifier)
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, f"Kutilmagan xatolik: {e}")

from core.updater import get_apt_updates, get_snap_updates, get_flatpak_updates

class UpdateCheckWorker(QThread):
    """
    Background'da barcha manbalardan yangilanishlarni qidiradi.
    Signals:
        updates_ready: dict[str, str] (identifier -> yangi versiya)
    """
    updates_ready = Signal(dict)

    def run(self) -> None:
        updates = {}
        try:
            updates.update(get_apt_updates())
            updates.update(get_snap_updates())
            updates.update(get_flatpak_updates())
        except Exception:
            pass
        self.updates_ready.emit(updates)


class UpdateWorker(QThread):
    """
    Dasturni yangilash jarayonini background'da bajaradi.
    Signals:
        finished: O'rnatish natijasi (success)
    """
    finished = Signal(bool)

    def __init__(
        self,
        update_func,
        identifier: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._update_func = update_func
        self._identifier = identifier

    def run(self) -> None:
        try:
            success = self._update_func(self._identifier)
            self.finished.emit(success)
        except Exception:
            self.finished.emit(False)


class InstallWorker(QThread):
    """Fayldan (AppImage, deb, archive) o'rnatish uchun mo'ljallangan fon ishchisi."""
    progress = Signal(str)
    terminal_output = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        from core.installer import install_file
        try:
            success, message = install_file(
                self.file_path,
                log_callback=self.terminal_output.emit,
                progress_callback=self.progress.emit,
            )
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, f"Kutilmagan xatolik: {e}")
