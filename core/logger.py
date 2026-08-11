"""
Log tizimini sozlash va Debian App Manager loyihasi uchun yagona jurnal yuritish moduli.
"""

import os
import logging

LOG_DIR = os.path.expanduser("~/.log")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "debian-app-manager.log")

# Logger ni yaratish
logger = logging.getLogger("debian-app-manager")
logger.setLevel(logging.DEBUG)

# Formatni sozlash
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] (%(filename)s:%(lineno)d) %(message)s")

# Faylga yozish handler'i
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Agar interfeys yoki konsoldan tekshirish kerak bo'lsa, konsolga chiqarish
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def get_logger() -> logging.Logger:
    """Ilova uchun mos logger ob'ektini qaytaradi."""
    return logger
