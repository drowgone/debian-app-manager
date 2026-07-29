"""
AppImage fayllarni boshqarish moduli.

Import qilish, metadata extraction, skanerlash va xavfsiz o'chirish.
AppImage — bu o'z ichiga hamma narsani olib yuruvchi yagona executable fayl.
Bu modul ularni ~/Applications papkasida markazlashtirib boshqaradi.
"""

import os
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass

from core.desktop_parser import parse_desktop_entry

# ── Konstantalar ──────────────────────────────────────────────────────────

APPIMAGE_DIR = os.path.expanduser("~/Applications")
ICON_CACHE_DIR = os.path.expanduser("~/.local/share/icons/appimagekit")
DESKTOP_DIR = os.path.expanduser("~/.local/share/applications")


@dataclass
class AppImageApp:
    """Bitta AppImage dasturni ifodalovchi ma'lumot tuzilmasi."""
    name: str
    file_path: str
    desktop_path: str
    icon_path: str | None
    size_bytes: int


def is_appimage_managed(desktop_entry: dict) -> bool:
    """Desktop entry AppImage boshqaruvi ostida ekanligini tekshiradi."""
    return desktop_entry.get("X-AppImage-Managed", "").lower() == "true"


def scan_appimage_folder() -> list[AppImageApp]:
    """
    APPIMAGE_DIR ichidagi barcha .AppImage fayllarni topadi.
    Har biri uchun mos .desktop fayl mavjudligini tekshiradi.
    """
    apps: list[AppImageApp] = []
    if not os.path.isdir(APPIMAGE_DIR):
        return apps

    for filename in os.listdir(APPIMAGE_DIR):
        if not filename.lower().endswith(".appimage"):
            continue
        file_path = os.path.join(APPIMAGE_DIR, filename)
        if not os.path.isfile(file_path):
            continue

        # Hajmni olish
        try:
            size_bytes = os.path.getsize(file_path)
        except OSError:
            size_bytes = 0

        # Mos .desktop faylni qidirish
        base_name = os.path.splitext(filename)[0]
        desktop_name = f"appimage-{base_name}.desktop"
        desktop_path = os.path.join(DESKTOP_DIR, desktop_name)

        # Ikonkani qidirish
        icon_path = None
        if os.path.isdir(ICON_CACHE_DIR):
            for icon_file in os.listdir(ICON_CACHE_DIR):
                if icon_file.startswith(base_name):
                    icon_path = os.path.join(ICON_CACHE_DIR, icon_file)
                    break

        apps.append(AppImageApp(
            name=base_name,
            file_path=file_path,
            desktop_path=desktop_path if os.path.isfile(desktop_path) else "",
            icon_path=icon_path,
            size_bytes=size_bytes,
        ))

    return apps


