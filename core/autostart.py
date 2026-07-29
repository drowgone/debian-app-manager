"""
Autorun (avtoishga tushish) yozuvlarini o'qish, yoqish/o'chirish
va o'chirish moduli.

XDG standartiga rioya qiladi:
  - Foydalanuvchi fayllari: ~/.config/autostart/
  - Tizim fayllari: /etc/xdg/autostart/ (faqat o'qish)
  - Tizim fayllarini o'zgartirish uchun ~/.config/autostart/ ga override yoziladi.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass

from core.desktop_parser import find_desktop_files, parse_desktop_entry


USER_AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
SYSTEM_AUTOSTART_DIR = "/etc/xdg/autostart"


@dataclass
class AutostartEntry:
    """Bitta avtoishga tushish yozuvini ifodalovchi ma'lumot tuzilmasi."""
    name: str
    desktop_path: str       # Haqiqiy fayl joylashuvi
    filename: str           # Fayl nomi (masalan, "slack.desktop")
    enabled: bool           # Yoqilgan yoki o'chirilgan
    is_system: bool         # Tizim darajasidagi fayl yoki foydalanuvchi
    icon: str
    comment: str
    boot_time: str = ""     # systemd-analyze blame dan olingan yuklanish vaqti


def _is_entry_enabled(entry: dict) -> bool:
    """Desktop entry yoqilgan yoki o'chirilganligini aniqlaydi."""
    # Hidden=true — o'chirilgan
    if entry.get("Hidden", "").lower() == "true":
        return False
    # X-GNOME-Autostart-enabled=false — o'chirilgan
    if entry.get("X-GNOME-Autostart-enabled", "").lower() == "false":
        return False
    return True


