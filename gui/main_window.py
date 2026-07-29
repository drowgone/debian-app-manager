"""
Asosiy dastur oynasi — QMainWindow + QTabWidget.

Ikkita tab:
  1) "Dasturlar" — o'rnatilgan dasturlar ro'yxati (qidiruv va filtr bilan)
  2) "Avtoishga tushish" — autorun yozuvlari (yoqish/o'chirish/olib tashlash)
"""

import os
from functools import partial

from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox,
    QPushButton, QHeaderView, QMessageBox, QCheckBox,
    QStatusBar, QLabel, QAbstractItemView, QProgressBar, QSizePolicy,
    QListWidget, QTextEdit, QDialog, QFrame,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QIcon, QColor

from gui.theme import (
    colors, system_ui_font, build_stylesheet,
    terminal_stylesheet, info_banner_stylesheet,
    TAB_ICONS, ACTION_ICONS,
)

from core.scanner import App
from core.launcher import launch_app
from core.updater import update_apt_package, update_snap_package, update_flatpak_app
from core.autostart import (
    AutostartEntry, toggle_autostart, remove_autostart_entry,
)
from core.remover import (
    remove_apt_package, remove_snap_package,
    remove_flatpak_app, remove_manual_app, get_manual_app_binary,
)
from gui.scan_worker import ScanWorker, RemoveWorker, UpdateCheckWorker, UpdateWorker, InstallWorker
from gui.clean_worker import CleanWorker
from gui.widgets import (
    SourceBadge, RemoveButton, AutostartRemoveButton, UpdateBadge, UpdateButton,
    AppInfoWidget,
)
from gui.animations import (
    OperationOverlay, AnimatedProgressBar, OperationBadge,
    SuccessFlash, RotatingIconButton, TextSpinnerLabel, PulseAnimator,
    OverlayContainer,
)
from gui.app_detail_dialog import AppDetailDialog
from gui.layout_helpers import CardFrame, CountBadge, InfoBanner, SectionHeader, TabToolbar


