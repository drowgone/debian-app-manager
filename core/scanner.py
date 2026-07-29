"""
Barcha manbalardan (APT, Snap, Flatpak, qo'lda) o'rnatilgan
dasturlar ro'yxatini yig'ish moduli.
"""

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime

from core.desktop_parser import find_desktop_files, parse_desktop_entry
from core.appimage_manager import is_appimage_managed, APPIMAGE_DIR


# ── Tizim snap'lari — filtrlanadi ──────────────────────────────────────────
SYSTEM_SNAPS = frozenset({
    "core", "core18", "core20", "core22", "core24", "snapd", "bare",
})

# ── .desktop fayl joylashuvi ───────────────────────────────────────────────
DESKTOP_DIRS = [
    "/usr/share/applications",
    "/usr/local/share/applications",
    "/var/lib/snapd/desktop/applications",
    os.path.expanduser("~/.local/share/applications"),
]

# ── Faqat Settings/System kategoriyali dasturlarni o'tkazib yuborish ───────
_SYSTEM_ONLY_CATEGORIES = {"Settings", "System"}


@dataclass
class App:
    """Bitta dasturni ifodalovchi ma'lumot tuzilmasi."""
    name: str
    source: str          # "apt" | "snap" | "flatpak" | "appimage" | "manual"
    identifier: str      # paket nomi / snap nomi / flatpak app-id / desktop fayl yo'li
    desktop_path: str
    icon: str
    exec_line: str
    version: str = ""
    size: str = ""
    date: str = ""       # o'rnatilgan/yangilangan sana (YYYY-MM-DD)
    has_update: bool = False
    new_version: str = ""


# ── APT yordamchi funksiyalar ──────────────────────────────────────────────