def get_systemd_boot_info() -> tuple[str, list[tuple[str, str]]]:
    """
    Tizimning umumiy yuklanish vaqtini va top eng sekin tizim xizmatlarini qaytaradi.
    Qaytaradi: (overall_time_str, [(service_name, time_str), ...])
    """
    overall_time = ""
    top_services = []
    
    # 1. Umumiy vaqt
    try:
        res = subprocess.run(["systemd-analyze"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            if lines:
                overall_time = lines[0].replace("Startup finished in ", "").strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 2. Top xizmatlar (tizimni eng ko'p sekinlashtiradigan 5 ta)
    try:
        res = subprocess.run(["systemd-analyze", "blame"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                parts = line.strip().split(" ", 1)
                if len(parts) == 2:
                    top_services.append((parts[1].strip(), parts[0].strip()))
                    if len(top_services) >= 5:
                        break
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return overall_time, top_services


def _get_systemd_blame_dict() -> dict[str, str]:
    """systemd-analyze blame dan (tizim va user) barcha vaqtlarni yig'adi."""
    blame = {}
    for cmd in [["systemd-analyze", "blame"], ["systemd-analyze", "--user", "blame"]]:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    parts = line.strip().split(" ", 1)
                    if len(parts) == 2:
                        blame[parts[1].strip()] = parts[0].strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return blame


def _get_boot_time(filename: str, blame_data: dict[str, str]) -> str:
    app_base = filename.replace(".desktop", "")
    possible_services = [
        f"app-{app_base}@autostart.service",
        f"app-gnome-{app_base}-autostart.service",
        f"app-{app_base}.service",
        f"{app_base}.service"
    ]
    for srv in possible_services:
        if srv in blame_data:
            return blame_data[srv]
    return ""


def get_autostart_entries() -> list[AutostartEntry]:
    """
    Barcha avtoishga tushish yozuvlarini o'qiydi.
    Foydalanuvchi fayllari tizim fayllaridan ustun turadi (override).
    """
    entries: list[AutostartEntry] = []
    seen_filenames: set[str] = set()
    blame_data = _get_systemd_blame_dict()

    # 1) Avval foydalanuvchi fayllari (ustun turadi)
    user_files = find_desktop_files([USER_AUTOSTART_DIR])
    for path in user_files:
        entry = parse_desktop_entry(path)
        if not entry:
            continue

        filename = os.path.basename(path)
        seen_filenames.add(filename)

        # Agar shu nom bilan /etc/xdg/autostart/ da ham bo'lsa, bu override
        system_counterpart = os.path.join(SYSTEM_AUTOSTART_DIR, filename)
        is_system = os.path.isfile(system_counterpart)

        name = entry.get("Name", filename.replace(".desktop", ""))
        enabled = _is_entry_enabled(entry)
        icon = entry.get("Icon", "")
        comment = entry.get("Comment", "")

        entries.append(AutostartEntry(
            name=name,
            desktop_path=path,
            filename=filename,
            enabled=enabled,
            is_system=is_system,
            icon=icon,
            comment=comment,
            boot_time=_get_boot_time(filename, blame_data),
        ))

    # 2) Tizim fayllari — foydalanuvchi tomonidan override qilinmaganlarini qo'shish
    system_files = find_desktop_files([SYSTEM_AUTOSTART_DIR])
    for path in system_files:
        filename = os.path.basename(path)
        if filename in seen_filenames:
            continue  # Foydalanuvchi allaqachon override qilgan

        entry = parse_desktop_entry(path)
        if not entry:
            continue

        name = entry.get("Name", filename.replace(".desktop", ""))
        icon = entry.get("Icon", "")
        comment = entry.get("Comment", "")

        entries.append(AutostartEntry(
            name=name,
            desktop_path=path,
            filename=filename,
            enabled=_is_entry_enabled(entry),
            is_system=True,
            icon=icon,
            comment=comment,
            boot_time=_get_boot_time(filename, blame_data),
        ))

    # Nom bo'yicha tartiblash
    entries.sort(key=lambda x: x.name.lower())
    return entries


def _ensure_user_autostart_dir() -> None:
    """~/.config/autostart/ papkasi mavjudligini ta'minlaydi."""
    os.makedirs(USER_AUTOSTART_DIR, exist_ok=True)


def _write_override_file(filename: str, hidden: bool) -> str:
    """
    Tizim autostart faylini override qilish uchun
    ~/.config/autostart/ ga fayl yozadi.
    """
    _ensure_user_autostart_dir()
    override_path = os.path.join(USER_AUTOSTART_DIR, filename)

    system_path = os.path.join(SYSTEM_AUTOSTART_DIR, filename)
    if os.path.isfile(system_path):
        # Tizim faylini nusxalab, o'zgartirish
        entry = parse_desktop_entry(system_path)
    else:
        entry = {}

    # Override fayl yozish
    with open(override_path, "w", encoding="utf-8") as f:
        f.write("[Desktop Entry]\n")
        # Asl fayl qiymatlarini saqlash
        for key in ("Type", "Name", "Exec", "Icon", "Comment"):
            if key in entry:
                f.write(f"{key}={entry[key]}\n")
        # Yoqish/o'chirish
        hidden_str = "true" if hidden else "false"
        f.write(f"Hidden={hidden_str}\n")
        f.write(f"X-GNOME-Autostart-enabled={'false' if hidden else 'true'}\n")

    return override_path


def toggle_autostart(entry: AutostartEntry, enable: bool) -> tuple[bool, str]:
    """
    Avtoishga tushish yozuvini yoqish yoki o'chirish.

    Tizim fayllari uchun ~/.config/autostart/ ga override yoziladi.
    Foydalanuvchi fayllari to'g'ridan-to'g'ri tahrirlanadi.
    """
    try:
        user_path = os.path.join(USER_AUTOSTART_DIR, entry.filename)
        status_word = "yoqildi" if enable else "o'chirildi"

        if entry.is_system and not os.path.isfile(user_path):
            # Tizim fayli uchun override yaratish
            _write_override_file(entry.filename, hidden=not enable)
            return True, f"'{entry.name}' {status_word} (override yaratildi)"

        # Foydalanuvchi faylini tahrirlash
        if os.path.isfile(user_path):
            _update_desktop_file_status(user_path, enable)
            return True, f"'{entry.name}' {status_word}"

        # Agar fayl boshqa joyda bo'lsa va foydalanuvchi papkasida yo'q
        if entry.is_system:
            _write_override_file(entry.filename, hidden=not enable)
            return True, f"'{entry.name}' {status_word} (override yaratildi)"

        return False, f"'{entry.name}' fayli topilmadi"
    except OSError as e:
        return False, f"Xatolik: {e}"


def _update_desktop_file_status(path: str, enable: bool) -> None:
    """Desktop faylda Hidden va X-GNOME-Autostart-enabled qiymatlarini yangilaydi."""
    lines: list[str] = []
    hidden_set = False
    autostart_set = False

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            original_lines = f.readlines()
    except OSError:
        original_lines = []

    in_section = False
    for line in original_lines:
        stripped = line.strip()

        if stripped.startswith("["):
            in_section = stripped == "[Desktop Entry]"
            lines.append(line)
            continue

        if in_section:
            if stripped.startswith("Hidden="):
                lines.append(f"Hidden={'false' if enable else 'true'}\n")
                hidden_set = True
                continue
            if stripped.startswith("X-GNOME-Autostart-enabled="):
                lines.append(f"X-GNOME-Autostart-enabled={'true' if enable else 'false'}\n")
                autostart_set = True
                continue

        lines.append(line)

    # Agar kalitlar topilmagan bo'lsa, [Desktop Entry] bo'limiga qo'shish
    if not hidden_set or not autostart_set:
        result_lines: list[str] = []
        for line in lines:
            result_lines.append(line)
            if line.strip() == "[Desktop Entry]":
                if not hidden_set:
                    result_lines.append(f"Hidden={'false' if enable else 'true'}\n")
                if not autostart_set:
                    result_lines.append(f"X-GNOME-Autostart-enabled={'true' if enable else 'false'}\n")
        lines = result_lines

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def remove_autostart_entry(entry: AutostartEntry) -> tuple[bool, str]:
    """
    Avtoishga tushish yozuvini o'chirish.

    Foydalanuvchi fayli to'g'ridan-to'g'ri o'chiriladi.
    Tizim fayli uchun override bilan yashiriladi.
    """
    try:
        user_path = os.path.join(USER_AUTOSTART_DIR, entry.filename)

        if entry.is_system:
            # Tizim faylini hech qachon o'chirmaymiz!
            # Override orqali yashiramiz
            _write_override_file(entry.filename, hidden=True)
            return True, f"'{entry.name}' tizim darajasida yashirildi (override yaratildi)"

        # Foydalanuvchi faylini o'chirish
        if os.path.isfile(user_path):
            os.remove(user_path)
            return True, f"'{entry.name}' avtoishga tushish ro'yxatidan olib tashlandi"

        # Haqiqiy joylashuvidagi faylni o'chirish (agar ~/.config/autostart/ ichida bo'lsa)
        if os.path.isfile(entry.desktop_path):
            real_path = os.path.realpath(entry.desktop_path)
            # Xavfsizlik: faqat foydalanuvchi papkasidagi fayllarga tegish mumkin
            user_home = os.path.expanduser("~")
            if real_path.startswith(user_home):
                os.remove(entry.desktop_path)
                return True, f"'{entry.name}' avtoishga tushish ro'yxatidan olib tashlandi"
            else:
                # Tizim papkasidagi fayl — override orqali yashirish
                _write_override_file(entry.filename, hidden=True)
                return True, f"'{entry.name}' tizim darajasida yashirildi"

        return False, f"'{entry.name}' fayli topilmadi"
    except OSError as e:
        return False, f"Xatolik: {e}"
