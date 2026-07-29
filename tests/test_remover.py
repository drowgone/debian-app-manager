"""
core/remover.py uchun unit testlar.
subprocess.run va os.remove mock qilinadi.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from core.remover import (
    remove_apt_package,
    remove_snap_package,
    remove_flatpak_app,
    remove_manual_app,
    _is_safe_path,
)


class TestIsSafePath:
    """Yo'l xavfsizligi tekshiruvi testlari."""

    @patch("os.path.realpath", side_effect=lambda p: p)
    def test_home_directory_safe(self, mock_real: MagicMock) -> None:
        home = os.path.expanduser("~")
        assert _is_safe_path(f"{home}/apps/test.desktop") is True

    @patch("os.path.realpath", side_effect=lambda p: p)
    def test_opt_directory_safe(self, mock_real: MagicMock) -> None:
        assert _is_safe_path("/opt/myapp/myapp.desktop") is True

    @patch("os.path.realpath", side_effect=lambda p: p)
    def test_usr_bin_forbidden(self, mock_real: MagicMock) -> None:
        assert _is_safe_path("/usr/bin/something") is False

    @patch("os.path.realpath", side_effect=lambda p: p)
    def test_usr_lib_forbidden(self, mock_real: MagicMock) -> None:
        assert _is_safe_path("/usr/lib/something") is False

    @patch("os.path.realpath", side_effect=lambda p: p)
    def test_etc_forbidden(self, mock_real: MagicMock) -> None:
        assert _is_safe_path("/etc/something") is False

    @patch("os.path.realpath")
    def test_symlink_to_system_blocked(self, mock_real: MagicMock) -> None:
        """Symlink orqali tizim faylini o'chirishning oldini olish."""
        # Foydalanuvchi papkasidagi symlink /usr/lib ga ishora qiladi
        mock_real.return_value = "/usr/lib/important.so"
        home = os.path.expanduser("~")
        assert _is_safe_path(f"{home}/sneaky_link") is False


class TestRemoveAptPackage:
    """APT paketini o'chirish testlari."""

    @patch("core.remover.subprocess.run")
    def test_successful_removal(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        success, message = remove_apt_package("firefox")
        assert success is True
        assert "muvaffaqiyatli" in message
        # pkexec bilan chaqirilganini tekshirish
        mock_run.assert_called_once_with(
            ["pkexec", "apt-get", "remove", "--yes", "firefox"],
            capture_output=True, text=True, timeout=300,
        )

    @patch("core.remover.subprocess.run")
    def test_user_cancelled(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=126, stderr="dismissed", stdout=""
        )
        success, message = remove_apt_package("firefox")
        assert success is False
        assert "bekor" in message

    @patch("core.remover.subprocess.run")
    def test_pkexec_not_found(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        success, message = remove_apt_package("firefox")
        assert success is False
        assert "pkexec" in message

    def test_invalid_package_name(self) -> None:
        success, message = remove_apt_package("bad;name")
        assert success is False

    def test_empty_package_name(self) -> None:
        success, message = remove_apt_package("")
        assert success is False

    @patch("core.remover.subprocess.run")
    def test_timeout(self, mock_run: MagicMock) -> None:
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("pkexec", 300)
        success, message = remove_apt_package("firefox")
        assert success is False
        assert "Vaqt tugadi" in message


class TestRemoveSnapPackage:
    """Snap paketini o'chirish testlari."""

    @patch("core.remover.subprocess.run")
    def test_successful_removal(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        success, message = remove_snap_package("firefox")
        assert success is True

    @patch("core.remover.subprocess.run")
    def test_snap_not_installed(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        success, message = remove_snap_package("firefox")
        assert success is False
        assert "topilmadi" in message

    @patch("core.remover.subprocess.run")
    def test_permission_denied_escalates(self, mock_run: MagicMock) -> None:
        """Ruxsat rad etilganda pkexec bilan qayta urinish."""
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="access denied", stdout=""),
            MagicMock(returncode=0, stderr="", stdout=""),
        ]
        success, message = remove_snap_package("firefox")
        assert success is True
        assert mock_run.call_count == 2

    def test_invalid_snap_name(self) -> None:
        success, message = remove_snap_package("bad;name")
        assert success is False


class TestRemoveFlatpakApp:
    """Flatpak ilovasini o'chirish testlari."""

    @patch("core.remover.subprocess.run")
    def test_successful_removal(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        success, message = remove_flatpak_app("org.gimp.GIMP")
        assert success is True
        # --noninteractive flag'i bilan chaqirilganini tekshirish
        mock_run.assert_called_once_with(
            ["flatpak", "uninstall", "--noninteractive", "org.gimp.GIMP"],
            capture_output=True, text=True, timeout=300,
        )

    @patch("core.remover.subprocess.run")
    def test_flatpak_not_installed(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        success, message = remove_flatpak_app("org.gimp.GIMP")
        assert success is False
        assert "topilmadi" in message

    def test_empty_app_id(self) -> None:
        success, message = remove_flatpak_app("")
        assert success is False


class TestRemoveManualApp:
    """Qo'lda o'rnatilgan dasturni o'chirish testlari."""

    @patch("os.remove")
    @patch("os.path.isfile")
    @patch("os.path.realpath")
    def test_successful_removal(
        self, mock_real: MagicMock, mock_isfile: MagicMock, mock_remove: MagicMock,
    ) -> None:
        home = os.path.expanduser("~")
        desktop_path = f"{home}/.local/share/applications/test.desktop"
        mock_real.return_value = desktop_path
        mock_isfile.return_value = True

        success, message = remove_manual_app(desktop_path)
        assert success is True
        mock_remove.assert_called_once_with(desktop_path)

    @patch("os.path.realpath")
    def test_system_path_blocked(self, mock_real: MagicMock) -> None:
        """Tizim papkasidagi fayl o'chirilmasligi kerak."""
        mock_real.return_value = "/usr/bin/dangerous"
        success, message = remove_manual_app("/usr/bin/dangerous.desktop")
        assert success is False
        assert "taqiqlangan" in message

    def test_invalid_extension(self) -> None:
        success, message = remove_manual_app("/home/user/test.txt")
        assert success is False

    def test_empty_path(self) -> None:
        success, message = remove_manual_app("")
        assert success is False

    @patch("os.path.isfile")
    @patch("os.path.realpath")
    def test_file_not_found(
        self, mock_real: MagicMock, mock_isfile: MagicMock,
    ) -> None:
        home = os.path.expanduser("~")
        path = f"{home}/.local/share/applications/gone.desktop"
        mock_real.return_value = path
        mock_isfile.return_value = False
        success, message = remove_manual_app(path)
        assert success is False
        assert "topilmadi" in message