def extract_appimage_metadata(appimage_path: str) -> dict:
    """
    AppImage ichidan metadata (nom, ikonka, izoh) ni chiqarib oladi.

    --appimage-extract buyrug'i orqali squashfs-root papkasiga ochadi,
    .desktop faylni o'qiydi va ikonkani ICON_CACHE_DIR ga nusxalaydi.

    Xatolik yuz bersa graceful fallback: fayl nomini Name sifatida qaytaradi.
    """
    fallback_name = os.path.splitext(os.path.basename(appimage_path))[0]
    fallback = {
        "Name": fallback_name,
        "Icon": "application-x-executable",
        "Comment": "",
    }

    # Bajarilish huquqini tekshirish va qo'yish
    try:
        current_mode = os.stat(appimage_path).st_mode
        if not (current_mode & stat.S_IXUSR):
            os.chmod(appimage_path, current_mode | stat.S_IXUSR)
    except OSError:
        return fallback

    tmp_dir = tempfile.mkdtemp(prefix="appimage_extract_")
    try:
        # squashfs-root ga extraction
        result = subprocess.run(
            [appimage_path, "--appimage-extract"],
            cwd=tmp_dir,
            capture_output=True,
            text=True,
            timeout=15,
        )

        squashfs_root = os.path.join(tmp_dir, "squashfs-root")
        if result.returncode != 0 or not os.path.isdir(squashfs_root):
            return fallback

        # .desktop faylni topish
        desktop_file = None
        for f in os.listdir(squashfs_root):
            if f.endswith(".desktop"):
                desktop_file = os.path.join(squashfs_root, f)
                break

        if not desktop_file:
            return fallback

        entry = parse_desktop_entry(desktop_file)
        if not entry:
            return fallback

        name = entry.get("Name", fallback_name)
        icon_name = entry.get("Icon", "")
        comment = entry.get("Comment", "")

        # Ikonkani topish va nusxalash
        icon_path = "application-x-executable"
        if icon_name:
            # squashfs-root ichidan ikonkani qidirish
            found_icon = _find_icon_in_dir(squashfs_root, icon_name)
            if found_icon:
                try:
                    os.makedirs(ICON_CACHE_DIR, exist_ok=True)
                    ext = os.path.splitext(found_icon)[1]
                    dest_icon = os.path.join(
                        ICON_CACHE_DIR,
                        f"{fallback_name}{ext}",
                    )
                    shutil.copy2(found_icon, dest_icon)
                    icon_path = dest_icon
                except OSError:
                    icon_path = "application-x-executable"

        return {
            "Name": name,
            "Icon": icon_path,
            "Comment": comment,
        }

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return fallback
    finally:
        # Vaqtinchalik papkani har doim tozalash
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _find_icon_in_dir(root_dir: str, icon_name: str) -> str | None:
    """squashfs-root ichidan ikonka faylini topadi."""
    # Avval to'g'ridan-to'g'ri
    for ext in (".png", ".svg", ".xpm", ".ico"):
        candidate = os.path.join(root_dir, icon_name + ext)
        if os.path.isfile(candidate):
            return candidate
        # .DirIcon ham bo'lishi mumkin
        candidate = os.path.join(root_dir, icon_name)
        if os.path.isfile(candidate):
            return candidate

    # Rekursiv qidirish (faqat birinchi topilganini qaytarish)
    for dirpath, _dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            base = os.path.splitext(fname)[0]
            if base == icon_name and fname.lower().endswith(
                (".png", ".svg", ".xpm", ".ico")
            ):
                return os.path.join(dirpath, fname)
    return None


