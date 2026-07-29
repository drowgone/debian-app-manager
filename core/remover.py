"""
Dasturlarni manba bo'yicha xavfsiz o'chirish moduli.

Har bir manba (APT, Snap, Flatpak, qo'lda) uchun alohida funksiya.
Root huquqi kerak bo'lsa pkexec orqali (hech qachon sudo emas).
Barcha subprocess chaqiruvlari list shaklida (shell=True siz).
"""

import os
import subprocess


# ── Xavfsiz papkalar — faqat shulardan qo'lda o'chirish mumkin ────────────
_SAFE_MANUAL_PREFIXES = (
    os.path.expanduser("~"),      # Foydalanuvchi uy papkasi
    "/opt/",                       # Uchinchi tomon dasturlar
    "/usr/local/share/applications/",  # Qo'lda qo'shilgan .desktop fayllar
)

# ── Taqiqlangan papkalar — hech qachon o'chirmaslik kerak ─────────────────
_FORBIDDEN_PREFIXES = (
    "/usr/bin/",
    "/usr/lib/",
    "/usr/sbin/",
    "/etc/",
    "/var/lib/dpkg/",
    "/boot/",
)


def _is_safe_path(path: str) -> bool:
    """Fayl yo'li xavfsiz o'chirish uchun mos ekanini tekshiradi."""
    real_path = os.path.realpath(path)  # Symlink'larni hal qilish

    # Taqiqlangan papkalarga tegmaslik
    for prefix in _FORBIDDEN_PREFIXES:
        if real_path.startswith(prefix):
            return False

    # Faqat ruxsat etilgan papkalardan o'chirish
    for prefix in _SAFE_MANUAL_PREFIXES:
        if real_path.startswith(prefix):
            return True

    return False


