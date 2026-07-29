import pytest
from unittest.mock import patch, MagicMock
from core.updater import (
    get_apt_updates,
    get_snap_updates,
    get_flatpak_updates,
    update_apt_package,
    update_snap_package,
    update_flatpak_app,
)

class TestGetUpdates:
    @patch("core.updater.subprocess.run")
    def test_get_apt_updates_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="firefox/stable 121.0-1 amd64 [upgradable from: 120.0-1]\n"
                   "curl/stable 8.5.0-1 amd64 [upgradable from: 8.4.0-1]\n"
        )
        updates = get_apt_updates()
        assert len(updates) == 2
        assert updates["firefox"] == "121.0-1"
        assert updates["curl"] == "8.5.0-1"

    @patch("core.updater.subprocess.run")
    def test_get_apt_updates_empty(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="Listing...\n")
        updates = get_apt_updates()
        assert len(updates) == 0

    @patch("core.updater.subprocess.run")
    def test_get_snap_updates_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Name  Version  Rev  Publisher  Notes\n"
                   "firefox 121.0 3441 mozilla -\n"
                   "telegram 4.12 1235 telegram -\n"
        )
        updates = get_snap_updates()
        assert len(updates) == 2
        assert updates["firefox"] == "121.0"
        assert updates["telegram"] == "4.12"

    @patch("core.updater.subprocess.run")
    def test_get_flatpak_updates_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="org.gimp.GIMP\t2.10.36\norg.vlc.VLC\t3.0.20\n"
        )
        updates = get_flatpak_updates()
        assert len(updates) == 2
        assert updates["org.gimp.GIMP"] == "2.10.36"

class TestUpdateCommands:
    @patch("core.updater.subprocess.run")
    def test_update_apt_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        assert update_apt_package("firefox") is True

    @patch("core.updater.subprocess.run")
    def test_update_snap_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        assert update_snap_package("firefox") is True

    @patch("core.updater.subprocess.run")
    def test_update_flatpak_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        assert update_flatpak_app("org.gimp.GIMP") is True