def get_manual_apt_packages() -> set[str]:
    """apt-mark showmanual orqali foydalanuvchi o'zi o'rnatgan paketlarni qaytaradi."""
    try:
        result = subprocess.run(
            ["apt-mark", "showmanual"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return set(result.stdout.strip().splitlines())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return set()


def get_dpkg_owners(paths: list[str]) -> dict[str, str]:
    """Bir nechta fayl yo'llari uchun dpkg paket egalarini aniqlaydi."""
    if not paths:
        return {}
    owners = {}
    chunk_size = 500
    for i in range(0, len(paths), chunk_size):
        chunk = paths[i:i + chunk_size]
        try:
            result = subprocess.run(
                ["dpkg", "-S"] + chunk,
                capture_output=True, text=True, timeout=30,
            )
            for line in result.stdout.splitlines():
                if ":" in line:
                    parts = line.split(":", 1)
                    package = parts[0].strip()
                    if "," in package:
                        package = package.split(",")[0].strip()
                    filepath = parts[1].strip()
                    owners[filepath] = package
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return owners


# ── Snap yordamchi funksiya ────────────────────────────────────────────────

def get_snap_apps() -> list[dict]:
    """snap list chiqishini parse qilib, tizim snap'larini filtrlab qaytaradi."""
    apps: list[dict] = []
    try:
        result = subprocess.run(
            ["snap", "list"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return apps
        lines = result.stdout.strip().splitlines()
        if len(lines) < 2:
            return apps
        # Birinchi qator sarlavha: Name  Version  Rev  ...
        for line in lines[1:]:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            if name in SYSTEM_SNAPS:
                continue
            version = parts[1] if len(parts) > 1 else ""
            rev = parts[2] if len(parts) > 2 else ""
            apps.append({"name": name, "version": version, "rev": rev})
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return apps


# ── Flatpak yordamchi funksiya ─────────────────────────────────────────────

def get_flatpak_apps() -> list[dict]:
    """flatpak list --app orqali faqat ilovalarni oladi (runtime'lar chiqariladi)."""
    apps: list[dict] = []
    try:
        result = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application,name,version,size"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return apps
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                app_id = parts[0].strip()
                name = parts[1].strip()
                version = parts[2].strip() if len(parts) > 2 else ""
                size = parts[3].strip() if len(parts) > 3 else ""
                apps.append({"app_id": app_id, "name": name, "version": version, "size": size})
            elif len(parts) == 1 and parts[0].strip():
                app_id = parts[0].strip()
                apps.append({"app_id": app_id, "name": app_id, "version": "", "size": ""})
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return apps


# ── Paket Priority tekshiruvi ──────────────────────────────────────────────

def get_essential_packages() -> set[str]:
    """Tizimdagi barcha required/important paketlarni qaytaradi."""
    essentials = set()
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package} ${Priority}\n"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    pkg = parts[0]
                    prio = parts[1].lower()
                    if prio in ("required", "important"):
                        essentials.add(pkg)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return essentials


def _is_library_package(package_name: str) -> bool:
    """Paket kutubxona ekanini tekshiradi (nomi lib bilan boshlanadi)."""
    return package_name.startswith("lib")


# ── Manba aniqlash ─────────────────────────────────────────────────────────

def _detect_source(
    desktop_path: str,
    exec_line: str,
    snap_names: set[str],
    flatpak_ids: dict[str, str],
    dpkg_owner_pkg: str | None,
) -> tuple[str, str]:
    """
    .desktop faylning manbasini aniqlaydi.
    Qaytaradi: (source, identifier)
    """
    # 1) Snap tekshiruvi
    if "/snap/" in desktop_path or "/var/lib/snapd/" in desktop_path:
        # Snap nomini desktop fayl nomidan aniqlash: firefox_firefox.desktop -> firefox
        basename = os.path.basename(desktop_path)
        snap_name = basename.split("_")[0] if "_" in basename else basename.replace(".desktop", "")
        if snap_name in snap_names:
            return "snap", snap_name
        # Exec yo'lidan aniqlash
        if "/snap/" in exec_line:
            parts = exec_line.split("/snap/")
            if len(parts) > 1:
                snap_name = parts[1].split("/")[0]
                if snap_name in snap_names:
                    return "snap", snap_name
        return "snap", snap_name

    # 2) Flatpak tekshiruvi
    if "flatpak run" in exec_line:
        # "flatpak run com.example.App" -> "com.example.App"
        parts = exec_line.split("flatpak run")
        if len(parts) > 1:
            remaining = parts[1].strip().split()
            # Flaglarni o'tkazib yuborish (--file-forwarding kabi)
            for part in remaining:
                if not part.startswith("-"):
                    app_id = part.strip()
                    return "flatpak", app_id
        return "flatpak", ""

    # Flatpak desktop faylini app-id orqali tekshirish
    basename = os.path.basename(desktop_path).replace(".desktop", "")
    if basename in flatpak_ids:
        return "flatpak", basename

    # 3) dpkg orqali tekshirish
    if dpkg_owner_pkg:
        return "apt", dpkg_owner_pkg

    # 4) AppImage tekshiruvi — Exec satrida .appimage bo'lsa (qayerda joylashganidan qat'iy nazar)
    # Bu orqali foydalanuvchi oldin o'rnatgan (boshqa papkadagi) AppImagelar ham aniqlanadi.
    for part in exec_line.split():
        clean_part = part.strip('"').strip("'")
        if clean_part.lower().endswith(".appimage"):
            return "appimage", clean_part

    # 5) Qo'lda o'rnatilgan
    return "manual", desktop_path


# ── Kategoriya filtri ──────────────────────────────────────────────────────

def _should_skip_by_category(categories_str: str) -> bool:
    """Faqat Settings/System kategoriyali dasturlarni o'tkazib yuborish."""
    if not categories_str:
        return False
    cats = {c.strip() for c in categories_str.split(";") if c.strip()}
    # Agar faqat System/Settings kategoriyalari bo'lsa — o'tkazib yuborish
    return bool(cats) and cats.issubset(_SYSTEM_ONLY_CATEGORIES)


# ── Asosiy funksiya ───────────────────────────────────────────────────────

def _get_apt_metadata() -> dict[str, tuple[str, str, str]]:
    """Barcha APT paketlarining versiya, hajm va sanasini qaytaradi.
    Qaytaradi: {paket_nomi: (versiya, hajm_str, sana_str)}
    """
    data: dict[str, tuple[str, str, str]] = {}
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Installed-Size}\n"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) == 3:
                    pkg, ver, size_kb = parts
                    # Hajmni o'qish (KB -> MB)
                    try:
                        mb = int(size_kb) / 1024
                        if mb >= 1:
                            size_str = f"{mb:.1f} MB"
                        else:
                            size_str = f"{int(size_kb)} KB"
                    except ValueError:
                        size_str = ""
                    # Sanani aniqlash
                    date_str = ""
                    list_file = f"/var/lib/dpkg/info/{pkg}.list"
                    if os.path.exists(list_file):
                        try:
                            mtime = os.path.getmtime(list_file)
                            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                        except OSError:
                            pass
                    data[pkg] = (ver, size_str, date_str)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return data


def _get_snap_metadata(snap_apps: list[dict]) -> dict[str, tuple[str, str, str]]:
    """Snap dasturlarining versiya, hajm va sanasini qaytaradi.
    Qaytaradi: {snap_nomi: (versiya, hajm_str, sana_str)}
    """
    data: dict[str, tuple[str, str, str]] = {}
    for s in snap_apps:
        name = s["name"]
        version = s.get("version", "")
        rev = s.get("rev", "")
        size_str = ""
        date_str = ""
        # snap faylining hajmi va sanasi
        snap_file = f"/var/lib/snapd/snaps/{name}_{rev}.snap"
        if os.path.exists(snap_file):
            try:
                fsize = os.path.getsize(snap_file)
                mb = fsize / (1024 * 1024)
                if mb >= 1:
                    size_str = f"{mb:.1f} MB"
                else:
                    size_str = f"{fsize // 1024} KB"
                mtime = os.path.getmtime(snap_file)
                date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            except OSError:
                pass
        data[name] = (version, size_str, date_str)
    return data


def _get_flatpak_metadata(flatpak_apps: list[dict]) -> dict[str, tuple[str, str, str]]:
    """Flatpak dasturlarining versiya, hajm va sanasini qaytaradi.
    Qaytaradi: {app_id: (versiya, hajm_str, sana_str)}
    """
    data: dict[str, tuple[str, str, str]] = {}
    for f in flatpak_apps:
        app_id = f["app_id"]
        version = f.get("version", "")
        size = f.get("size", "")
        date_str = ""
        # Flatpak o'rnatilgan sanasi
        for base in [
            f"/var/lib/flatpak/app/{app_id}/current/active/metadata",
            os.path.expanduser(f"~/.local/share/flatpak/app/{app_id}/current/active/metadata"),
        ]:
            if os.path.exists(base):
                try:
                    mtime = os.path.getmtime(base)
                    date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                except OSError:
                    pass
                break
        data[app_id] = (version, size, date_str)
    return data


def _get_manual_metadata(desktop_path: str) -> tuple[str, str, str]:
    """Qo'lda o'rnatilgan dasturning versiya, hajm va sanasini qaytaradi."""
    version = ""
    size_str = ""
    date_str = ""
    try:
        stat = os.stat(desktop_path)
        fsize = stat.st_size
        if fsize >= 1024 * 1024:
            size_str = f"{fsize / (1024 * 1024):.1f} MB"
        elif fsize >= 1024:
            size_str = f"{fsize // 1024} KB"
        else:
            size_str = f"{fsize} B"
        mtime = stat.st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except OSError:
        pass
    return version, size_str, date_str


def _get_appimage_metadata(entry: dict, identifier: str) -> tuple[str, str, str]:
    """AppImage dasturning versiya, hajm va sanasini qaytaradi.
    identifier bu yerda AppImage faylning to'liq yo'li.
    """
    version = ""
    size_str = ""
    date_str = ""
    # Exec satridagi yo'lni olish — identifier AppImage fayl yo'li
    file_path = identifier.strip('"').strip("'")
    try:
        if os.path.isfile(file_path):
            fstat = os.stat(file_path)
            fsize = fstat.st_size
            if fsize >= 1024 * 1024:
                size_str = f"{fsize / (1024 * 1024):.1f} MB"
            elif fsize >= 1024:
                size_str = f"{fsize // 1024} KB"
            else:
                size_str = f"{fsize} B"
            mtime = fstat.st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except OSError:
        pass
    return version, size_str, date_str


def build_app_list() -> list[App]:
    """
    Barcha manbalardan dasturlarni skanerlab, App ro'yxatini qaytaradi.
    Kutubxonalar, sistema demonlari va essential paketlar filtrlanadi.
    """
    # Oldindan barcha ma'lumotlarni yig'ish
    manual_packages = get_manual_apt_packages()
    snap_apps = get_snap_apps()
    snap_names = {s["name"] for s in snap_apps}
    flatpak_apps = get_flatpak_apps()
    flatpak_ids = {f["app_id"]: f["name"] for f in flatpak_apps}

    desktop_files = find_desktop_files(DESKTOP_DIRS)
    dpkg_owners = get_dpkg_owners(desktop_files)
    essential_packages = get_essential_packages()

    # Metadata'ni oldindan yig'ish (bir marta batch)
    apt_meta = _get_apt_metadata()
    snap_meta = _get_snap_metadata(snap_apps)
    flatpak_meta = _get_flatpak_metadata(flatpak_apps)

    apps: list[App] = []
    seen_identifiers: set[str] = set()

    for dpath in desktop_files:
        entry = parse_desktop_entry(dpath)
        if not entry:
            continue

        # NoDisplay yoki Hidden bo'lsa — o'tkazib yuborish
        if entry.get("NoDisplay", "").lower() == "true":
            continue
        if entry.get("Hidden", "").lower() == "true":
            continue

        # Type = Application bo'lmasa — o'tkazib yuborish
        if entry.get("Type", "Application") != "Application":
            continue

        # Faqat Settings/System kategoriya bo'lsa — o'tkazib yuborish
        if _should_skip_by_category(entry.get("Categories", "")):
            continue

        name = entry.get("Name", os.path.basename(dpath).replace(".desktop", ""))
        exec_line = entry.get("Exec", "")
        icon = entry.get("Icon", "")

        # Manbani aniqlash
        source, identifier = _detect_source(dpath, exec_line, snap_names, flatpak_ids, dpkg_owners.get(dpath))

        # AppImage: desktop fayldagi X-AppImage-Managed kaliti bilan ham tekshirish
        if source == "manual" and is_appimage_managed(entry):
            # Exec satridagi AppImage faylini identifier sifatida ishlatish
            for part in exec_line.split():
                clean_part = part.strip('"').strip("'")
                if clean_part.lower().endswith(".appimage"):
                    source = "appimage"
                    identifier = clean_part
                    break
            else:
                source = "appimage"

        # Takroriy identifikatorlarni oldini olish
        if identifier in seen_identifiers:
            continue
        seen_identifiers.add(identifier)

        # APT paketlar uchun qo'shimcha filtrlar
        if source == "apt":
            # Kutubxonalar
            if _is_library_package(identifier):
                continue
            # Essential/important paketlar
            if identifier in essential_packages:
                continue

        # Versiya, hajm va sanani olish
        version, size, date = "", "", ""
        if source == "apt":
            version, size, date = apt_meta.get(identifier, ("", "", ""))
        elif source == "snap":
            version, size, date = snap_meta.get(identifier, ("", "", ""))
        elif source == "flatpak":
            version, size, date = flatpak_meta.get(identifier, ("", "", ""))
        elif source == "appimage":
            version, size, date = _get_appimage_metadata(entry, identifier)
        else:
            version, size, date = _get_manual_metadata(dpath)

        apps.append(App(
            name=name,
            source=source,
            identifier=identifier,
            desktop_path=dpath,
            icon=icon,
            exec_line=exec_line,
            version=version,
            size=size,
            date=date,
        ))

    # Nom bo'yicha tartiblash
    apps.sort(key=lambda a: a.name.lower())
    return apps
