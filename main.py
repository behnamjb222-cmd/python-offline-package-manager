#!/usr/bin/env python3
"""Python Offline Package Manager - entry point."""
from __future__ import annotations

import sys


def selftest() -> int:
    """Headless smoke test (also used to check a built EXE): database, services and every page must come up."""
    import os
    import tempfile
    from pathlib import Path

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from app import i18n
    from app.bootstrap import create_context
    from app.ui.main_window import PAGES, MainWindow

    app = QApplication([])
    with tempfile.TemporaryDirectory(prefix="popm_selftest_") as tmp:
        ctx = create_context(Path(tmp))
        for lang in ("en", "fa"):
            i18n.set_language(lang)
            win = MainWindow(ctx)
            for i in range(len(PAGES)):
                win.sidebar.setCurrentRow(i)
                app.processEvents()
            win.close()
        ctx.close()
    print("POPM selftest OK")
    return 0


def main() -> int:
    if sys.version_info < (3, 11):
        sys.stderr.write("POPM needs Python 3.11 or newer to run.\n")
        return 1
    if "--selftest" in sys.argv:
        return selftest()
    from PySide6.QtWidgets import QApplication

    from app import i18n
    from app.bootstrap import create_context
    from app.core.constants import APP_NAME
    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    ctx = create_context()
    i18n.set_language(ctx.settings.language)
    win = MainWindow(ctx)
    win.show()
    code = app.exec()
    ctx.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
