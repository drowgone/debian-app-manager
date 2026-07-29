# Tashqi Dastur Boshqaruvchisi

Bu GitHub asosiy sahifasi uchun O‘zbekcha versiya. Agar boshqa til kerak
bo‘lsa, quyidagi fayllardan foydalanishingiz mumkin:

- [English](README.en.md)
- [Русский](README.ru.md)
- [O‘zbekcha](README.uz.md)

Tashqi Dastur Boshqaruvchisi Debian/Ubuntu asosidagi Linux tizimlarida
o'rnatilgan dasturlarni bitta joydan ko'rish, ishga tushirish, yangilash,
o'chirish, AppImage fayllarni import qilish va avtoishga tushish yozuvlarini
boshqarish uchun yaratilgan PySide6 grafik dastur.

Ilova APT, Snap, Flatpak, AppImage va qo'lda o'rnatilgan dasturlarni alohida
manbalar sifatida taniydi. Interfeys Linux desktop muhitlariga mos, yorug' va
qorong'u mavzuni avtomatik qo'llaydi hamda High-DPI ekranlarda tiniq ko'rinish
uchun sozlangan.

## Asosiy Imkoniyatlar

- O'rnatilgan dasturlarni APT, Snap, Flatpak, AppImage va qo'lda o'rnatilgan
  manbalar bo'yicha ko'rish
- Dasturlarni nomi bo'yicha qidirish va manba bo'yicha filtrlash
- Dastur haqida versiya, hajm, manba va o'rnatilgan sana kabi ma'lumotlarni
  ko'rsatish
- Dasturlarni xavfsiz tarzda ishga tushirish, yangilash va o'chirish
- `.AppImage` fayllarni import qilish, executable qilish va desktop launcher
  yaratish
- Kompyuter yoqilganda avtomatik ishga tushadigan dasturlarni boshqarish
- Tizim yuklanish vaqti hamda ko'p vaqt olgan xizmatlar haqida qisqa ma'lumot
  chiqarish
- APT keshi, keraksiz bog'liqliklar, Flatpak runtime qoldiqlari va loglarni
  tanlab tozalash
- Xatolik va ogohlantirishlarni alohida tabda ko'rsatish
- Skanerlash, yangilash va tozalash jarayonlari uchun fon worker'lari va UI
  animatsiyalari
- High-DPI ekranlar uchun tiniq matn, ikon va scaling sozlamalari

## Interfeys Tab'lari

### Dasturlar

Bu bo'lim tizimdagi dasturlarni umumiy ro'yxatda ko'rsatadi. Qidiruv maydoni,
manba filtri va dastur soni ko'rsatkichi mavjud. Har bir dastur satrida nom,
manba badge'i va bajariladigan amal tugmalari chiqadi.

### Avtoishga Tushish

Bu bo'lim kompyuter ishga tushganda avtomatik ochiladigan dasturlarni
boshqaradi. Foydalanuvchi va tizim darajasidagi autostart yozuvlari o'qiladi.
Tizim yozuvlari bevosita o'zgartirilmaydi, kerak bo'lsa foydalanuvchi
override fayli orqali boshqariladi.

### Tozalash

Bu bo'lim tizimda vaqt o'tishi bilan yig'iladigan kesh va qoldiq fayllarni
tanlab tozalashga yordam beradi. Tozalash jarayoni terminal ko'rinishidagi
panelda chiqariladi.

### Xatoliklar

Skanerlash, yangilash, o'chirish yoki tozalash paytida yuz bergan muammolar
shu bo'limda jamlanadi. Bu foydalanuvchiga qaysi manba yoki buyruqda muammo
bo'lganini tez tushunishga yordam beradi.

## Tizim Talablari

- Debian 12+ yoki Ubuntu 22.04+ asosidagi desktop Linux
- Python 3.10 yoki undan yangi versiya
- `pkexec` va polkit
- PySide6
- Ixtiyoriy: `snapd`
- Ixtiyoriy: `flatpak`
- Ixtiyoriy: `systemd-analyze`

## O'rnatish

GitHub'dan klon qilish:

```bash
git clone https://github.com/<username>/debian-app-manager.git
cd debian-app-manager
```

Virtual muhit yaratish:

```bash
python3 -m venv venv
source venv/bin/activate
```

Bog'liqliklarni o'rnatish:

