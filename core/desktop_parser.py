"""
.desktop fayllarni o'qish uchun yordamchi modul.
XDG Desktop Entry formatini to'liq INI parseri bilan o'qish muammoli
bo'lishi mumkin (dublikat kalitlar, izohlar), shuning uchun soddaroq
qo'lda parser ishlatamiz.
"""

import os


def parse_desktop_entry(path: str) -> dict:
    """[Desktop Entry] bo'limidagi key=value juftliklarini dict qilib qaytaradi."""
    entry = {}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            in_section = False
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("["):
                    in_section = line == "[Desktop Entry]"
                    continue
                if in_section and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    if key not in entry:
                        entry[key] = value.strip()
    except OSError:
        return {}
    return entry


def find_desktop_files(directories: list) -> list:
    """Berilgan papkalardan barcha .desktop fayl yo'llarini topadi."""
    found = []
    for directory in directories:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            if fname.endswith(".desktop"):
                found.append(os.path.join(directory, fname))
    return found
