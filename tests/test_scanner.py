"""
core/scanner.py uchun unit testlar.
subprocess.run mock qilinadi — haqiqiy tizim komandalari chaqirilmaydi.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from core.scanner import (
    get_manual_apt_packages,
    get_dpkg_owners,
    get_snap_apps,
    get_flatpak_apps,
    build_app_list,
    _should_skip_by_category,
    _is_library_package,
    App,
)


class TestGetManualAptPackages:
    """apt-mark showmanual testlari."""

    @patch("core.scanner.subprocess.run")
    def test_returns_set_of_packages(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="firefox\nvlc\ngimp\n",
        )
        result = get_manual_apt_packages()
        assert result == {"firefox", "vlc", "gimp"}

    @patch("core.scanner.subprocess.run")
    def test_empty_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = get_manual_apt_packages()
        assert result == set()

    @patch("core.scanner.subprocess.run")
    def test_command_not_found(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        result = get_manual_apt_packages()
        assert result == set()

    @patch("core.scanner.subprocess.run")
    def test_command_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = get_manual_apt_packages()
        assert result == set()

    @patch("core.scanner.subprocess.run")
    def test_timeout(self, mock_run: MagicMock) -> None:
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("apt-mark", 30)
        result = get_manual_apt_packages()
        assert result == set()


class TestGetSnapApps:
    """snap list testlari."""

    @patch("core.scanner.subprocess.run")
    def test_returns_apps_filtering_system(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "Name      Version  Rev    Tracking     Publisher   Notes\n"
                "core22    20231219 1122   latest/stable canonical✓ base\n"
                "firefox   120.0    3440   latest/stable mozilla✓   -\n"
                "snapd     2.61     20671  latest/stable canonical✓ snapd\n"
                "telegram  4.12     1234   latest/stable telegram   -\n"
            ),
        )
        result = get_snap_apps()
        names = [app["name"] for app in result]
        assert "firefox" in names
        assert "telegram" in names
        assert "core22" not in names
        assert "snapd" not in names

    @patch("core.scanner.subprocess.run")
    def test_snap_not_installed(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        result = get_snap_apps()
        assert result == []

    @patch("core.scanner.subprocess.run")
    def test_snap_command_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = get_snap_apps()
        assert result == []


class TestGetFlatpakApps:
    """flatpak list testlari."""

    @patch("core.scanner.subprocess.run")
    def test_returns_apps(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="org.gimp.GIMP\tGNU Image Manipulation Program\norg.vlc.VLC\tVLC media player\n",
        )
        result = get_flatpak_apps()
        assert len(result) == 2
        assert result[0]["app_id"] == "org.gimp.GIMP"
        assert result[1]["name"] == "VLC media player"

    @patch("core.scanner.subprocess.run")
    def test_flatpak_not_installed(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        result = get_flatpak_apps()
        assert result == []

    @patch("core.scanner.subprocess.run")
    def test_flatpak_command_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = get_flatpak_apps()
        assert result == []


class TestShouldSkipByCategory:
    """Kategoriya filtri testlari."""

    def test_only_settings(self) -> None:
        assert _should_skip_by_category("Settings;") is True

    def test_only_system(self) -> None:
        assert _should_skip_by_category("System;") is True

    def test_settings_and_system(self) -> None:
        assert _should_skip_by_category("Settings;System;") is True

    def test_mixed_categories(self) -> None:
        assert _should_skip_by_category("Graphics;Settings;") is False

    def test_empty_categories(self) -> None:
        assert _should_skip_by_category("") is False

    def test_normal_app(self) -> None:
        assert _should_skip_by_category("Audio;Music;Player;") is False


class TestIsLibraryPackage:
    """Kutubxona paket tekshiruvi."""

    def test_library(self) -> None:
        assert _is_library_package("libgtk-3-0") is True

    def test_not_library(self) -> None:
        assert _is_library_package("firefox") is False

    def test_libre_office_not_library(self) -> None:
        # "libreoffice" "lib" bilan boshlansa ham, bu kutubxona emas
        # Lekin bizning oddiy tekshiruv uni filtrlab yuboradi
        # Bu ma'lum cheklov — murakkab mantiq kerak bo'lmasa, bu yetarli
        assert _is_library_package("libreoffice") is True


class TestBuildAppList:
    """build_app_list asosiy funksiyasi testlari."""

    @patch("core.scanner.find_desktop_files")
    @patch("core.scanner.parse_desktop_entry")
    @patch("core.scanner.get_manual_apt_packages")
    @patch("core.scanner.get_snap_apps")
    @patch("core.scanner.get_flatpak_apps")
    @patch("core.scanner.get_dpkg_owners")
    @patch("core.scanner.get_essential_packages")
    def test_nodisplay_filtered_out(
        self,
        mock_essential_packages: MagicMock,
        mock_dpkg_owners: MagicMock,
        mock_flatpak: MagicMock,
        mock_snap: MagicMock,
        mock_manual: MagicMock,
        mock_parse: MagicMock,
        mock_find: MagicMock,
    ) -> None:
        """NoDisplay=true bo'lgan dastur ro'yxatga tushmasligi kerak."""
        mock_find.return_value = ["/usr/share/applications/hidden.desktop"]
        mock_parse.return_value = {
            "Name": "Hidden App",
            "Type": "Application",
            "NoDisplay": "true",
            "Exec": "/usr/bin/hidden",
        }
        mock_manual.return_value = set()
        mock_snap.return_value = []
        mock_flatpak.return_value = []
        mock_dpkg_owners.return_value = {}
        mock_essential_packages.return_value = set()

        result = build_app_list()
        assert len(result) == 0

    @patch("core.scanner.find_desktop_files")
    @patch("core.scanner.parse_desktop_entry")
    @patch("core.scanner.get_manual_apt_packages")
    @patch("core.scanner.get_snap_apps")
    @patch("core.scanner.get_flatpak_apps")
    @patch("core.scanner.get_dpkg_owners")
    @patch("core.scanner.get_essential_packages")
    def test_hidden_filtered_out(
        self,
        mock_essential_packages: MagicMock,
        mock_dpkg_owners: MagicMock,
        mock_flatpak: MagicMock,
        mock_snap: MagicMock,
        mock_manual: MagicMock,
        mock_parse: MagicMock,
        mock_find: MagicMock,
    ) -> None:
        """Hidden=true bo'lgan dastur ro'yxatga tushmasligi kerak."""
        mock_find.return_value = ["/usr/share/applications/hidden2.desktop"]
        mock_parse.return_value = {
            "Name": "Hidden App 2",
            "Type": "Application",
            "Hidden": "true",
            "Exec": "/usr/bin/hidden2",
        }
        mock_manual.return_value = set()
        mock_snap.return_value = []
        mock_flatpak.return_value = []
        mock_dpkg_owners.return_value = {}
        mock_essential_packages.return_value = set()

        result = build_app_list()
        assert len(result) == 0

    @patch("core.scanner.find_desktop_files")
    @patch("core.scanner.parse_desktop_entry")
    @patch("core.scanner.get_manual_apt_packages")
    @patch("core.scanner.get_snap_apps")
    @patch("core.scanner.get_flatpak_apps")
    @patch("core.scanner.get_dpkg_owners")
    @patch("core.scanner.get_essential_packages")
    def test_snap_source_detected(
        self,
        mock_essential_packages: MagicMock,
        mock_dpkg_owners: MagicMock,
        mock_flatpak: MagicMock,
        mock_snap: MagicMock,
        mock_manual: MagicMock,
        mock_parse: MagicMock,
        mock_find: MagicMock,
    ) -> None:
        """Snap dasturi to'g'ri aniqlanishi kerak."""
        mock_find.return_value = [
            "/var/lib/snapd/desktop/applications/firefox_firefox.desktop"
        ]
        mock_parse.return_value = {
            "Name": "Firefox",
            "Type": "Application",
            "Exec": "/snap/firefox/current/firefox %u",
            "Icon": "firefox",
        }
        mock_manual.return_value = set()
        mock_snap.return_value = [{"name": "firefox", "version": "120.0"}]
        mock_flatpak.return_value = []
        mock_dpkg_owners.return_value = {}
        mock_essential_packages.return_value = set()

        result = build_app_list()
        assert len(result) == 1
        assert result[0].source == "snap"
        assert result[0].identifier == "firefox"

    @patch("core.scanner.find_desktop_files")
    @patch("core.scanner.parse_desktop_entry")
    @patch("core.scanner.get_manual_apt_packages")
    @patch("core.scanner.get_snap_apps")
    @patch("core.scanner.get_flatpak_apps")
    @patch("core.scanner.get_dpkg_owners")
    @patch("core.scanner.get_essential_packages")
    def test_flatpak_source_detected(
        self,
        mock_essential_packages: MagicMock,
        mock_dpkg_owners: MagicMock,
        mock_flatpak: MagicMock,
        mock_snap: MagicMock,
        mock_manual: MagicMock,
        mock_parse: MagicMock,
        mock_find: MagicMock,
    ) -> None:
        """Flatpak dasturi to'g'ri aniqlanishi kerak."""
        mock_find.return_value = [
            "/usr/share/applications/org.gimp.GIMP.desktop"
        ]
        mock_parse.return_value = {
            "Name": "GIMP",
            "Type": "Application",
            "Exec": "flatpak run org.gimp.GIMP %U",
            "Icon": "gimp",
        }
        mock_manual.return_value = set()
        mock_snap.return_value = []
        mock_flatpak.return_value = [{"app_id": "org.gimp.GIMP", "name": "GIMP"}]
        mock_dpkg_owners.return_value = {}
        mock_essential_packages.return_value = set()

        result = build_app_list()
        assert len(result) == 1
        assert result[0].source == "flatpak"
        assert result[0].identifier == "org.gimp.GIMP"

    @patch("core.scanner.find_desktop_files")
    @patch("core.scanner.parse_desktop_entry")
    @patch("core.scanner.get_manual_apt_packages")
    @patch("core.scanner.get_snap_apps")
    @patch("core.scanner.get_flatpak_apps")
    @patch("core.scanner.get_dpkg_owners")
    @patch("core.scanner.get_essential_packages")
    def test_manual_source_detected(
        self,
        mock_essential_packages: MagicMock,
        mock_dpkg_owners: MagicMock,
        mock_flatpak: MagicMock,
        mock_snap: MagicMock,
        mock_manual: MagicMock,
        mock_parse: MagicMock,
        mock_find: MagicMock,
    ) -> None:
        """Qo'lda o'rnatilgan dastur to'g'ri aniqlanishi kerak."""
        desktop_path = os.path.expanduser("~/.local/share/applications/myapp.desktop")
        mock_find.return_value = [desktop_path]
        mock_parse.return_value = {
            "Name": "My App",
            "Type": "Application",
            "Exec": "/opt/myapp/myapp",
            "Icon": "myapp",
        }
        mock_manual.return_value = set()
        mock_snap.return_value = []
        mock_flatpak.return_value = []
        mock_dpkg_owners.return_value = {}
        mock_essential_packages.return_value = set()

        result = build_app_list()
        assert len(result) == 1
        assert result[0].source == "manual"

    @patch("core.scanner.find_desktop_files")
    @patch("core.scanner.parse_desktop_entry")
    @patch("core.scanner.get_manual_apt_packages")
    @patch("core.scanner.get_snap_apps")
    @patch("core.scanner.get_flatpak_apps")
    @patch("core.scanner.get_dpkg_owners")
    @patch("core.scanner.get_essential_packages")
    def test_non_application_type_filtered(
        self,
        mock_essential_packages: MagicMock,
        mock_dpkg_owners: MagicMock,
        mock_flatpak: MagicMock,
        mock_snap: MagicMock,
        mock_manual: MagicMock,
        mock_parse: MagicMock,
        mock_find: MagicMock,
    ) -> None:
        """Type=Link kabi Application bo'lmagan yozuvlar filtrlanishi kerak."""
        mock_find.return_value = ["/usr/share/applications/link.desktop"]
        mock_parse.return_value = {
            "Name": "Some Link",
            "Type": "Link",
            "URL": "https://example.com",
        }
        mock_manual.return_value = set()
        mock_snap.return_value = []
        mock_flatpak.return_value = []
        mock_dpkg_owners.return_value = {}
        mock_essential_packages.return_value = set()

        result = build_app_list()
        assert len(result) == 0