class MainWindow(QMainWindow):
    """Dasturning asosiy oynasi."""

    _TAB_APPS = 0
    _TAB_AUTOSTART = 1
    _TAB_CLEANER = 2
    _TAB_ERRORS = 3

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Tashqi Dastur Boshqaruvchisi")
        self.setMinimumSize(850, 600)
        self.resize(1000, 700)
        self.setWindowIcon(
            QIcon.fromTheme("system-software-install", QIcon.fromTheme("applications-system"))
        )

        # Ma'lumotlar
        self._apps: list[App] = []
        self._autostart_entries: list[AutostartEntry] = []
        self._errors: list[str] = []
        self._scan_worker: ScanWorker | None = None
        self._update_check_worker: UpdateCheckWorker | None = None
        self._update_worker: UpdateWorker | None = None
        self._updating_apps = set()  # app identifiers currently updating
        self._removing_apps = set()  # app identifiers currently removing
        self._remove_worker: RemoveWorker | None = None
        self._clean_worker: CleanWorker | None = None
        self._install_worker: InstallWorker | None = None
        self._install_dialog: QDialog | None = None
        self._animate_update_check = True  # faqat dastur ishga tushganda

        # UI
        self._setup_ui()
        self.setStyleSheet(build_stylesheet())
        self.setFont(system_ui_font(10))

        # Animatsiya yordamchilari
        self._refresh_animator = RotatingIconButton(
            self._refresh_btn, "Yangilash", "Skanerlanmoqda..."
        )
        self._status_pulse: PulseAnimator | None = None

        # Boshlang'ich skanerlash
        QTimer.singleShot(100, self._start_scan)

    # ── UI qurish ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Asosiy UI komponentlarini yaratadi."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # GNOME-style header bar
        header = self._create_header()
        layout.addWidget(header)

        # Tab widget
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 14, 16, 10)
        content_layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        content_layout.addWidget(self._tabs)
        layout.addWidget(content, stretch=1)

        # Tab 1: Dasturlar
        apps_tab = self._create_apps_tab()
        self._tabs.addTab(
            apps_tab,
            QIcon.fromTheme(TAB_ICONS["apps"]),
            "Dasturlar",
        )

        # Tab 2: Avtoishga tushish
        autostart_tab = self._create_autostart_tab()
        self._tabs.addTab(
            autostart_tab,
            QIcon.fromTheme(TAB_ICONS["autostart"]),
            "Avtoishga tushish",
        )

        # Tab 3: Tozalash
        cleaner_tab = self._create_cleaner_tab()
        self._tabs.addTab(
            cleaner_tab,
            QIcon.fromTheme(TAB_ICONS["cleaner"]),
            "Tozalash",
        )

        # Tab 4: Xatoliklar
        errors_tab = self._create_errors_tab()
        self._tabs.addTab(
            errors_tab,
            QIcon.fromTheme(TAB_ICONS["errors"]),
            "Xatoliklar",
        )

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Tayyor")

    def _create_header(self) -> QFrame:
        """GNOME-style header bar — sarlavha va yangilash tugmasi."""
        header = QFrame()
        header.setObjectName("headerBar")
        header.setFixedHeight(56)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Ilova ikonkasi
        app_icon = QLabel()
        icon = QIcon.fromTheme(
            "system-software-install",
            QIcon.fromTheme("applications-system"),
        )
        app_icon.setPixmap(icon.pixmap(QSize(32, 32)))
        app_icon.setFixedSize(32, 32)
        layout.addWidget(app_icon)

        # Sarlavha ustuni
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Tashqi Dastur Boshqaruvchisi")
        title.setObjectName("appTitle")
        title.setFont(system_ui_font(15, bold=True))
        title_col.addWidget(title)

        subtitle = QLabel("APT · Snap · Flatpak · AppImage")
        subtitle.setObjectName("appSubtitle")
        subtitle.setFont(system_ui_font(10))
        title_col.addWidget(subtitle)

        layout.addLayout(title_col)
        layout.addStretch()

        self._refresh_btn = QPushButton("  Yangilash")
        self._refresh_btn.setObjectName("refreshBtn")
        self._refresh_btn.setIcon(QIcon.fromTheme(ACTION_ICONS["refresh"]))
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.clicked.connect(self._start_scan)
        layout.addWidget(self._refresh_btn)

        return header

    def _create_apps_tab(self) -> QWidget:
        """Dasturlar tab'ini yaratadi."""
        c = colors()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(SectionHeader(
            "O'rnatilgan dasturlar",
            "Dasturlarni qidiring, manba bo'yicha saralang yoki fayldan o'rnating.",
            "application-x-executable-symbolic",
        ))

        # Qidiruv va filtr satri
        toolbar = TabToolbar()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Dastur nomini qidirish...")
        self._search_input.addAction(
            QIcon.fromTheme(ACTION_ICONS["search"]), QLineEdit.ActionPosition.LeadingPosition
        )
        self._search_input.textChanged.connect(self._filter_apps)
        toolbar.add_widget(self._search_input, stretch=1)

        self._source_filter = QComboBox()
        self._source_filter.addItems([
            "Barchasi", "APT", "Snap", "Flatpak", "AppImage", "Qo'lda",
        ])
        self._source_filter.currentTextChanged.connect(self._filter_apps)
        toolbar.add_widget(self._source_filter)

        self._app_count_label = CountBadge("")
        toolbar.add_widget(self._app_count_label)

        self._install_file_btn = QPushButton("  Fayldan o'rnatish")
        self._install_file_btn.setObjectName("primaryBtn")
        self._install_file_btn.setIcon(QIcon.fromTheme(ACTION_ICONS["install"]))
        self._install_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._install_file_btn.clicked.connect(self._on_install_file)
        toolbar.add_widget(self._install_file_btn)

        layout.addWidget(toolbar)

        # Jadval
        self._apps_table = QTableWidget()
        self._apps_table.setColumnCount(3)
        self._apps_table.setHorizontalHeaderLabels(["Nomi", "Manba", "Amal"])
        self._apps_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._apps_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self._apps_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed
        )
        self._apps_table.setColumnWidth(1, 110)
        self._apps_table.setColumnWidth(2, 110)
        self._apps_table.verticalHeader().setVisible(False)
        self._apps_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._apps_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._apps_table.setAlternatingRowColors(True)
        self._apps_table.setIconSize(QSize(32, 32))
        self._apps_table.setShowGrid(False)
        self._apps_table.cellClicked.connect(self._on_app_cell_clicked)

        # Jadval + skanerlash overlay konteyneri
        self._scan_overlay = OperationOverlay()
        self._success_flash = SuccessFlash()
        self._table_container = OverlayContainer(
            self._apps_table, self._scan_overlay, self._success_flash
        )

        table_card = CardFrame()
        table_card._layout.setContentsMargins(1, 1, 1, 1)
        table_card.add_widget(self._table_container, stretch=1)
        layout.addWidget(table_card, stretch=1)
        return widget

    def _create_autostart_tab(self) -> QWidget:
        """Avtoishga tushish tab'ini yaratadi."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(SectionHeader(
            "Avtoishga tushish",
            "Kompyuter yoqilganda ishga tushadigan dasturlarni boshqaring.",
            "system-run-symbolic",
        ))

        self._boot_info_label = QLabel(
            "Tizim yuklanganda avtomatik ishga tushadigan dasturlar. "
            "Tizim darajasidagi yozuvlar override orqali boshqariladi."
        )
        self._boot_info_label.setObjectName("infoBannerText")
        self._boot_info_label.setWordWrap(True)
        boot_info = InfoBanner("")
        boot_info_layout = boot_info.layout()
        old_label = boot_info_layout.itemAt(1).widget()
        boot_info_layout.replaceWidget(old_label, self._boot_info_label)
        old_label.deleteLater()
        layout.addWidget(boot_info)

        # Jadval
        self._autostart_table = QTableWidget()
        self._autostart_table.setColumnCount(3)
        self._autostart_table.setHorizontalHeaderLabels(["Nomi va Yuklanish", "Holati", "Amal"])
        self._autostart_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._autostart_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self._autostart_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed
        )
        self._autostart_table.setColumnWidth(1, 130)
        self._autostart_table.setColumnWidth(2, 130)
        self._autostart_table.verticalHeader().setVisible(False)
        self._autostart_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._autostart_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._autostart_table.setAlternatingRowColors(True)
        self._autostart_table.setIconSize(QSize(32, 32))
        self._autostart_table.setShowGrid(False)

        self._autostart_card = CardFrame()
        self._autostart_card._layout.setContentsMargins(1, 1, 1, 1)
        self._autostart_card.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self._autostart_card.add_widget(self._autostart_table)
        layout.addWidget(self._autostart_card)
        layout.addStretch(1)
        return widget

    def _create_cleaner_tab(self) -> QWidget:
        """Tozalash tab'ini yaratadi."""
        c = colors()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(SectionHeader(
            "Tizimni tozalash",
            "Keraksiz keshlar va eskirgan fayllarni xavfsiz tarzda tanlab tozalang.",
            "edit-clear-all-symbolic",
        ))

        layout.addWidget(InfoBanner(
            "Tizimda vaqt o'tishi bilan yig'ilib qoladigan keshlar, "
            "o'chirilgan dastur qoldiqlari va eskirgan loglarni tozalash orqali bo'sh joy ochishingiz mumkin."
        ))

        options_card = CardFrame()
        options_layout = options_card._layout
        options_layout.setContentsMargins(16, 14, 16, 14)
        options_layout.setSpacing(6)
        options_title = QLabel("Tozalash parametrlari")
        options_title.setObjectName("sectionTitle")
        options_layout.addWidget(options_title)

        self._chk_apt_cache = QCheckBox("APT keshini tozalash (apt-get clean)")
        self._chk_apt_cache.setChecked(True)
        options_layout.addWidget(self._chk_apt_cache)

        self._chk_apt_autoremove = QCheckBox("Keraksiz bog'liqliklarni o'chirish (autoremove)")
        self._chk_apt_autoremove.setChecked(True)
        options_layout.addWidget(self._chk_apt_autoremove)

        self._chk_apt_leftovers = QCheckBox("O'chirilgan dasturlar konfiguratsiya qoldiqlarini tozalash (dpkg --purge)")
        self._chk_apt_leftovers.setChecked(True)
        options_layout.addWidget(self._chk_apt_leftovers)

        self._chk_flatpak = QCheckBox("Ishlatilmayotgan Flatpak kutubxonalarini tozalash")
        self._chk_flatpak.setChecked(True)
        options_layout.addWidget(self._chk_flatpak)

        self._chk_journal = QCheckBox("Tizim loglarini qisqartirish (oxirgi 3 kunlikni qoldirish)")
        self._chk_journal.setChecked(True)
        options_layout.addWidget(self._chk_journal)

        layout.addWidget(options_card)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self._start_clean_btn = QPushButton("  Tozalashni boshlash")
        self._start_clean_btn.setObjectName("dangerBtn")
        self._start_clean_btn.setIcon(QIcon.fromTheme(ACTION_ICONS["remove"]))
        self._start_clean_btn.setMinimumHeight(40)
        self._start_clean_btn.setMinimumWidth(200)
        self._start_clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_clean_btn.clicked.connect(self._start_cleaning)
        btn_layout.addWidget(self._start_clean_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self._clean_terminal = QTextEdit()
        self._clean_terminal.setObjectName("terminal")
        self._clean_terminal.setReadOnly(True)
        self._clean_terminal.setStyleSheet(terminal_stylesheet())
        self._clean_terminal.setMinimumHeight(170)
        terminal_card = CardFrame()
        terminal_card._layout.setContentsMargins(1, 1, 1, 1)
        terminal_card.add_widget(self._clean_terminal, stretch=1)
        layout.addWidget(terminal_card, stretch=1)

        return widget

    def _create_errors_tab(self) -> QWidget:
        """Xatoliklar tab'ini yaratadi."""
        c = colors()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(SectionHeader(
            "Xatoliklar va ogohlantirishlar",
            "Dastur ishlashi davomida yuz bergan muammalar ro'yxati.",
            "dialog-warning-symbolic",
        ))
        header_layout.addStretch()

        self._clear_errors_btn = QPushButton("  Tozalash")
        self._clear_errors_btn.setIcon(QIcon.fromTheme("edit-clear"))
        self._clear_errors_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_errors_btn.clicked.connect(self._clear_errors)
        header_layout.addWidget(self._clear_errors_btn)

        layout.addLayout(header_layout)

        self._errors_list = QListWidget()
        self._errors_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        list_card = CardFrame()
        list_card._layout.setContentsMargins(1, 1, 1, 1)
        list_card.add_widget(self._errors_list, stretch=1)
        layout.addWidget(list_card, stretch=1)

        return widget

    # ── Skanerlash ─────────────────────────────────────────────────────────

    def _start_scan(self) -> None:
        """Background'da skanerlashni boshlaydi."""
        if self._scan_worker and self._scan_worker.isRunning():
            return

        self._refresh_animator.start()
        self._scan_overlay.show_operation(
            "Dasturlar skanerlanmoqda...",
            "APT, Snap, Flatpak va AppImage qidirilmoqda",
        )
        self._status_bar.showMessage("Dasturlar skanerlanmoqda...")
        self._pulse_status_bar(True)

        self._scan_worker = ScanWorker(self)
        self._scan_worker.apps_ready.connect(self._on_apps_ready)
        self._scan_worker.autostart_ready.connect(self._on_autostart_ready)
        self._scan_worker.boot_info_ready.connect(self._on_boot_info_ready)
        self._scan_worker.error_occurred.connect(self._on_scan_error)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_apps_ready(self, apps: list[App]) -> None:
        """Dasturlar ro'yxati tayyor bo'lganda chaqiriladi."""
        self._apps = apps
        self._populate_apps_table()

    def _on_autostart_ready(self, entries: list) -> None:
        """Avtoishga tushish ro'yxati tayyor bo'lganda chaqiriladi."""
        self._autostart_entries = entries
        self._populate_autostart_table()
        
    def _on_boot_info_ready(self, boot_info: tuple[str, list[tuple[str, str]]]) -> None:
        """Tizim yuklanish vaqti tayyor bo'lganda chaqiriladi."""
        overall, top = boot_info
        
        lines = [
            f"<b>Tizim ishga tushish vaqti:</b> {overall or 'Aniqlanmadi'}",
            "<br/><i>Tizimni ko'p band qilgan xizmatlar (Top 5):</i>"
        ]
        if top:
            for srv, time_str in top:
                lines.append(f" • <b>{srv}</b> — {time_str}")
        else:
            lines.append(" • Ma'lumot topilmadi.")
            
        self._boot_info_label.setText("<br/>".join(lines))

    def _on_scan_error(self, message: str) -> None:
        """Skanerlashda xatolik bo'lganda chaqiriladi."""
        self._status_bar.showMessage(f"⚠️  {message}", 5000)
        self._add_error(f"Skanerlash xatoligi: {message}")

    def _start_update_check(self, *, animated: bool = False) -> None:
        if animated:
            self._status_bar.showMessage("Yangilanishlar tekshirilmoqda...")
            self._scan_overlay.show_operation(
                "Yangilanishlar tekshirilmoqda...",
                "APT, Snap va Flatpak repozitoriyalari tekshirilmoqda",
                color=colors()["success"],
            )
        self._update_check_worker = UpdateCheckWorker(self)
        self._update_check_worker.updates_ready.connect(
            lambda updates: self._on_updates_ready(updates, animated=animated)
        )
        self._update_check_worker.start()

    def _on_updates_ready(self, updates: dict, *, animated: bool = False) -> None:
        count = 0
        for app in self._apps:
            if app.identifier in updates:
                app.has_update = True
                app.new_version = updates[app.identifier]
                count += 1
        self._pulse_status_bar(False)
        self._populate_apps_table()

        if animated:
            self._scan_overlay.hide_operation()
            if count > 0:
                self._status_bar.showMessage(f"🟢 {count} ta dastur uchun yangilanish mavjud", 5000)
            else:
                self._status_bar.showMessage("✓ Barcha dasturlar yangilangan", 5000)
            self._success_flash.flash()
            self._animate_update_check = False
        elif count > 0:
            self._status_bar.showMessage(f"{count} ta dastur uchun yangilanish mavjud", 5000)

    def _on_scan_finished(self) -> None:
        """Skanerlash tugaganda chaqiriladi."""
        self._refresh_animator.stop()
        total = len(self._apps)
        animated = self._animate_update_check

        if animated:
            self._start_update_check(animated=True)
        else:
            self._scan_overlay.hide_operation()
            self._pulse_status_bar(False)
            self._status_bar.showMessage(f"✓ {total} ta dastur topildi", 5000)
            self._start_update_check(animated=False)

    def _load_icon(self, icon_name: str) -> QIcon:
        """Belgilangan nom yoki yo'l bo'yicha ikonkani yuklaydi."""
        if not icon_name:
            return QIcon.fromTheme("application-x-executable")
        if os.path.isabs(icon_name) and os.path.isfile(icon_name):
            return QIcon(icon_name)
        return QIcon.fromTheme(icon_name, QIcon.fromTheme("application-x-executable"))

    # ── Dasturlar jadvali ──────────────────────────────────────────────────

    def _populate_apps_table(self) -> None:
        """Dasturlar jadvalini to'ldiradi (filtr bilan)."""
        search_text = self._search_input.text().lower().strip()
        source_filter = self._source_filter.currentText()

        # Filtr xaritasi
        source_map = {
            "APT": "apt",
            "Snap": "snap",
            "Flatpak": "flatpak",
            "AppImage": "appimage",
            "Qo'lda": "manual",
        }

        filtered: list[App] = []
        for app in self._apps:
            # Qidiruv filtri
            if search_text and search_text not in app.name.lower():
                continue
            # Manba filtri
            if source_filter != "Barchasi":
                expected_source = source_map.get(source_filter, "")
                if app.source != expected_source:
                    continue
            filtered.append(app)

        self._apps_table.setRowCount(len(filtered))

        for row, app in enumerate(filtered):
            # Nomi + tafsilotlar (ikonka, versiya, hajm, sana)
            icon = self._load_icon(app.icon)
            info_widget = AppInfoWidget(
                name=app.name,
                icon=icon,
                version=app.version,
                size=app.size,
                date=app.date,
            )
            # Yangilanish bor bo'lsa tooltip qo'shish
            if app.has_update and app.new_version:
                info_widget.setToolTip(
                    f"Yangilanish mavjud!\n"
                    f"Yangi versiya: {app.new_version}\n"
                    f"Hozirgi versiya: {app.version or 'nomalum'}"
                )
            # UserRole uchun hidden item (matn yozilmaydi, chunki info_widget ustma-ust tushib qoladi)
            name_item = QTableWidgetItem("")
            name_item.setData(Qt.ItemDataRole.UserRole, app)
            self._apps_table.setItem(row, 0, name_item)
            self._apps_table.setCellWidget(row, 0, info_widget)

            # Manba badge
            badge_widgets = [SourceBadge(app.source)]
            if app.has_update:
                badge_widgets.append(UpdateBadge(app.new_version))
            self._apps_table.setCellWidget(row, 1, self._row_widget(badge_widgets))

            # Amallar
            action_widgets = []

            if app.identifier in self._removing_apps:
                action_widgets.append(OperationBadge("remove"))
                self._apps_table.setCellWidget(
                    row, 2, self._center_widget(action_widgets[0])
                )
                self._apps_table.setRowHeight(row, 60)
                red_brush = QColor(colors()["danger_bg"])
                name_item.setBackground(red_brush)
                info_widget.setStyleSheet("background-color: #fce8e6;")
                dummy1 = QTableWidgetItem()
                dummy1.setBackground(red_brush)
                self._apps_table.setItem(row, 1, dummy1)
                dummy2 = QTableWidgetItem()
                dummy2.setBackground(red_brush)
                self._apps_table.setItem(row, 2, dummy2)
                continue
            elif app.identifier in self._updating_apps:
                prog = AnimatedProgressBar("update")
                prog.setFixedSize(110, 22)
                action_widgets.append(prog)
            else:
                if app.has_update:
                    upd_btn = UpdateButton()
                    upd_btn.clicked.connect(partial(self._on_update_app, app))
                    action_widgets.append(upd_btn)
                
                btn = RemoveButton()
                btn.clicked.connect(partial(self._on_remove_app, app))
                action_widgets.append(btn)
                
            if app.has_update:
                self._apps_table.setCellWidget(row, 2, self._col_widget(action_widgets))
                self._apps_table.setRowHeight(row, 80)
                green_brush = QColor(colors()["success_bg"])
                name_item.setBackground(green_brush)
                info_widget.setStyleSheet("background-color: #f0fdf4;")
                # Qolgan ustunlar uchun dummy item qo'shib fonini bo'yash
                dummy1 = QTableWidgetItem()
                dummy1.setBackground(green_brush)
                self._apps_table.setItem(row, 1, dummy1)
                dummy2 = QTableWidgetItem()
                dummy2.setBackground(green_brush)
                self._apps_table.setItem(row, 2, dummy2)
            else:
                self._apps_table.setCellWidget(row, 2, self._row_widget(action_widgets))
                self._apps_table.setRowHeight(row, 60)

        # Dasturlar soni
        total = len(self._apps)
        shown = len(filtered)
        if shown == total:
            self._app_count_label.setText(f"{total} ta dastur")
        else:
            self._app_count_label.setText(f"{shown} / {total}")

    def _filter_apps(self) -> None:
        """Qidiruv yoki filtr o'zgarganda jadvalini qayta to'ldiradi."""
        self._populate_apps_table()

    def _on_app_cell_clicked(self, row: int, column: int) -> None:
        """Dastur qatoriga bosilganda batafsil ma'lumot dialogini ochadi."""
        if column == 2:
            return
        item = self._apps_table.item(row, 0)
        if item is None:
            return
        app = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(app, App):
            return
        icon = self._load_icon(app.icon)
        dialog = AppDetailDialog(app, icon, self)
        dialog.launch_requested.connect(lambda: self._launch_app(app))
        dialog.remove_requested.connect(lambda: self._on_remove_app(app, dialog))
        dialog.update_requested.connect(lambda: self._on_update_app(app, dialog))
        dialog.exec()

    # ── Avtoishga tushish jadvali ──────────────────────────────────────────

    def _populate_autostart_table(self) -> None:
        """Avtoishga tushish jadvalini to'ldiradi."""
        entries = self._autostart_entries
        self._autostart_table.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            # Nomi va Yuklanish
            name_text = entry.name
            if entry.is_system:
                name_text += "  [tizim]"
            icon = self._load_icon(entry.icon)
            
            # AppInfoWidget orqali yuklanish vaqtini ko'rsatamiz
            info_widget = AppInfoWidget(
                name=name_text,
                icon=icon,
                version=entry.boot_time if entry.boot_time else "Yuklanish vaqti: Aniqlanmadi",
                size="",
                date="",
            )
            
            name_item = QTableWidgetItem("")
            name_item.setToolTip(
                f"Fayl: {entry.desktop_path}\n"
                f"{'Tizim darajasi' if entry.is_system else 'Foydalanuvchi darajasi'}"
            )
            name_item.setData(Qt.ItemDataRole.UserRole, entry)
            self._autostart_table.setItem(row, 0, name_item)
            self._autostart_table.setCellWidget(row, 0, info_widget)

            # Holati (checkbox)
            checkbox = QCheckBox("Yoqilgan" if entry.enabled else "O'chirilgan")
            checkbox.setChecked(entry.enabled)
            checkbox.setStyleSheet("padding-left: 12px;")
            checkbox.toggled.connect(partial(self._on_toggle_autostart, entry))
            self._autostart_table.setCellWidget(
                row, 1, self._center_widget(checkbox)
            )

            # O'chirish tugmasi
            btn = AutostartRemoveButton()
            btn.clicked.connect(partial(self._on_remove_autostart, entry))
            self._autostart_table.setCellWidget(row, 2, self._center_widget(btn))

            self._autostart_table.setRowHeight(row, 60)

        # Bo'sh jadval butun tabni egallab olmasin. 7 tadan ko'p yozuvda
        # jadval o'zida scroll qiladi, kam yozuvlarda esa kontentga mos qoladi.
        visible_rows = min(max(len(entries), 1), 7)
        header_height = self._autostart_table.horizontalHeader().height() or 38
        table_height = header_height + visible_rows * 60 + 2
        self._autostart_table.setFixedHeight(table_height)
        self._autostart_card.setFixedHeight(table_height + 2)

    # ── Amallar ────────────────────────────────────────────────────────────


    def _launch_app(self, app: App) -> None:
        """Dasturni ishga tushiradi."""
        success, message = launch_app(app)
        if success:
            self._status_bar.showMessage(f"▶ «{app.name}» ishga tushirildi", 3000)
        else:
            QMessageBox.warning(
                self,
                "Ishga tushirish",
                f"«{app.name}» ishga tushirilmadi:\n\n{message}",
            )

    def _on_update_app(self, app: App, source_dialog: AppDetailDialog | None = None) -> None:
        if app.identifier in self._updating_apps:
            return
        
        # update funksiyasini topish
        update_func = None
        if app.source == "apt":
            update_func = update_apt_package
        elif app.source == "snap":
            update_func = update_snap_package
        elif app.source == "flatpak":
            update_func = update_flatpak_app
        else:
            self._status_bar.showMessage(f"⚠️ {app.source} uchun yangilash qo'llab-quvvatlanmaydi", 5000)
            return

        self._updating_apps.add(app.identifier)
        self._populate_apps_table()
        self._status_bar.showMessage(f"⬆️ «{app.name}» yangilanmoqda...")
        self._pulse_status_bar(True)

        if source_dialog:
            source_dialog.start_operation("update", f"«{app.name}» yangilanmoqda...")

        self._update_worker = UpdateWorker(update_func, app.identifier, self)
        self._update_worker.finished.connect(
            partial(self._on_update_finished, app, source_dialog)
        )
        self._update_worker.start()

    def _on_update_finished(
        self, app: App, source_dialog: AppDetailDialog | None, success: bool
    ) -> None:
        self._updating_apps.discard(app.identifier)
        self._pulse_status_bar(False)
        if success:
            app.has_update = False
            app.new_version = ""
            msg = f"«{app.name}» muvaffaqiyatli yangilandi"
            self._status_bar.showMessage(f"✓ {msg}", 5000)
            self._success_flash.flash()
        else:
            msg = f"«{app.name}» yangilanishida xatolik yuz berdi"
            self._status_bar.showMessage(f"✗ {msg}", 5000)
            self._add_error(f"Yangilash xatoligi: «{app.name}» ({app.source}) yangilanmadi.")
        if source_dialog:
            source_dialog.finish_operation(success, msg)
        self._populate_apps_table()

    def _on_remove_app(self, app: App, source_dialog: AppDetailDialog | None = None) -> None:
        """Dasturni o'chirish tugmasi bosilganda."""
        # Tasdiqlash dialogi
        reply = QMessageBox.question(
            self,
            "Dasturni o'chirish",
            f"«{app.name}» dasturini butunlay o'chirmoqchimisiz?\n\n"
            f"Manba: {app.source.upper()}\n"
            f"Identifikator: {app.identifier}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Qo'lda o'rnatilgan dastur uchun binary haqida so'rash
        if app.source == "manual":
            binary = get_manual_app_binary(app.desktop_path)
            if binary:
                bin_reply = QMessageBox.question(
                    self,
                    "Binary faylni ham o'chirish",
                    f"Binary fayl ham topildi:\n{binary}\n\n"
                    "Uni ham o'chirmoqchimisiz?\n"
                    "(Faqat .desktop fayl o'chirilsa, dastur havolasiz qoladi)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if bin_reply == QMessageBox.StandardButton.Yes:
                    self._remove_binary_file(binary)

        # Manba bo'yicha o'chirish funksiyasini aniqlash
        if app.source == "appimage":
            from core.appimage_manager import remove_appimage, AppImageApp
            appimage_app = AppImageApp(
                name=app.name, file_path=app.identifier,
                desktop_path=app.desktop_path,
                icon_path=app.icon if app.icon and os.path.isfile(app.icon) else None,
                size_bytes=0,
            )

            def _remove_wrapper(identifier):
                return remove_appimage(appimage_app)

            self._removing_apps.add(app.identifier)
            self._populate_apps_table()
            self._status_bar.showMessage(f"🗑️ «{app.name}» o'chirilmoqda...")
            self._pulse_status_bar(True)
            if source_dialog:
                source_dialog.start_operation("remove", f"«{app.name}» o'chirilmoqda...")
            self._remove_worker = RemoveWorker(_remove_wrapper, app.identifier, self)
            self._remove_worker.finished.connect(
                partial(self._on_remove_finished, app, source_dialog)
            )
            self._remove_worker.start()
            return

        remove_funcs = {
            "apt": remove_apt_package,
            "snap": remove_snap_package,
            "flatpak": remove_flatpak_app,
            "manual": remove_manual_app,
        }
        func = remove_funcs.get(app.source)
        if not func:
            self._status_bar.showMessage(f"⚠️  Noma'lum manba: {app.source}", 5000)
            return

        # Background thread'da o'chirish
        self._removing_apps.add(app.identifier)
        self._populate_apps_table()
        self._status_bar.showMessage(f"🗑️ «{app.name}» o'chirilmoqda...")
        self._pulse_status_bar(True)
        if source_dialog:
            source_dialog.start_operation("remove", f"«{app.name}» o'chirilmoqda...")
        self._remove_worker = RemoveWorker(func, app.identifier, self)
        self._remove_worker.finished.connect(
            partial(self._on_remove_finished, app, source_dialog)
        )
        self._remove_worker.start()

    def _on_remove_finished(
        self,
        app: App,
        source_dialog: AppDetailDialog | None,
        success: bool,
        message: str,
    ) -> None:
        """O'chirish tugaganda chaqiriladi."""
        self._removing_apps.discard(app.identifier)
        self._pulse_status_bar(False)
        if success:
            self._status_bar.showMessage(f"✓  {message}", 5000)
            self._success_flash.flash()
            if source_dialog:
                source_dialog.finish_operation(True, message, auto_close=True)
            QTimer.singleShot(500, self._start_scan)
        else:
            self._populate_apps_table()
            self._status_bar.showMessage(f"⚠️  {message}", 8000)
            self._add_error(f"O'chirish xatoligi: «{app.name}» — {message}")
            if source_dialog:
                source_dialog.finish_operation(False, message)
            else:
                QMessageBox.warning(
                    self,
                    "O'chirishda xatolik",
                    f"«{app.name}» o'chirilmadi:\n\n{message}",
                )

    def _remove_binary_file(self, binary_path: str) -> None:
        """Binary faylni o'chiradi (qo'lda o'rnatilgan dasturlar uchun)."""
        import os
        try:
            if os.path.isfile(binary_path):
                os.remove(binary_path)
                self._status_bar.showMessage(
                    f"✓  Binary fayl o'chirildi: {binary_path}", 5000
                )
        except PermissionError:
            import subprocess
            try:
                result = subprocess.run(
                    ["pkexec", "rm", binary_path],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    self._status_bar.showMessage(
                        f"✓  Binary fayl o'chirildi: {binary_path}", 5000
                    )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        except OSError:
            pass

    # ── Fayldan o'rnatish ─────────────────────────────────────────────────

    def _on_install_file(self) -> None:
        """AppImage, deb yoki arxiv faylni tanlash va o'rnatish."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "O'rnatish uchun faylni tanlang",
            os.path.expanduser("~/Downloads"),
            "O'rnatish fayllari (*.AppImage *.appimage *.deb *.tar.xz *.tar.gz *.zip);;"
            "Barcha fayllar (*)",
        )
        if not file_path:
            return

        self._show_install_dialog(os.path.basename(file_path))
        self._install_file_btn.setEnabled(False)

        self._install_worker = InstallWorker(file_path, self)
        self._install_worker.progress.connect(self._on_install_progress)
        self._install_worker.terminal_output.connect(self._on_install_terminal_output)
        self._install_worker.finished.connect(self._on_install_finished)
        self._install_worker.start()

    def _show_install_dialog(self, filename: str) -> None:
        """O'rnatish jarayonini ko'rsatadigan dialog oynasini ochadi."""
        if self._install_dialog:
            self._install_dialog.close()

        dialog = QDialog(self)
        dialog.setWindowTitle("Fayldan o'rnatish")
        dialog.setMinimumSize(560, 360)
        dialog.setModal(False)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)

        title = QLabel(filename)
        title.setFont(system_ui_font(13, bold=True))
        title.setStyleSheet(f"color: {colors()['text']};")
        layout.addWidget(title)

        self._install_status_label = TextSpinnerLabel("O'rnatish boshlanmoqda...")
        self._install_status_label.setStyleSheet(
            f"color: {colors()['success']}; font-size: 13px; font-weight: 600;"
        )
        self._install_status_label.start()
        layout.addWidget(self._install_status_label)

        self._install_progress_bar = AnimatedProgressBar("install")
        self._install_progress_bar.setFixedHeight(26)
        layout.addWidget(self._install_progress_bar)

        self._install_terminal = QTextEdit()
        self._install_terminal.setObjectName("terminal")
        self._install_terminal.setReadOnly(True)
        self._install_terminal.setStyleSheet(terminal_stylesheet())
        self._install_terminal.setMinimumHeight(200)
        layout.addWidget(self._install_terminal)

        close_btn = QPushButton("Yopish")
        close_btn.setEnabled(False)
        close_btn.clicked.connect(dialog.close)
        self._install_close_btn = close_btn
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._install_dialog = dialog
        dialog.show()
        self._status_bar.showMessage(f"⏳  '{filename}' o'rnatilmoqda...")

    def _on_install_progress(self, message: str) -> None:
        """O'rnatish bosqichi yangilanganda."""
        if hasattr(self, "_install_status_label"):
            self._install_status_label.set_text(message)
        self._status_bar.showMessage(f"📦  {message}")

    def _on_install_terminal_output(self, text: str) -> None:
        """O'rnatish terminal chiqishini ko'rsatadi."""
        if hasattr(self, "_install_terminal"):
            self._install_terminal.insertPlainText(text)
            self._install_terminal.ensureCursorVisible()

    def _on_install_finished(self, success: bool, message: str) -> None:
        """Fayldan o'rnatish tugaganda."""
        self._install_file_btn.setEnabled(True)

        if hasattr(self, "_install_progress_bar"):
            if success:
                self._install_progress_bar.set_success()
            else:
                self._install_progress_bar.set_error()

        if hasattr(self, "_install_status_label"):
            self._install_status_label.stop()
            status = "✓ O'rnatish muvaffaqiyatli yakunlandi" if success else "✗ O'rnatishda xatolik"
            self._install_status_label.setText(status)
            c = colors()
            self._install_status_label.setStyleSheet(
                f"color: {c['success_text'] if success else c['danger']}; "
                f"font-size: 13px; font-weight: 600;"
            )

        if hasattr(self, "_install_terminal"):
            prefix = "\n✓ " if success else "\n✗ "
            self._install_terminal.insertPlainText(f"{prefix}{message}\n")
            self._install_terminal.ensureCursorVisible()

        if hasattr(self, "_install_close_btn"):
            self._install_close_btn.setEnabled(True)

        if success:
            self._status_bar.showMessage(f"✓  {message}", 5000)
            self._success_flash.flash()
            self._start_scan()
        else:
            self._status_bar.showMessage(f"⚠️  {message}", 8000)
            self._add_error(f"Fayldan o'rnatish xatoligi: {message}")
            QMessageBox.warning(
                self,
                "O'rnatish xatoligi",
                f"Fayl o'rnatilmadi:\n\n{message}",
            )

    def _on_toggle_autostart(self, entry: AutostartEntry, checked: bool) -> None:
        """Avtoishga tushish holatini o'zgartirish."""
        success, message = toggle_autostart(entry, enable=checked)

        if success:
            self._status_bar.showMessage(f"✓  {message}", 5000)
            # Checkbox matnini yangilash
            entry.enabled = checked
        else:
            self._status_bar.showMessage(f"⚠️  {message}", 5000)
            # Checkboxni asl holatiga qaytarish
            QTimer.singleShot(100, lambda: self._start_scan())

    def _on_remove_autostart(self, entry: AutostartEntry) -> None:
        """Avtoishga tushish yozuvini olib tashlash."""
        desc = "tizim darajasida yashiriladi" if entry.is_system else "o'chiriladi"
        reply = QMessageBox.question(
            self,
            "Avtoishga tushish yozuvini olib tashlash",
            f"«{entry.name}» avtoishga tushish ro'yxatidan olib tashlansinmi?\n\n"
            f"Fayl: {entry.desktop_path}\n"
            f"Amal: {desc}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, message = remove_autostart_entry(entry)
        if success:
            self._status_bar.showMessage(f"✓  {message}", 5000)
            QTimer.singleShot(300, self._start_scan)
        else:
            self._status_bar.showMessage(f"⚠️  {message}", 5000)
            QMessageBox.warning(
                self,
                "Xatolik",
                f"Olib tashlashda xatolik:\n\n{message}",
            )

    def _on_remove_autostart_finished(self, entry: AutostartEntry, success: bool, message: str) -> None:
        """Avtoishga tushishdan o'chirish yakunlanganda."""
        if success:
            self._status_bar.showMessage(f"✓  {message}", 5000)
            self._start_scan()
        else:
            self._status_bar.showMessage(f"⚠️  {message}", 8000)
            self._add_error(f"Avtoishga tushish yozuvini o'chirish xatoligi: «{entry.name}» — {message}")
            QMessageBox.warning(
                self,
                "O'chirishda xatolik",
                f"«{entry.name}» o'chirilmadi:\n\n{message}",
            )

    # ── Tozalash ───────────────────────────────────────────────────────────

    def _start_cleaning(self) -> None:
        """Tozalash jarayonini boshlaydi."""
        if self._clean_worker and self._clean_worker.isRunning():
            return

        do_apt_cache = self._chk_apt_cache.isChecked()
        do_apt_autoremove = self._chk_apt_autoremove.isChecked()
        do_apt_leftovers = self._chk_apt_leftovers.isChecked()
        do_flatpak = self._chk_flatpak.isChecked()
        do_journal = self._chk_journal.isChecked()

        if not any([do_apt_cache, do_apt_autoremove, do_apt_leftovers, do_flatpak, do_journal]):
            QMessageBox.information(self, "Ma'lumot", "Iltimos, tozalash uchun kamida bitta variantni tanlang.")
            return

        # Terminalni tozalaymiz
        self._clean_terminal.clear()
        self._clean_terminal.insertPlainText("Tozalash jarayoni boshlanmoqda...\n\n")

        self._start_clean_btn.setEnabled(False)
        self._start_clean_btn.setText("  Tozalanmoqda...")
        self._status_bar.showMessage("Tozalash boshlandi...")

        self._clean_worker = CleanWorker(
            do_apt_cache=do_apt_cache,
            do_apt_autoremove=do_apt_autoremove,
            do_apt_leftovers=do_apt_leftovers,
            do_flatpak=do_flatpak,
            do_journal=do_journal,
            parent=self
        )
        self._clean_worker.progress.connect(self._on_clean_progress)
        self._clean_worker.terminal_output.connect(self._on_clean_terminal_output)
        self._clean_worker.error_occurred.connect(self._on_clean_error)
        self._clean_worker.finished_step.connect(self._on_clean_finished_step)
        self._clean_worker.finished_all.connect(self._on_clean_finished_all)
        self._clean_worker.start()

    def _on_clean_terminal_output(self, text: str) -> None:
        """Terminal oynasiga qator qo'shadi."""
        self._clean_terminal.insertPlainText(text)
        self._clean_terminal.ensureCursorVisible()

    def _on_clean_progress(self, message: str) -> None:
        self._status_bar.showMessage(f"⏳  {message}")

    def _on_clean_error(self, message: str) -> None:
        self._add_error(f"Tozalash xatoligi: {message}")

    def _on_clean_finished_step(self, success: bool, message: str) -> None:
        # Har qadam tugaganda status barni yangilab turamiz
        pass

    def _on_clean_finished_all(self) -> None:
        self._start_clean_btn.setEnabled(True)
        self._start_clean_btn.setText("  Tozalashni boshlash")
        self._status_bar.showMessage("✓ Tozalash jarayoni to'liq yakunlandi!", 8000)
        QMessageBox.information(self, "Tozalash yakunlandi", "Tanlangan barcha qismlar tozalandi!")

    # ── Yordamchi ──────────────────────────────────────────────────────────

    @staticmethod
    def _col_widget(widgets: list) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for w in widgets:
            layout.addWidget(w)
        return container

    @staticmethod
    def _row_widget(widgets: list[QWidget]) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for w in widgets:
            layout.addWidget(w)
        return container

    @staticmethod
    def _center_widget(widget: QWidget) -> QWidget:
        """Widgetni markazlashtirilgan konteynerga o'raydi."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget)
        return container

    # ── Xatoliklar Tab'i Yordamchi Funksiyalari ────────────────────────────

    def _add_error(self, message: str) -> None:
        """Xatoliklar ro'yxatiga yangi xatolik qo'shadi."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        self._errors.append(full_message)
        self._errors_list.addItem(full_message)
        
        # Tab nomini yangilash (agar xatoliklar bo'lsa)
        count = len(self._errors)
        self._tabs.setTabText(self._TAB_ERRORS, f"Xatoliklar ({count})")

    def _clear_errors(self) -> None:
        """Xatoliklar ro'yxatini tozalaydi."""
        self._errors.clear()
        self._errors_list.clear()
        self._tabs.setTabText(self._TAB_ERRORS, "Xatoliklar")

    def _pulse_status_bar(self, active: bool) -> None:
        """Status bar matnini pulsatsiya qilish."""
        if active:
            if self._status_pulse is None:
                self._status_pulse = PulseAnimator(self._status_bar, min_opacity=0.5)
            self._status_pulse.start()
        elif self._status_pulse is not None:
            self._status_pulse.stop()
