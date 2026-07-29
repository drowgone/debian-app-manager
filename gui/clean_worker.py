from PySide6.QtCore import QThread, Signal

from core.cleaner import (
    clean_apt_cache,
    clean_apt_autoremove,
    clean_apt_leftovers,
    clean_flatpak_unused,
    clean_journal_logs,
)

class CleanWorker(QThread):
    """
    Tizimni tozalash operatsiyalarini background'da bajaradi.
    Signals:
        progress: qaysi qadam bajarilayotgani haqida xabar beradi (str)
        finished_step: bitta qadam muvaffaqiyatli tugagani (bool, str)
        error_occurred: xatolik yuz berganda (str)
        finished_all: barcha belgilangan qadamlar tugaganda ()
    """
    progress = Signal(str)
    terminal_output = Signal(str)
    finished_step = Signal(bool, str)
    error_occurred = Signal(str)
    finished_all = Signal()

    def __init__(
        self,
        do_apt_cache: bool,
        do_apt_autoremove: bool,
        do_apt_leftovers: bool,
        do_flatpak: bool,
        do_journal: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.do_apt_cache = do_apt_cache
        self.do_apt_autoremove = do_apt_autoremove
        self.do_apt_leftovers = do_apt_leftovers
        self.do_flatpak = do_flatpak
        self.do_journal = do_journal

    def _log(self, text: str) -> None:
        self.terminal_output.emit(text)

    def run(self) -> None:
        if self.do_apt_cache:
            self.progress.emit("APT keshini tozalash boshlandi...")
            success, msg = clean_apt_cache(self._log)
            self.finished_step.emit(success, msg)
            if not success:
                self.error_occurred.emit(msg)

        if self.do_apt_autoremove:
            self.progress.emit("APT keraksiz paketlarini tozalash boshlandi...")
            success, msg = clean_apt_autoremove(self._log)
            self.finished_step.emit(success, msg)
            if not success:
                self.error_occurred.emit(msg)

        if self.do_apt_leftovers:
            self.progress.emit("O'chirilgan dastur qoldiqlarini tozalash boshlandi...")
            success, msg = clean_apt_leftovers(self._log)
            self.finished_step.emit(success, msg)
            if not success:
                self.error_occurred.emit(msg)

        if self.do_flatpak:
            self.progress.emit("Flatpak ishlatilmayotgan kutubxonalarini tozalash boshlandi...")
            success, msg = clean_flatpak_unused(self._log)
            self.finished_step.emit(success, msg)
            if not success:
                self.error_occurred.emit(msg)

        if self.do_journal:
            self.progress.emit("Tizim jurnallarini qisqartirish boshlandi...")
            success, msg = clean_journal_logs(self._log)
            self.finished_step.emit(success, msg)
            if not success:
                self.error_occurred.emit(msg)

        self.finished_all.emit()
