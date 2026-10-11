# PyInstaller spec for POPM (one-folder build).  Run from the project root:  pyinstaller scripts/popm.spec --noconfirm
from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("app")
excludes = ["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtQuick",
            "PySide6.QtQml", "PySide6.QtMultimedia", "tkinter", "pytest"]

a = Analysis(["../main.py"], pathex=[".."], hiddenimports=hidden, excludes=excludes, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="POPM", console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="POPM")
