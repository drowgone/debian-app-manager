# External Application Manager

This is the English version for the GitHub homepage. If you need a different language, you can use the following files:


- [English](README.en.md)
- [Русский](README.ru.md)
- [O‘zbekcha](README.uz.md)


External Application Manager is a PySide6-based GUI application for
Debian/Ubuntu-based Linux systems that lets you view, launch, update,
remove installed applications, import AppImage files, and manage
autostart entries — all from a single place.

The application recognizes APT, Snap, Flatpak, AppImage, and manually
installed applications as separate sources. The interface adapts to
Linux desktop environments, automatically applies light and dark
themes, and is tuned for crisp rendering on High-DPI displays.

## Key Features

- View installed applications grouped by APT, Snap, Flatpak, AppImage,
  and manually installed sources
- Search applications by name and filter by source
- Display application details such as version, size, source, and
  installation date
- Safely launch, update, and remove applications
- Import `.AppImage` files, make them executable, and create desktop
  launchers
- Manage applications that start automatically on boot
- Show a brief summary of system boot time and services that take the
  longest to start
- Selectively clean APT cache, orphaned dependencies, leftover Flatpak
  runtimes, and log files
- Display errors and warnings in a dedicated tab
- Background workers and UI animations for scanning, updating, and
  cleaning processes
- Clear text, icons, and scaling settings for High-DPI displays

## Interface Tabs

### Applications

This section shows installed applications in a unified list. It
includes a search field, a source filter, and an application count
indicator. Each application row shows its name, a source badge, and
action buttons.

### Autostart

This section manages applications that open automatically when the
computer starts. User-level and system-level autostart entries are
read. System entries are never modified directly; if needed, the user
manages them through an override file.

### Cleanup

This section helps selectively clean cache and residual files that
accumulate over time. The cleanup process is shown in a terminal-style
panel.

### Errors

Issues that occur during scanning, updating, removing, or cleaning are
collected in this section. It helps the user quickly understand which
source or command caused a problem.

## System Requirements

- Debian 12+ or Ubuntu 22.04+ based desktop Linux
- Python 3.10 or newer
- `pkexec` and polkit
- PySide6
- Optional: `snapd`
- Optional: `flatpak`
- Optional: `systemd-analyze`

## Installation

Clone from GitHub:

```bash
git clone https://github.com/<username>/debian-app-manager.git
cd debian-app-manager
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python main.py
```

To add it to the desktop menu:

```bash
./install.sh
```

`install.sh` creates a `.desktop` file for the current user and allows
launching the application from the desktop menu.

## Running Tests

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest tests/ -v
```

Short output:

```bash
pytest tests/ -q
```

Current test status:

```text
87 passed
```

## Pushing to GitHub

The project is ready for GitHub: `.gitignore`, `LICENSE`, README, and
tests are included. After creating a new GitHub repository, simply run:

```bash
git remote add origin https://github.com/<username>/debian-app-manager.git
git push -u origin main
```

If the remote has already been added:

```bash
git remote set-url origin https://github.com/<username>/debian-app-manager.git
git push -u origin main
```

## Project Structure

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

## Key Modules

- `core/scanner.py` — collects installed applications from various sources
- `core/remover.py` — safely removes applications depending on their source
- `core/updater.py` — manages APT, Snap, and Flatpak update operations
- `core/autostart.py` — reads and modifies autostart entries
- `core/appimage_manager.py` — handles AppImage import and removal
- `core/cleaner.py` — prepares system cleanup commands
- `gui/main_window.py` — builds the main PySide6 window and tabs
- `gui/theme.py` — provides colors, fonts, High-DPI, and stylesheet settings
- `gui/layout_helpers.py` — stores reusable UI layout components

## Security Approach

The application is designed to perform system-affecting operations
carefully.

- Subprocess calls are executed with `shell=False`
- Operations requiring root privileges are performed via `pkexec`
- `sudo` is never used directly
- System autostart files are never modified directly
- Automatic deletion of files in system directories is restricted
- Symlink and real path checks are applied
- A confirmation dialog is shown before dangerous operations such as
  removal or cleanup

## Troubleshooting

### PySide6 not found

Make sure the virtual environment is active:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### `pkexec` doesn't work

Check that polkit is installed:

```bash
pkexec --version
```

A polkit authentication agent must be running in the desktop session.

### Snap or Flatpak applications don't appear

Check that the corresponding service or CLI is installed:

```bash
snap version
flatpak --version
```

If these tools are not installed, the application continues to work
with the remaining sources.

### Application doesn't appear in the desktop menu

Re-run `install.sh`:

```bash
./install.sh
```

You may then need to reload the desktop environment or log out and
log back in.

## Development

Activate the virtual environment before making code changes:

```bash
source venv/bin/activate
```

Quick syntax check:

```bash
python -m py_compile main.py gui/main_window.py gui/theme.py
```

Full test run:

```bash
pytest tests/ -q
```

## Roadmap

- Add UI screenshots
- Prepare a `.deb` package
- Further enhance the AppImage import process
- Expand update checking to more sources
- Extract localization files into a separate format

## Contributing

Pull requests and suggestions are welcome. Run the tests before
submitting changes, and pay special attention when reviewing code that
touches sensitive system operations.

## License

This project is distributed under the MIT License. See the
[LICENSE](LICENSE) file for details.
