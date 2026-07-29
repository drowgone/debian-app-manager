"""Dasturlarni ishga tushirish."""

from __future__ import annotations

import os
import re
import subprocess

from core.scanner import App

_FIELD_CODE_RE = re.compile(r"%[fFuUdDnNiIcCkKvVmM]")


def _clean_exec_line(exec_line: str) -> str:
    return _FIELD_CODE_RE.sub("", exec_line).strip()


def launch_app(app: App) -> tuple[bool, str]:
    """Dasturni ishga tushiradi. (success, message) juftligini qaytaradi."""
    if app.desktop_path and os.path.isfile(app.desktop_path):
        desktop_id = os.path.basename(app.desktop_path)
        if desktop_id.endswith(".desktop"):
            desktop_id = desktop_id[:-8]

        for cmd in (
            ["gtk-launch", desktop_id],
            ["gio", "launch", app.desktop_path],
        ):
            try:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return True, ""
            except FileNotFoundError:
                continue
            except OSError as exc:
                return False, str(exc)

    if app.exec_line:
        cleaned = _clean_exec_line(app.exec_line)
        if not cleaned:
            return False, "Ishga tushirish buyrug'i bo'sh"
        try:
            subprocess.Popen(
                cleaned,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True, ""
        except OSError as exc:
            return False, str(exc)

    return False, "Ishga tushirish uchun ma'lumot topilmadi"