```bash
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

`install.sh` foydalanuvchi uchun `.desktop` fayl yaratadi va ilovani desktop
menyudan ishga tushirish imkonini beradi.

## Testlarni Ishga Tushirish

Development bog'liqliklarini o'rnatish:

```bash
pip install -r requirements-dev.txt
```

Testlarni bajarish:

```bash
pytest tests/ -v
```

Qisqa ko'rinish:

```bash
pytest tests/ -q
```

Hozirgi holatda testlar:

```text
87 passed
```

## GitHub'ga Yuklash

Loyiha GitHub uchun tayyorlangan: `.gitignore`, `LICENSE`, README va testlar
mavjud. Yangi GitHub repository ochilgandan keyin quyidagilarni bajarish
kifoya:

```bash
git remote add origin https://github.com/<username>/debian-app-manager.git
git push -u origin main
```

Agar remote avval qo'shilgan bo'lsa:

```bash
git remote set-url origin https://github.com/<username>/debian-app-manager.git
git push -u origin main
```

## Loyiha Tuzilmasi

```text
debian-app-manager/
├── main.py
├── install.sh
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── LICENSE
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
    ├── test_appimage.py
    ├── test_autostart.py
    ├── test_installer.py
    ├── test_remover.py
    ├── test_scanner.py
    └── test_updater.py
```

## Muhim Modullar

- `core/scanner.py` tizimdagi dasturlarni turli manbalardan yig'adi
- `core/remover.py` dasturlarni manbasiga qarab xavfsiz o'chiradi
- `core/updater.py` APT, Snap va Flatpak yangilash amallarini boshqaradi
- `core/autostart.py` avtoishga tushish yozuvlarini o'qiydi va o'zgartiradi
- `core/appimage_manager.py` AppImage import va o'chirish amallarini bajaradi
- `core/cleaner.py` tizim tozalash buyruqlarini tayyorlaydi
- `gui/main_window.py` asosiy PySide6 oynasi va tablarni quradi
- `gui/theme.py` ranglar, shriftlar, High-DPI va stylesheet sozlamalarini beradi
- `gui/layout_helpers.py` qayta ishlatiladigan UI layout komponentlarini saqlaydi

## Xavfsizlik Yondashuvi

Ilova tizimga ta'sir qiladigan amallarni ehtiyotkorlik bilan bajarishga
mo'ljallangan.

- Subprocess chaqiruvlari `shell=False` bilan bajariladi
- Root huquqi kerak bo'lgan amallar `pkexec` orqali bajariladi
- `sudo` to'g'ridan-to'g'ri ishlatilmaydi
- Tizim autostart fayllari bevosita o'zgartirilmaydi
- Tizim kataloglaridagi fayllarni avtomatik o'chirish cheklanadi
- Symlink va real path tekshiruvlari qo'llanadi
- O'chirish yoki tozalash kabi xavfli amallardan oldin tasdiqlash oynasi
  ko'rsatiladi

## Troubleshooting

### PySide6 topilmadi

Virtual muhit yoqilganini tekshiring:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### `pkexec` ishlamayapti

Polkit o'rnatilganini tekshiring:

```bash
pkexec --version
```

Desktop sessiyada polkit authentication agent ishlayotgan bo'lishi kerak.

### Snap yoki Flatpak dasturlari ko'rinmayapti

Mos servis yoki CLI o'rnatilganini tekshiring:

```bash
snap version
flatpak --version
```

Bu vositalar o'rnatilmagan bo'lsa, ilova qolgan manbalar bilan ishlashda davom
etadi.

### Desktop menyuda ilova ko'rinmadi

`install.sh`ni qayta ishga tushiring:

```bash
./install.sh
```

Keyin desktop muhitini qayta yuklash yoki logout/login qilish kerak bo'lishi
mumkin.

## Development

Kod o'zgarishidan oldin virtual muhitni yoqing:

```bash
source venv/bin/activate
```

Tez sintaksis tekshiruvi:

```bash
python -m py_compile main.py gui/main_window.py gui/theme.py
```

To'liq test:

```bash
pytest tests/ -q
```

## Reja

- UI uchun screenshotlar qo'shish
- `.deb` paket tayyorlash
- AppImage import jarayonini yanada boyitish
- Yangilanish tekshiruvini ko'proq manbalar bilan kengaytirish
- Lokalizatsiya fayllarini alohida formatga chiqarish

## Hissa Qo'shish

Pull requestlar va takliflar qabul qilinadi. O'zgarish yuborishdan oldin
testlarni ishga tushiring va xavfli tizim amallariga tegadigan kodni alohida
ehtiyotkorlik bilan tekshiring.

## Litsenziya

Ushbu loyiha MIT litsenziyasi ostida tarqatiladi. Batafsil ma'lumot
[LICENSE](LICENSE) faylida.
