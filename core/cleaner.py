"""
Tizimni tozalash operatsiyalarini bajaruvchi modul.
APT keshi, qoldiqlari, Flatpak keraksizlari va systemd loglari uchun.
"""

import subprocess
from typing import Callable

def _run_and_stream(cmd: list[str], log_callback: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Buyruqni ishga tushirib, natijani qatorma-qator qaytaradi."""
    if log_callback:
        log_callback(f"$ {' '.join(cmd)}\n")
        
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        output_lines = []
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                line = line.strip()
                if line:
                    if log_callback:
                        log_callback(line + "\n")
                    output_lines.append(line)
        
        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            return True, "Muvaffaqiyatli yakunlandi."
        else:
            err_msg = "Xatolik yuz berdi."
            if output_lines:
                err_msg = output_lines[-1]
            return False, err_msg
    except Exception as e:
        if log_callback:
            log_callback(f"Xatolik: {e}\n")
        return False, str(e)


def clean_apt_cache(log_callback: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """APT keshini tozalaydi (apt-get clean)."""
    return _run_and_stream(["pkexec", "apt-get", "clean"], log_callback)


def clean_apt_autoremove(log_callback: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Keraksiz bog'liqliklarni o'chiradi (apt-get autoremove -y)."""
    return _run_and_stream(["pkexec", "apt-get", "autoremove", "-y"], log_callback)


def clean_apt_leftovers(log_callback: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """O'chirilgan (rc) paketlar qoldiqlarini tozalaydi (dpkg --purge)."""
    try:
        if log_callback:
            log_callback("Qoldiq konfiguratsiya fayllarini qidirish...\n")
            
        res_list = subprocess.run(
            ["dpkg", "-l"],
            capture_output=True, text=True
        )
        if res_list.returncode != 0:
            if log_callback:
                log_callback("Paketlar ro'yxatini olishda xatolik yuz berdi.\n")
            return False, "Paketlar ro'yxatini olishda xatolik."
        
        leftover_packages = []
        for line in res_list.stdout.splitlines():
            if line.startswith("rc "):
                parts = line.split()
                if len(parts) >= 2:
                    leftover_packages.append(parts[1])
        
        if not leftover_packages:
            if log_callback:
                log_callback("Qoldiq konfiguratsiya fayllari topilmadi.\n")
            return True, "Qoldiq konfiguratsiya fayllari topilmadi."

        if log_callback:
            log_callback(f"{len(leftover_packages)} ta qoldiq fayl topildi. O'chirilmoqda...\n")

        cmd = ["pkexec", "apt-get", "purge", "-y"] + leftover_packages
        return _run_and_stream(cmd, log_callback)
    except Exception as e:
        if log_callback:
            log_callback(f"Xatolik: {e}\n")
        return False, str(e)


def clean_flatpak_unused(log_callback: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Ishlatilmayotgan Flatpak kutubxonalarini o'chiradi."""
    return _run_and_stream(["flatpak", "uninstall", "--unused", "-y"], log_callback)


def clean_journal_logs(log_callback: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """Tizim loglarini oxirgi 3 kunga qisqartiradi."""
    return _run_and_stream(["pkexec", "journalctl", "--vacuum-time=3d"], log_callback)