def remove_apt_package(package_name: str) -> tuple[bool, str]:
    """
    APT paketini pkexec orqali o'chiradi.

    Args:
        package_name: O'chiriladigan paket nomi.

    Returns:
        (success, message) juftligi.
    """
    if not package_name or not package_name.replace("-", "").replace(".", "").replace("+", "").replace(":", "").isalnum():
        return False, f"Noto'g'ri paket nomi: {package_name}"

    try:
        result = subprocess.run(
            ["pkexec", "apt-get", "remove", "--yes", package_name],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            return True, f"'{package_name}' muvaffaqiyatli o'chirildi"
        else:
            stderr = result.stderr.strip()
            if "dismissed" in stderr.lower() or result.returncode == 126:
                return False, "Foydalanuvchi amalni bekor qildi"
            return False, f"O'chirishda xatolik: {stderr or result.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Vaqt tugadi — jarayon juda uzoq davom etdi"
    except FileNotFoundError:
        return False, "pkexec topilmadi — polkit o'rnatilganligini tekshiring"


def remove_snap_package(snap_name: str) -> tuple[bool, str]:
    """
    Snap paketini o'chiradi.

    Args:
        snap_name: O'chiriladigan snap nomi.

    Returns:
        (success, message) juftligi.
    """
    if not snap_name or not snap_name.replace("-", "").replace(".", "").replace("_", "").isalnum():
        return False, f"Noto'g'ri snap nomi: {snap_name}"

    try:
        result = subprocess.run(
            ["snap", "remove", snap_name],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            return True, f"'{snap_name}' snap muvaffaqiyatli o'chirildi"
        else:
            stderr = result.stderr.strip()
            # Snap ba'zan root talab qiladi
            if "access denied" in stderr.lower() or "permission" in stderr.lower():
                result2 = subprocess.run(
                    ["pkexec", "snap", "remove", snap_name],
                    capture_output=True, text=True, timeout=300,
                )
                if result2.returncode == 0:
                    return True, f"'{snap_name}' snap muvaffaqiyatli o'chirildi"
                stderr2 = result2.stderr.strip()
                if result2.returncode == 126:
                    return False, "Foydalanuvchi amalni bekor qildi"
                return False, f"O'chirishda xatolik: {stderr2 or result2.stdout.strip()}"
            return False, f"O'chirishda xatolik: {stderr or result.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Vaqt tugadi — jarayon juda uzoq davom etdi"
    except FileNotFoundError:
        return False, "snap buyrug'i topilmadi — snapd o'rnatilganligini tekshiring"


def remove_flatpak_app(app_id: str) -> tuple[bool, str]:
    """
    Flatpak ilovasini o'chiradi.

    Args:
        app_id: O'chiriladigan flatpak ilova ID'si (masalan, com.example.App).

    Returns:
        (success, message) juftligi.
    """
    if not app_id:
        return False, "Flatpak ilova ID'si bo'sh"

    try:
        result = subprocess.run(
            ["flatpak", "uninstall", "--noninteractive", app_id],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            return True, f"'{app_id}' flatpak muvaffaqiyatli o'chirildi"
        else:
            stderr = result.stderr.strip()
            return False, f"O'chirishda xatolik: {stderr or result.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Vaqt tugadi — jarayon juda uzoq davom etdi"
    except FileNotFoundError:
        return False, "flatpak buyrug'i topilmadi — flatpak o'rnatilganligini tekshiring"


def remove_manual_app(desktop_path: str) -> tuple[bool, str]:
    """
    Qo'lda o'rnatilgan dasturning .desktop faylini o'chiradi.
    Xavfsizlik tekshiruvlari bilan.

    Args:
        desktop_path: O'chiriladigan .desktop fayl yo'li.

    Returns:
        (success, message) juftligi.
    """
    if not desktop_path or not desktop_path.endswith(".desktop"):
        return False, "Noto'g'ri .desktop fayl yo'li"

    real_path = os.path.realpath(desktop_path)

    # Xavfsizlik tekshiruvi
    if not _is_safe_path(real_path):
        return False, f"Xavfsizlik: '{real_path}' tizim papkasida — o'chirish taqiqlangan"

    if not os.path.isfile(real_path):
        return False, f"Fayl topilmadi: {desktop_path}"

    try:
        os.remove(real_path)
        return True, f"'{os.path.basename(desktop_path)}' muvaffaqiyatli o'chirildi"
    except PermissionError:
        # pkexec bilan qayta urinish
        try:
            result = subprocess.run(
                ["pkexec", "rm", real_path],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return True, f"'{os.path.basename(desktop_path)}' muvaffaqiyatli o'chirildi"
            if result.returncode == 126:
                return False, "Foydalanuvchi amalni bekor qildi"
            return False, f"O'chirishda xatolik: {result.stderr.strip()}"
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return False, f"Xatolik: {e}"
    except OSError as e:
        return False, f"Xatolik: {e}"


def get_manual_app_binary(desktop_path: str) -> str | None:
    """
    .desktop fayldan binary yo'lini ajratib oladi.
    Faqat /opt/ yoki foydalanuvchi uy papkasidagi binarylar qaytariladi.
    """
    from core.desktop_parser import parse_desktop_entry

    entry = parse_desktop_entry(desktop_path)
    exec_line = entry.get("Exec", "")
    if not exec_line:
        return None

    # Exec satridan birinchi buyruqni ajratish
    # Exec=env VAR=val /path/to/binary --arg tarzida bo'lishi mumkin
    parts = exec_line.split()
    binary_path = None

    for part in parts:
        if part.startswith("/"):
            binary_path = part
            break
        if "=" in part or part == "env":
            continue
        # Nisbiy yo'l — which bilan topish
        binary_path = part
        break

    if not binary_path or not os.path.isabs(binary_path):
        return None

    real_binary = os.path.realpath(binary_path)

    # Faqat xavfsiz papkalardan
    if _is_safe_path(real_binary):
        return real_binary

    return None
