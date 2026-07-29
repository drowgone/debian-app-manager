import os
import tarfile
import zipfile
from unittest import mock

import pytest

from core.installer import install_file


def _make_dummy_deb(path: str) -> None:
    with open(path, "wb") as f:
        f.write(b"!<arch>\n")


def _mock_popen(return_code: int = 0, lines: list[str] | None = None):
    """subprocess.Popen ni mock qilish uchun yordamchi."""
    lines = lines or []

    class MockStdout:
        def __init__(self, output_lines: list[str]) -> None:
            self._lines = list(output_lines)
            self._index = 0

        def readline(self) -> str:
            if self._index < len(self._lines):
                line = self._lines[self._index]
                self._index += 1
                return line if line.endswith("\n") else line + "\n"
            return ""

        def close(self) -> None:
            pass

    mock_process = mock.Mock()
    mock_process.stdout = MockStdout(lines)
    mock_process.wait.return_value = return_code
    return mock_process


def test_install_file_not_found():
    success, message = install_file("/tmp/nonexistent-package.deb")
    assert success is False
    assert "Fayl topilmadi" in message


def test_install_file_unsupported_format(tmp_path):
    bad_file = tmp_path / "package.rpm"
    bad_file.write_text("rpm")
    success, message = install_file(str(bad_file))
    assert success is False
    assert "Qo'llab-quvvatlanmaydigan" in message


def test_install_deb_success(tmp_path):
    deb_file = tmp_path / "app.deb"
    _make_dummy_deb(str(deb_file))

    with mock.patch("core.installer.subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen(return_code=0)
        success, message = install_file(str(deb_file))

    assert success is True
    assert "1 ta .deb paketi" in message
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert cmd[:4] == ["pkexec", "apt-get", "install", "--yes"]
    assert os.path.abspath(str(deb_file)) in cmd


def test_install_deb_user_cancelled(tmp_path):
    deb_file = tmp_path / "app.deb"
    _make_dummy_deb(str(deb_file))

    with mock.patch("core.installer.subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen(return_code=126, lines=["dismissed"])
        success, message = install_file(str(deb_file))

    assert success is False
    assert "bekor qildi" in message


def test_install_multiple_debs_single_apt_call(tmp_path):
    deb1 = tmp_path / "app.deb"
    deb2 = tmp_path / "lib-app.deb"
    _make_dummy_deb(str(deb1))
    _make_dummy_deb(str(deb2))

    with mock.patch("core.installer.subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen(return_code=0)
        from core.installer import _install_deb_files
        success, message = _install_deb_files([str(deb1), str(deb2)])

    assert success is True
    assert "2 ta .deb paketi" in message
    cmd = mock_popen.call_args[0][0]
    assert cmd[:4] == ["pkexec", "apt-get", "install", "--yes"]
    assert os.path.abspath(str(deb1)) in cmd
    assert os.path.abspath(str(deb2)) in cmd


def test_install_from_zip_archive(tmp_path):
    deb1 = tmp_path / "pkg1.deb"
    deb2 = tmp_path / "nested" / "pkg2.deb"
    _make_dummy_deb(str(deb1))
    os.makedirs(deb2.parent)
    _make_dummy_deb(str(deb2))

    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(deb1, "pkg1.deb")
        zf.write(deb2, "nested/pkg2.deb")

    with mock.patch("core.installer._install_deb_files") as mock_install:
        mock_install.return_value = (True, "ok")
        success, message = install_file(str(archive))

    assert success is True
    mock_install.assert_called_once()
    installed = mock_install.call_args[0][0]
    assert len(installed) == 2
    assert any(p.endswith("pkg1.deb") for p in installed)
    assert any(p.endswith("pkg2.deb") for p in installed)


def test_install_from_tar_xz_archive(tmp_path):
    deb_file = tmp_path / "app.deb"
    _make_dummy_deb(str(deb_file))

    archive = tmp_path / "bundle.tar.xz"
    with tarfile.open(archive, "w:xz") as tf:
        tf.add(deb_file, arcname="app.deb")

    with mock.patch("core.installer._install_deb_files") as mock_install:
        mock_install.return_value = (True, "ok")
        success, message = install_file(str(archive))

    assert success is True
    installed = mock_install.call_args[0][0]
    assert len(installed) == 1
    assert installed[0].endswith("app.deb")


def test_install_from_tar_gz_archive(tmp_path):
    deb_file = tmp_path / "app.deb"
    _make_dummy_deb(str(deb_file))

    archive = tmp_path / "bundle.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(deb_file, arcname="packages/app.deb")

    with mock.patch("core.installer._install_deb_files") as mock_install:
        mock_install.return_value = (True, "ok")
        success, message = install_file(str(archive))

    assert success is True
    installed = mock_install.call_args[0][0]
    assert len(installed) == 1


def test_install_archive_without_deb_files(tmp_path):
    archive = tmp_path / "empty.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("readme.txt", "no packages here")

    success, message = install_file(str(archive))
    assert success is False
    assert "hech qanday .deb fayl topilmadi" in message


def test_install_archive_rejects_path_traversal(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.deb", "bad")

    success, message = install_file(str(archive))
    assert success is False
    assert "Arxivni ochishda xatolik" in message


def test_install_appimage_delegates(tmp_path):
    appimage = tmp_path / "Test.AppImage"
    appimage.write_text("appimage")

    with mock.patch("core.appimage_manager.import_appimage") as mock_import:
        mock_import.return_value = (True, "imported", None)
        success, message = install_file(str(appimage))

    assert success is True
    assert message == "imported"
    mock_import.assert_called_once_with(str(appimage))


def test_install_file_emits_progress_callbacks(tmp_path):
    deb_file = tmp_path / "app.deb"
    _make_dummy_deb(str(deb_file))
    progress_messages: list[str] = []
    log_messages: list[str] = []

    with mock.patch("core.installer.subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen(return_code=0)
        install_file(
            str(deb_file),
            log_callback=log_messages.append,
            progress_callback=progress_messages.append,
        )

    assert any(".deb paketi o'rnatilmoqda" in msg for msg in progress_messages)
    assert any("$ pkexec apt-get install" in msg for msg in log_messages)
