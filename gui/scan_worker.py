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


import subprocess

class UpdateWorker(QThread):
    """
    Dasturni yangilash jarayonini real vaqtda yuklash foizlari va hajmlari bilan background'da bajaradi.
    Signals:
        finished: O'rnatish natijasi (success)
        progress_updated: real vaqt rejimida yuklash holati (masalan: "45% (12 MB / 25 MB)")
    """
    finished = Signal(bool)
    progress_updated = Signal(str)

    def __init__(
        self,
        update_func,
        identifier: str,
        source: str = "apt",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._update_func = update_func
        self._identifier = identifier
        self._source = source

    def run(self) -> None:
        if self._source == "apt":
            cmd = ["pkexec", "apt-get", "install", "--only-upgrade", "-y", self._identifier]
            self._run_and_parse_apt(cmd)
        elif self._source == "flatpak":
            cmd = ["flatpak", "update", "--noninteractive", "-y", self._identifier]
            self._run_and_parse_flatpak(cmd)
        else:
            try:
                success = self._update_func(self._identifier)
                self.finished.emit(success)
            except Exception:
                self.finished.emit(False)

    def _run_and_parse_apt(self, cmd: list[str]) -> None:
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    line_str = line.strip()
                    # APT yuklash jarayonini aniqlash: "Get:1 ... [12.5 MB/25.0 MB] 50%"
                    if "Get:" in line_str and "%" in line_str:
                        try:
                            parts = line_str.split()
                            percent = [p for p in parts if "%" in p][0]
                            sizes = [p for p in parts if "B" in p or "B/" in p]
                            size_str = f" ({sizes[-1]})" if sizes else ""
                            self.progress_updated.emit(f"{percent}{size_str}")
                        except Exception:
                            pass
            process.wait()
            self.finished.emit(process.returncode == 0)
        except Exception:
            self.finished.emit(False)

    def _run_and_parse_flatpak(self, cmd: list[str]) -> None:
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    line_str = line.strip()
                    # Flatpak progress formati: "Downloading ... 45%"
                    if "Downloading" in line_str or "Installing" in line_str:
                        parts = line_str.split()
                        percent_parts = [p for p in parts if "%" in p]
                        if percent_parts:
                            self.progress_updated.emit(percent_parts[0])
            process.wait()
            self.finished.emit(process.returncode == 0)
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
