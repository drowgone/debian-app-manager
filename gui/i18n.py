"""Simple runtime translations for the desktop UI reading from locales/ JSON files."""

from __future__ import annotations

import os
import json
from PySide6.QtCore import QSettings


LANGUAGES = {
    "uz": "O'zbek",
    "ru": "Русский",
    "en": "English",
}

DEFAULT_LANGUAGE = "uz"

_settings = QSettings("Donegrow", "DebianAppManager")
_language = _settings.value("language", DEFAULT_LANGUAGE)
if _language not in LANGUAGES:
    _language = DEFAULT_LANGUAGE

# Tarjimalarni locales/*.json fayllaridan yuklash
TRANSLATIONS: dict[str, dict[str, str]] = {}

def load_translations() -> None:
    """JSON fayllardan barcha tillar uchun tarjimalarni yuklaydi."""
    global TRANSLATIONS
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    locales_dir = os.path.join(base_dir, "locales")

    for lang in LANGUAGES:
        TRANSLATIONS[lang] = {}
        json_path = os.path.join(locales_dir, f"{lang}.json")
        if os.path.isfile(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    TRANSLATIONS[lang] = json.load(f)
            except Exception as e:
                # Fallback to empty if reading fails
                TRANSLATIONS[lang] = {}

# Birinchi marta yuklab olamiz
load_translations()


def current_language() -> str:
    return str(_language)


def set_language(language: str) -> None:
    global _language
    if language not in LANGUAGES:
        language = DEFAULT_LANGUAGE
    _language = language
    _settings.setValue("language", language)


def tr(key: str, **kwargs: object) -> str:
    lang = current_language()
    lang_translations = TRANSLATIONS.get(lang, {})
    default_translations = TRANSLATIONS.get(DEFAULT_LANGUAGE, {})

    text = lang_translations.get(key, default_translations.get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