def import_appimage(source_path: str) -> tuple[bool, str, AppImageApp | None]:
    """
    AppImage faylni import qiladi:
    1. Faylni ~/Applications ga nusxalaydi
    2. Metadata ni chiqarib oladi
    3. .desktop fayl yaratadi

    Args:
        source_path: Import qilinadigan .AppImage faylning to'liq yo'li.

    Returns:
        (success, message, AppImageApp | None)
    """
    # Manba fayl tekshiruvi
    if not source_path or not os.path.isfile(source_path):
        return False, "Fayl topilmadi yoki yo'l noto'g'ri.", None

    # Symlink tekshiruvi — faqat oddiy fayllar qabul qilinadi
    if os.path.islink(source_path):
        return False, "Xavfsizlik: symlink fayllarni import qilish taqiqlangan.", None

    filename = os.path.basename(source_path)
    if not filename.lower().endswith(".appimage"):
        return False, "Faqat .AppImage fayllarni import qilish mumkin.", None

    # Maqsad papkani yaratish
    os.makedirs(APPIMAGE_DIR, exist_ok=True)

    dest_path = os.path.join(APPIMAGE_DIR, filename)

    # Agar shu nomda fayl mavjud bo'lsa
    if os.path.exists(dest_path):
        return (
            False,
            f"'{filename}' nomli AppImage allaqachon mavjud. "
            f"Iltimos, faylni qayta nomlang yoki avval mavjudini o'chiring.",
            None,
        )

    try:
        # Faylni nusxalash
        shutil.copy2(source_path, dest_path)
        # Bajarilish huquqini qo'yish
        os.chmod(dest_path, 0o755)
    except (OSError, shutil.Error) as e:
        # Nusxalashda xato bo'lsa, yarim qolgan faylni tozalash
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False, f"Faylni nusxalashda xatolik: {e}", None

    # Metadata extraction
    metadata = extract_appimage_metadata(dest_path)

    name = metadata.get("Name", os.path.splitext(filename)[0])
    icon = metadata.get("Icon", "application-x-executable")
    comment = metadata.get("Comment", "")

    # .desktop fayl yaratish
    base_name = os.path.splitext(filename)[0]
    desktop_name = f"appimage-{base_name}.desktop"
    desktop_path = os.path.join(DESKTOP_DIR, desktop_name)

    desktop_content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={name}\n"
        f'Exec="{dest_path}" %U\n'
        f"Icon={icon}\n"
        f"Comment={comment}\n"
        "Categories=Utility;\n"
        "X-AppImage-Managed=true\n"
        "Terminal=false\n"
    )

    try:
        os.makedirs(DESKTOP_DIR, exist_ok=True)
        with open(desktop_path, "w", encoding="utf-8") as f:
            f.write(desktop_content)
    except OSError as e:
        return False, f".desktop fayl yaratishda xatolik: {e}", None

    # Hajmni olish
    try:
        size_bytes = os.path.getsize(dest_path)
    except OSError:
        size_bytes = 0

    icon_path: str | None = icon if icon != "application-x-executable" and os.path.isfile(icon) else None

    app = AppImageApp(
        name=name,
        file_path=dest_path,
        desktop_path=desktop_path,
        icon_path=icon_path,
        size_bytes=size_bytes,
    )

    return True, f"'{name}' muvaffaqiyatli import qilindi!", app


def remove_appimage(app: AppImageApp) -> tuple[bool, str]:
    """
    AppImage dasturni to'liq o'chiradi:
    - .AppImage fayl
    - .desktop fayl
    - Ikonka fayl

    Xavfsizlik: har bir faylning realpath'i tegishli papka ichida
    ekanligini tekshiradi.

    Returns:
        (success, message)
    """
    errors: list[str] = []

    # 1. AppImage faylni o'chirish
    if app.file_path:
        from core.remover import _is_safe_path
        real_file = os.path.realpath(app.file_path)
        if not _is_safe_path(real_file):
            return (
                False,
                f"Xavfsizlik: '{real_file}' — tizim papkasi yoki ruxsat etilmagan joyda, "
                f"o'chirish rad etildi.",
            )
        try:
            os.remove(real_file)
        except FileNotFoundError:
            pass  # Allaqachon o'chirilgan
        except OSError as e:
            errors.append(f"AppImage faylni o'chirishda xatolik: {e}")

    # 2. .desktop faylni o'chirish
    if app.desktop_path:
        real_desktop = os.path.realpath(app.desktop_path)
        real_desktop_dir = os.path.realpath(DESKTOP_DIR)
        if real_desktop.startswith(real_desktop_dir + os.sep):
            try:
                os.remove(real_desktop)
            except FileNotFoundError:
                pass
            except OSError as e:
                errors.append(f".desktop faylni o'chirishda xatolik: {e}")

    # 3. Ikonkani o'chirish
    if app.icon_path:
        real_icon = os.path.realpath(app.icon_path)
        real_icon_dir = os.path.realpath(ICON_CACHE_DIR)
        if real_icon.startswith(real_icon_dir + os.sep):
            try:
                os.remove(real_icon)
            except FileNotFoundError:
                pass
            except OSError as e:
                errors.append(f"Ikonkani o'chirishda xatolik: {e}")

    if errors:
        return False, "; ".join(errors)

    return True, f"'{app.name}' AppImage to'liq o'chirildi."
