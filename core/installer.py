"""
Fayldan (AppImage, deb, arxivlar) dasturlarni o'rnatish moduli.
"""

import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from typing import Callable


def install_file(
    file_path: str,
    log_callback: Callable[[str], None] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """
    Kengaytmaga qarab faylni o'rnatish jarayonini boshqaradi.

    Qo'llab-quvvatlanadigan formatlar:
    - .AppImage, .appimage -> core.appimage_manager orqali
    - .deb -> pkexec apt-get install --yes
    - .tar.xz, .tar.gz, .zip -> arxivni ochib ichidagi barcha .deb fayllarni o'rnatadi.
    """
    if not os.path.isfile(file_path):
        return False, f"Fayl topilmadi: {file_path}"

    basename = os.path.basename(file_path)
    ext = file_path.lower()

    if ext.endswith(".appimage"):
        if progress_callback:
            progress_callback(f"AppImage import qilinmoqda: {basename}")
        if log_callback:
            log_callback(f"AppImage fayl: {file_path}\n")
        from core.appimage_manager import import_appimage
        success, msg, _ = import_appimage(file_path)
        if log_callback:
            log_callback(f"{msg}\n")
        return success, msg

    if ext.endswith(".deb"):
        if progress_callback:
            progress_callback(f".deb paketi o'rnatilmoqda: {basename}")
        return _install_deb_files([file_path], log_callback, progress_callback)

    if ext.endswith((".tar.xz", ".tar.gz", ".tar.bz2", ".tar", ".zip")):
        return _install_from_archive(file_path, log_callback, progress_callback)

    return False, f"Qo'llab-quvvatlanmaydigan fayl formati: {basename}"


def _log(log_callback: Callable[[str], None] | None, text: str) -> None:
    if log_callback:
        log_callback(text)


def _progress(
    progress_callback: Callable[[str], None] | None,
    message: str,
) -> None:
    if progress_callback:
        progress_callback(message)


def _run_and_stream(
    cmd: list[str],
    log_callback: Callable[[str], None] | None = None,
    timeout: int = 600,
) -> tuple[int, str]:
    """Buyruqni ishga tushirib, chiqishni qatorma-qator log qiladi."""
    _log(log_callback, f"$ {' '.join(cmd)}\n")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except OSError as e:
        _log(log_callback, f"Jarayonni ishga tushirishda xatolik: {e}\n")
        return -1, str(e)

    output_lines: list[str] = []
    try:
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                line = line.rstrip("\n")
                if line:
                    _log(log_callback, line + "\n")
                    output_lines.append(line)
        process.stdout.close()
        return_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        _log(log_callback, "O'rnatish jarayoni juda uzoq davom etdi (Timeout).\n")
        return -2, "Timeout"
    except FileNotFoundError:
        _log(log_callback, "pkexec buyrug'i topilmadi.\n")
        return -1, "pkexec topilmadi"

    return return_code, "\n".join(output_lines)


def _install_deb_files(
    deb_paths: list[str],
    log_callback: Callable[[str], None] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Bitta yoki bir nechta .deb fayllarni pkexec orqali birdaniga o'rnatadi."""
    if not deb_paths:
        return False, "O'rnatish uchun .deb fayllar berilmadi."

    abs_paths = [os.path.abspath(p) for p in deb_paths]
    for path in abs_paths:
        if not os.path.isfile(path):
            return False, f"Fayl topilmadi: {path}"

    count = len(abs_paths)
    _progress(
        progress_callback,
        f"{count} ta .deb paketi o'rnatilmoqda...",
    )
    for path in abs_paths:
        _log(log_callback, f"  • {os.path.basename(path)}\n")

    cmd = ["pkexec", "apt-get", "install", "--yes", *abs_paths]
    return_code, output = _run_and_stream(cmd, log_callback)

    if return_code == 0:
        msg = f"{count} ta .deb paketi muvaffaqiyatli o'rnatildi."
        _log(log_callback, f"\n✓ {msg}\n")
        return True, msg

    stderr = output.strip()
    if return_code == 126 or "dismissed" in stderr.lower():
        return False, "Foydalanuvchi parolni kiritishni bekor qildi."
    if return_code == -2:
        return False, "O'rnatish jarayoni juda uzoq davom etdi (Timeout)."
    if return_code == -1 and "pkexec" in stderr.lower():
        return False, "pkexec buyrug'i topilmadi. Tizimda polkit o'rnatilganligini tekshiring."
    err_detail = stderr or "Noma'lum xatolik"
    return False, f"O'rnatishda xatolik: {err_detail}"


def _is_safe_member_path(base_dir: str, member_path: str) -> bool:
    """Arxiv a'zosi maqsad papka ichida ekanini tekshiradi (path traversal himoyasi)."""
    base = os.path.abspath(base_dir)
    target = os.path.abspath(os.path.join(base_dir, member_path))
    return target == base or target.startswith(base + os.sep)


def _safe_extract_zip(zip_ref: zipfile.ZipFile, dest_dir: str) -> None:
    for member in zip_ref.infolist():
        if not _is_safe_member_path(dest_dir, member.filename):
            raise zipfile.BadZipFile(f"Xavfli yo'l aniqlandi: {member.filename}")
    zip_ref.extractall(dest_dir)


def _safe_extract_tar(tar_ref: tarfile.TarFile, dest_dir: str) -> None:
    for member in tar_ref.getmembers():
        if not _is_safe_member_path(dest_dir, member.name):
            raise tarfile.TarError(f"Xavfli yo'l aniqlandi: {member.name}")

    extract_kwargs: dict = {}
    if hasattr(tarfile, "data_filter"):
        extract_kwargs["filter"] = "data"
    tar_ref.extractall(dest_dir, **extract_kwargs)


def _find_deb_files(directory: str) -> list[str]:
    deb_files: list[str] = []
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(".deb"):
                deb_files.append(os.path.join(root, filename))
    return sorted(deb_files)


def _install_from_archive(
    archive_path: str,
    log_callback: Callable[[str], None] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Arxivni vaqtinchalik papkaga ochadi va barcha .deb fayllarni o'rnatadi."""
    basename = os.path.basename(archive_path)
    _progress(progress_callback, f"Arxiv ochilmoqda: {basename}")
    _log(log_callback, f"Arxiv: {archive_path}\n")

    tmp_dir = tempfile.mkdtemp(prefix="dam_archive_")
    try:
        try:
            if archive_path.lower().endswith(".zip"):
                _log(log_callback, "ZIP arxiv ochilmoqda...\n")
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    _safe_extract_zip(zip_ref, tmp_dir)
            else:
                _log(log_callback, "TAR arxiv ochilmoqda...\n")
                with tarfile.open(archive_path, "r") as tar_ref:
                    _safe_extract_tar(tar_ref, tmp_dir)
        except (zipfile.BadZipFile, tarfile.TarError, OSError) as e:
            return False, f"Arxivni ochishda xatolik: {e}"

        deb_files = _find_deb_files(tmp_dir)
        if not deb_files:
            return False, (
                f"Arxiv ichidan hech qanday .deb fayl topilmadi: {basename}"
            )

        _log(log_callback, f"{len(deb_files)} ta .deb fayl topildi:\n")
        for deb in deb_files:
            _log(log_callback, f"  • {os.path.basename(deb)}\n")
        _log(log_callback, "\n")

        return _install_deb_files(deb_files, log_callback, progress_callback)
    finally:
        _log(log_callback, "Vaqtinchalik fayllar tozalanmoqda...\n")
        shutil.rmtree(tmp_dir, ignore_errors=True)
