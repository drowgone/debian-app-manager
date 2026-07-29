"""
core/autostart.py uchun unit testlar.
Fayl tizimi operatsiyalari mock qilinadi.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, mock_open

from core.autostart import (
    get_autostart_entries,
    toggle_autostart,
    remove_autostart_entry,
    AutostartEntry,
    _is_entry_enabled,
    USER_AUTOSTART_DIR,
    SYSTEM_AUTOSTART_DIR,
)


class TestIsEntryEnabled:
    """Desktop entry yoqilgan/o'chirilgan holati testlari."""

    def test_enabled_by_default(self) -> None:
        entry = {"Name": "Test", "Type": "Application"}
        assert _is_entry_enabled(entry) is True

    def test_hidden_true(self) -> None:
        entry = {"Name": "Test", "Hidden": "true"}
        assert _is_entry_enabled(entry) is False

    def test_hidden_false(self) -> None:
        entry = {"Name": "Test", "Hidden": "false"}
        assert _is_entry_enabled(entry) is True

    def test_gnome_autostart_disabled(self) -> None:
        entry = {"Name": "Test", "X-GNOME-Autostart-enabled": "false"}
        assert _is_entry_enabled(entry) is False

    def test_gnome_autostart_enabled(self) -> None:
        entry = {"Name": "Test", "X-GNOME-Autostart-enabled": "true"}
        assert _is_entry_enabled(entry) is True


class TestGetAutostartEntries:
    """Avtoishga tushish yozuvlarini o'qish testlari."""

    @patch("core.autostart.find_desktop_files")
    @patch("core.autostart.parse_desktop_entry")
    def test_user_entry_loaded(
        self, mock_parse: MagicMock, mock_find: MagicMock,
    ) -> None:
        user_path = os.path.join(USER_AUTOSTART_DIR, "test.desktop")
        mock_find.side_effect = [
            [user_path],  # Foydalanuvchi fayllari
            [],           # Tizim fayllari
        ]
        mock_parse.return_value = {
            "Name": "Test App",
            "Type": "Application",
            "Exec": "/usr/bin/test",
        }

        entries = get_autostart_entries()
        assert len(entries) == 1
        assert entries[0].name == "Test App"
        assert entries[0].enabled is True

    @patch("core.autostart.find_desktop_files")
    @patch("core.autostart.parse_desktop_entry")
    def test_hidden_entry_disabled(
        self, mock_parse: MagicMock, mock_find: MagicMock,
    ) -> None:
        user_path = os.path.join(USER_AUTOSTART_DIR, "disabled.desktop")
        mock_find.side_effect = [
            [user_path],
            [],
        ]
        mock_parse.return_value = {
            "Name": "Disabled App",
            "Hidden": "true",
        }

        entries = get_autostart_entries()
        assert len(entries) == 1
        assert entries[0].enabled is False

    @patch("core.autostart.find_desktop_files")
    @patch("core.autostart.parse_desktop_entry")
    @patch("os.path.isfile")
    def test_system_entry_marked_as_system(
        self, mock_isfile: MagicMock, mock_parse: MagicMock, mock_find: MagicMock,
    ) -> None:
        system_path = os.path.join(SYSTEM_AUTOSTART_DIR, "sys.desktop")
        mock_find.side_effect = [
            [],             # Foydalanuvchi fayllari yo'q
            [system_path],  # Tizim fayllari
        ]
        mock_parse.return_value = {
            "Name": "System App",
            "Exec": "/usr/bin/sysapp",
        }
        mock_isfile.return_value = False  # Override fayli yo'q

        entries = get_autostart_entries()
        assert len(entries) == 1
        assert entries[0].is_system is True

    @patch("core.autostart.find_desktop_files")
    @patch("core.autostart.parse_desktop_entry")
    @patch("os.path.isfile")
    def test_user_override_hides_system(
        self, mock_isfile: MagicMock, mock_parse: MagicMock, mock_find: MagicMock,
    ) -> None:
        """Foydalanuvchi override fayli bo'lsa, tizim fayli qo'shilmasligi kerak."""
        user_path = os.path.join(USER_AUTOSTART_DIR, "shared.desktop")
        system_path = os.path.join(SYSTEM_AUTOSTART_DIR, "shared.desktop")

        mock_find.side_effect = [
            [user_path],      # Foydalanuvchi override
            [system_path],    # Tizim fayli
        ]
        mock_parse.return_value = {
            "Name": "Shared App",
            "Hidden": "true",
        }
        mock_isfile.return_value = True  # Tizim counterpart mavjud

        entries = get_autostart_entries()
        # Faqat foydalanuvchi override ko'rsatiladi, tizim fayli emas
        assert len(entries) == 1
        assert entries[0].desktop_path == user_path


class TestToggleAutostart:
    """Avtoishga tushish yoqish/o'chirish testlari."""

    @patch("core.autostart._update_desktop_file_status")
    @patch("os.path.isfile")
    def test_toggle_user_entry(
        self, mock_isfile: MagicMock, mock_update: MagicMock,
    ) -> None:
        entry = AutostartEntry(
            name="Test",
            desktop_path=os.path.join(USER_AUTOSTART_DIR, "test.desktop"),
            filename="test.desktop",
            enabled=True,
            is_system=False,
            icon="",
            comment="",
        )
        mock_isfile.return_value = True

        success, message = toggle_autostart(entry, enable=False)
        assert success is True
        mock_update.assert_called_once()

    @patch("core.autostart._write_override_file")
    @patch("os.path.isfile")
    def test_toggle_system_entry_creates_override(
        self, mock_isfile: MagicMock, mock_write: MagicMock,
    ) -> None:
        """Tizim fayli uchun override yaratilishi kerak."""
        entry = AutostartEntry(
            name="System App",
            desktop_path=os.path.join(SYSTEM_AUTOSTART_DIR, "sysapp.desktop"),
            filename="sysapp.desktop",
            enabled=True,
            is_system=True,
            icon="",
            comment="",
        )
        mock_isfile.return_value = False  # Override fayl hali yo'q

        success, message = toggle_autostart(entry, enable=False)
        assert success is True
        mock_write.assert_called_once_with("sysapp.desktop", hidden=True)


class TestRemoveAutostartEntry:
    """Avtoishga tushish yozuvini olib tashlash testlari."""

    @patch("core.autostart._write_override_file")
    def test_remove_system_creates_override(self, mock_write: MagicMock) -> None:
        """Tizim faylini o'chirish emas, override yaratish kerak."""
        entry = AutostartEntry(
            name="System App",
            desktop_path=os.path.join(SYSTEM_AUTOSTART_DIR, "sysapp.desktop"),
            filename="sysapp.desktop",
            enabled=True,
            is_system=True,
            icon="",
            comment="",
        )

        success, message = remove_autostart_entry(entry)
        assert success is True
        assert "yashirildi" in message
        mock_write.assert_called_once_with("sysapp.desktop", hidden=True)

    @patch("os.remove")
    @patch("os.path.isfile")
    def test_remove_user_deletes_file(
        self, mock_isfile: MagicMock, mock_remove: MagicMock,
    ) -> None:
        """Foydalanuvchi faylini o'chirish mumkin."""
        user_path = os.path.join(USER_AUTOSTART_DIR, "myapp.desktop")
        entry = AutostartEntry(
            name="My App",
            desktop_path=user_path,
            filename="myapp.desktop",
            enabled=True,
            is_system=False,
            icon="",
            comment="",
        )
        mock_isfile.return_value = True

        success, message = remove_autostart_entry(entry)
        assert success is True
        mock_remove.assert_called_once_with(user_path)
