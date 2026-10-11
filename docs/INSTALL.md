# Installation / راهنمای نصب

## From source (Windows / Linux / macOS)
```
python --version                      # must be 3.11 or newer
python -m venv .venv
.venv\Scripts\activate                # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
python main.py
```
PowerShell helper: `.\scripts\create_venv.ps1`.

## On an offline machine
POPM itself can be moved offline the same way it moves other packages: on an online machine make a repository for the target
(Python 3.12 / windows / x86_64, say) containing `PySide6-Essentials` and `packaging`, create a bundle, and run its `install_offline.py`.
Or use the prebuilt EXE (`scripts\build_windows.ps1` → `dist\POPM`), which needs no Python installed to *run POPM*
(you still need a Python on the machine to *install packages into*).

## فارسی
۱. Python ۳.۱۱ یا بالاتر نصب کنید. ۲. `python -m venv .venv` و فعال‌سازی آن. ۳. `pip install -r requirements-dev.txt`. ۴. `python main.py`.
برای سیستم آفلاین: روی سیستم آنلاین یک مخزن برای مقصد (مثلاً Python 3.12 / windows / x86_64) با پکیج‌های `PySide6-Essentials` و `packaging` بسازید، بسته بسازید و
`install_offline.py` را اجرا کنید؛ یا از نسخه‌ی EXE استفاده کنید (برای *اجرای POPM* به Python نیاز ندارد، اما برای *نصب پکیج‌ها* باید یک Python روی سیستم باشد).
