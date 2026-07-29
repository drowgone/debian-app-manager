"""
Tizim va tashqi dasturlarni yangilash moduli.
APT, Snap va Flatpak uchun yangilanishlarni tekshirish va o'rnatish funksiyalari.
"""

import subprocess

def get_apt_updates() -> dict[str, str]:
    """
    APT orqali qaysi paketlarga yangilanish kelganini tekshiradi.
    Qaytaradi: {paket_nomi: yangi_versiya_va_malumot}
    """
    updates = {}
    try:
        result = subprocess.run(
            ["apt", "list", "--upgradable"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "/" in line and "[upgradable from:" in line:
                    parts = line.split("/")
                    package = parts[0].strip()
                    version_part = line.split(" ", 2)[1] if len(line.split(" ")) > 1 else ""
                    
                    # Size malumotini olish (apt-cache show)
                    size_info = ""
                    try:
                        show_res = subprocess.run(
                            ["apt-cache", "show", package],
                            capture_output=True, text=True, timeout=5
                        )
                        size_bytes = 0
                        installed_kb = 0
                        for s_line in show_res.stdout.splitlines():
                            if s_line.startswith("Size: "):
                                size_bytes = int(s_line.split(" ")[1])
                            elif s_line.startswith("Installed-Size: "):
                                installed_kb = int(s_line.split(" ")[1])
                        if size_bytes or installed_kb:
                            mb_dl = size_bytes / (1024*1024)
                            mb_inst = installed_kb / 1024
                            size_info = f" (Yuklash: {mb_dl:.1f} MB, Joy: {mb_inst:.1f} MB)"
                    except Exception:
                        pass
                        
                    updates[package] = version_part + size_info
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return updates

def get_snap_updates() -> dict[str, str]:
    """
    Snap orqali qaysi dasturlarga yangilanish kelganini tekshiradi.
    Qaytaradi: {snap_nomi: yangi_versiya}
    """
    updates = {}
    try:
        # snap refresh --list
        result = subprocess.run(
            ["snap", "refresh", "--list"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            if len(lines) > 1:
                # Birinchi qator sarlavha: Name  Version  Rev  ...
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        updates[parts[0]] = parts[1]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return updates

def get_flatpak_updates() -> dict[str, str]:
    """
    Flatpak orqali qaysi dasturlarga yangilanish kelganini tekshiradi.
    Qaytaradi: {app_id: yangi_versiya}
    """
    updates = {}
    try:
        # flatpak remote-ls --updates --app --columns=application,version
        result = subprocess.run(
            ["flatpak", "remote-ls", "--updates", "--app", "--columns=application,version"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    app_id = parts[0].strip()
                    version = parts[1].strip()
                    updates[app_id] = version
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return updates

def update_apt_package(package_name: str) -> bool:
    """pkexec orqali apt paketini yangilaydi."""
    try:
        result = subprocess.run(
            ["pkexec", "apt-get", "install", "--only-upgrade", "-y", package_name],
            capture_output=True, timeout=300
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def update_snap_package(snap_name: str) -> bool:
    """pkexec orqali snap paketini yangilaydi."""
    try:
        result = subprocess.run(
            ["pkexec", "snap", "refresh", snap_name],
            capture_output=True, timeout=300
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def update_flatpak_app(app_id: str) -> bool:
    """flatpak dasturini yangilaydi."""
    try:
        result = subprocess.run(
            ["flatpak", "update", "--noninteractive", "-y", app_id],
            capture_output=True, timeout=300
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
