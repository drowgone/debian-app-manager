import os
import shutil
import stat
import subprocess
from unittest import mock

import pytest

from core.appimage_manager import (
    APPIMAGE_DIR, DESKTOP_DIR, ICON_CACHE_DIR, AppImageApp,
    extract_appimage_metadata, import_appimage, remove_appimage,
    is_appimage_managed,
)


@pytest.fixture
def mock_dirs(tmp_path):
    """
    Testlar uchun APPIMAGE_DIR, DESKTOP_DIR va ICON_CACHE_DIR yo'llarini
    vaqtinchalik (tmp_path) papkaga yo'naltiradi.
    """
    app_dir = tmp_path / "Applications"
    desk_dir = tmp_path / "applications"
    icon_dir = tmp_path / "icons"

    with mock.patch("core.appimage_manager.APPIMAGE_DIR", str(app_dir)), \
         mock.patch("core.appimage_manager.DESKTOP_DIR", str(desk_dir)), \
         mock.patch("core.appimage_manager.ICON_CACHE_DIR", str(icon_dir)):
        yield app_dir, desk_dir, icon_dir


def test_is_appimage_managed():
    assert is_appimage_managed({"X-AppImage-Managed": "true"}) is True
    assert is_appimage_managed({"X-AppImage-Managed": "True"}) is True
    assert is_appimage_managed({"X-AppImage-Managed": "false"}) is False
    assert is_appimage_managed({}) is False


def test_extract_metadata_success(tmp_path):
    """Muvaffaqiyatli extraction holati."""
    dummy_appimage = tmp_path / "Dummy.AppImage"
    dummy_appimage.write_text("dummy")

    def mock_run(*args, **kwargs):
        # subprocess.run o'rnida: cwd ichida 'squashfs-root' yaratamiz
        # va uning ichiga .desktop va ikonka fayllarini qo'yamiz
        cwd = kwargs.get("cwd")
        sq_root = os.path.join(cwd, "squashfs-root")
        os.makedirs(sq_root)
        
        # .desktop
        desktop_content = "[Desktop Entry]\nName=My App\nIcon=my-icon\nComment=Test"
        with open(os.path.join(sq_root, "dummy.desktop"), "w") as f:
            f.write(desktop_content)
            
        # ikonka
        with open(os.path.join(sq_root, "my-icon.png"), "w") as f:
            f.write("icon-data")

        return mock.Mock(returncode=0)

    icon_cache = tmp_path / "icons"
    with mock.patch("core.appimage_manager.ICON_CACHE_DIR", str(icon_cache)), \
         mock.patch("subprocess.run", side_effect=mock_run):
        metadata = extract_appimage_metadata(str(dummy_appimage))
    
    assert metadata["Name"] == "My App"
    assert metadata["Comment"] == "Test"
    assert metadata["Icon"].endswith("Dummy.png")
    
    # Executable permissions check
    st = os.stat(str(dummy_appimage))
    assert st.st_mode & stat.S_IXUSR


def test_extract_metadata_timeout_fallback(tmp_path):
    """Timeout yoki subprocess xatolik bo'lsa fallback ishlayotganligi."""
    dummy_appimage = tmp_path / "Broken.AppImage"
    dummy_appimage.write_text("broken")

    def mock_run_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=15)

    with mock.patch("subprocess.run", side_effect=mock_run_timeout):
        metadata = extract_appimage_metadata(str(dummy_appimage))

    assert metadata["Name"] == "Broken"
    assert metadata["Icon"] == "application-x-executable"
    assert metadata["Comment"] == ""


def test_remove_outside_appimage_dir_rejected(mock_dirs, tmp_path):
    """APPIMAGE_DIR tashqarisidagi yo'l berilsa o'chirish rad etilishi kerak."""
    app_dir, desk_dir, icon_dir = mock_dirs

    app_dir.mkdir(parents=True)
    
    # Tizim tashqarisidagi (xavfli) fayl simulatsiyasi
    dangerous_file = tmp_path / "system_file.so"
    dangerous_file.write_text("important")
    
    app = AppImageApp(
        name="HackApp",
        file_path=str(dangerous_file),
        desktop_path="",
        icon_path="",
        size_bytes=100
    )
    
    success, message = remove_appimage(app)
    
    assert success is False
    assert "ruxsat etilmagan joyda, o'chirish rad etildi" in message
    assert dangerous_file.exists()


def test_import_duplicate_filename(mock_dirs, tmp_path):
    """Bir xil nomli fayl allaqachon bo'lsa import rad etilishi."""
    app_dir, desk_dir, icon_dir = mock_dirs
    app_dir.mkdir(parents=True)
    
    existing_file = app_dir / "TestApp.AppImage"
    existing_file.write_text("old")
    
    source_file = tmp_path / "TestApp.AppImage"
    source_file.write_text("new")
    
    success, message, app = import_appimage(str(source_file))
    
    assert success is False
    assert "allaqachon mavjud" in message
    assert app is None
