# Tashqi Dastur Boshqaruvchisi

Debian/Ubuntu Linux uchun APT, Snap, Flatpak, AppImage va qo'lda o'rnatilgan
dasturlarni bitta grafik interfeysdan boshqarish vositasi.

## Xususiyatlar

- O'rnatilgan dasturlarni manba bo'yicha ko'rish, qidirish va filtrlash
- APT, Snap, Flatpak, AppImage va qo'lda o'rnatilgan dasturlarni xavfsiz o'chirish
- `.AppImage` fayllarni import qilish va desktop launcher yaratish
- Avtoishga tushadigan dasturlarni yoqish, o'chirish va olib tashlash
- Tizim keshlarini, keraksiz bog'liqliklarni va loglarni tanlab tozalash
- Xatolik va ogohlantirishlarni alohida tabda ko'rish
- Linux desktop muhitlariga mos yorug'/qorong'u tema va High-DPI tiniq UI

## Tizim Talablari

- Debian 12+ yoki Ubuntu 22.04+ asosidagi desktop Linux
- Python 3.10+
- `pkexec` / polkit
- Ixtiyoriy: `snapd`, `flatpak`, `systemd-analyze`

## O'rnatish

```bash
git clone https://github.com/<username>/debian-app-manager.git
cd debian-app-manager

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Ishga Tushirish

```bash
python main.py
```

Desktop menyuga qo'shish uchun:

```bash
./install.sh
```

## Testlar

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Loyiha Tuzilmasi

```text
debian-app-manager/
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── install.sh
├── core/
│   ├── appimage_manager.py
│   ├── autostart.py
│   ├── cleaner.py
│   ├── desktop_parser.py
│   ├── installer.py
│   ├── launcher.py
│   ├── remover.py
│   ├── scanner.py
│   └── updater.py
├── gui/
│   ├── animations.py
│   ├── app_detail_dialog.py
│   ├── clean_worker.py
│   ├── layout_helpers.py
│   ├── main_window.py
│   ├── scan_worker.py
│   ├── theme.py
│   └── widgets.py
└── tests/
```

## Xavfsizlik

- Subprocess chaqiruvlari `shell=False` bilan ishlaydi
- Root huquqi kerak bo'lgan amallar `pkexec` orqali bajariladi
- Tizim autostart fayllari bevosita o'zgartirilmaydi, override ishlatiladi
- AppImage va qo'lda o'rnatilgan fayllarni o'chirishda path xavfsizligi tekshiriladi
- Har bir xavfli amal oldidan foydalanuvchidan tasdiqlash olinadi

## Litsenziya

MIT
