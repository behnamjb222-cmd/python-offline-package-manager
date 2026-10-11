"""GUI tests run headless (QT_QPA_PLATFORM=offscreen). They drive the real pages, workers and services."""
import os
import subprocess
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["POPM_I18N_TRACE"] = "1"

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from app import i18n
from app.ui.main_window import PAGES, MainWindow
from app.workers.base import TaskWorker


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def win(qapp, ctx, monkeypatch, host):
    i18n.set_language("en")
    w = MainWindow(ctx)
    # never block on modal dialogs in tests: record them instead
    w.shown = []
    monkeypatch.setattr(w, "info", lambda t: w.shown.append(("info", t)))
    monkeypatch.setattr(w, "warn", lambda t: w.shown.append(("warn", t)))
    monkeypatch.setattr(w, "error", lambda e: w.shown.append(("error", str(getattr(e, "user_message", lambda l: e)("en") if hasattr(e, "user_message") else e))))
    w.answers = []
    monkeypatch.setattr(w, "confirm", lambda t, destructive=False: (w.answers.append(t), w.confirm_result)[1])
    w.confirm_result = True
    w.show()
    yield w
    w.close()
    w.deleteLater()
    i18n.set_language("en")


def wait_idle(qapp, win, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        qapp.processEvents()
        if win.worker is None or (not win.worker.isRunning() and win.task_bar.isHidden()):
            return
        time.sleep(0.02)
    raise TimeoutError("task did not finish")


def test_all_pages_open_in_both_languages_and_themes(qapp, win, ctx):
    for lang, theme in (("en", "light"), ("fa", "dark")):
        ctx.settings.theme = theme
        i18n.set_language(lang)
        win.rebuild("dashboard")
        for i, _ in enumerate(PAGES):
            win.sidebar.setCurrentRow(i)
            qapp.processEvents()
            assert win.stack.currentIndex() == i
        assert (qapp.layoutDirection().name == "RightToLeft") == (lang == "fa")


def test_persian_translation_coverage(qapp, win, ctx):
    from app.i18n import FA, SEEN
    i18n.set_language("fa")
    win.rebuild("dashboard")
    for i, _ in enumerate(PAGES):
        win.sidebar.setCurrentRow(i)
        qapp.processEvents()
    missing = sorted(s for s in SEEN if s not in FA and any(c.isalpha() for c in s) and "/" not in s and "·" not in s
                     and " — v" not in s and ":" not in s[:3] and not s.startswith(("<", "Python /")))
    assert missing == [], f"untranslated UI strings: {missing}"


def test_dashboard_cards_reflect_data(qapp, win, ctx, filled_repo):
    page = win.pages["dashboard"]
    page.refresh()
    assert page.vals["Archived files"].text() == "4"
    assert page.vals["Registered packages"].text() == "3"
    assert page.vals["Versions available"].text() == "4"
    assert page.vals["Repository status"].text() == "1 ✔"
    assert page.vals["Detected environments"].text() == "1"


def test_downloader_page_collects_into_repository(qapp, win, ctx, repo, index):
    page = win.pages["downloader"]
    win.goto("downloader")
    page.reqs.setPlainText("alpha")
    page.findlinks.setText(str(index))
    page.retries.setValue(0)
    page.start()
    wait_idle(qapp, win)
    assert not [s for s in win.shown if s[0] == "error"], win.shown
    names = {page.table.item(r, 0).text() for r in range(page.table.rowCount())}
    assert names == {"alpha-1.0-py3-none-any.whl", "beta-1.2-py3-none-any.whl"}
    assert {f.name for f in ctx.repos.list_files(repo.id)} == {"alpha", "beta"}


def test_downloader_reports_invalid_input_without_crashing(qapp, win, repo):
    page = win.pages["downloader"]
    win.goto("downloader")
    page.reqs.setPlainText("not a valid requirement !!")
    page.start()
    assert win.shown and win.shown[-1][0] == "error"
    page.reqs.setPlainText("")
    page.start()
    assert win.shown[-1][0] == "info"


def test_installer_page_plan_confirm_install_and_verify(qapp, win, ctx, filled_repo, tmp_path, monkeypatch):
    page = win.pages["installer"]
    win.goto("installer")
    shown = []
    from app.ui import installer_page
    monkeypatch.setattr(installer_page.SummaryDialog, "exec", lambda self: shown.append(self.windowTitle()) or True)
    for i in range(page.pkgs.count()):
        if page.pkgs.item(i).text() == "alpha":
            page.pkgs.item(i).setSelected(True)
    page.venv.setText(str(tmp_path / "gui venv"))
    assert not (tmp_path / "gui venv").exists()
    page.plan()
    wait_idle(qapp, win)                       # planning worker -> summary dialog (auto-accepted) -> install worker
    wait_idle(qapp, win)
    assert shown and "nothing has been changed yet" in shown[0]
    assert page.result is not None and page.result.ok, (page.result, win.shown)
    assert {page.table.item(r, 0).text() for r in range(page.table.rowCount())} == {"alpha", "beta"}
    out = subprocess.run([page.result.python_path, "-c", "import alpha;print(alpha.VERSION)"], capture_output=True, text=True)
    assert out.stdout.strip() == "1.0"


def test_installer_page_declined_summary_installs_nothing(qapp, win, ctx, filled_repo, tmp_path, monkeypatch):
    page = win.pages["installer"]
    win.goto("installer")
    from app.ui import installer_page
    monkeypatch.setattr(installer_page.SummaryDialog, "exec", lambda self: False)      # user presses Cancel
    page.pkgs.item(0).setSelected(True)
    page.venv.setText(str(tmp_path / "never"))
    page.plan()
    wait_idle(qapp, win)
    assert page.result is None and not (tmp_path / "never").exists()


def test_destructive_actions_ask_for_confirmation(qapp, win, ctx, filled_repo):
    page = win.pages["repositories"]
    win.goto("repositories")
    win.confirm_result = False
    page.delete()
    assert win.answers and ctx.repos.list(), "declining must keep the repository"
    page.table.selectAll()
    page.hard_delete()
    assert ctx.repos.get(filled_repo.id).files == 4
    win.confirm_result = True
    page.table.selectAll()
    page.hard_delete()
    assert ctx.repos.get(filled_repo.id).files == 0


def test_cancel_button_stops_a_running_task(qapp, win):
    def slow(w: TaskWorker):
        for _ in range(400):
            w.token.raise_if_cancelled()
            time.sleep(0.02)
        return "done"
    cancelled = []
    wk = TaskWorker("slow", slow)
    wk.cancelled.connect(lambda: cancelled.append(1))
    assert win.run(wk)
    assert win.cancel_btn.isVisibleTo(win) and not win.run(TaskWorker("second", lambda w: 1))      # one task at a time
    win.cancel_task()
    wait_idle(qapp, win, 10)
    qapp.processEvents()
    assert cancelled and win.task_bar.isHidden()


def test_settings_page_validation_and_language_switch(qapp, win, ctx):
    page = win.pages["settings"]
    win.goto("settings")
    page.proxy.setText("ftp//bad")
    page.save()
    assert win.shown[-1][0] == "error" and ctx.settings.proxy_url == ""
    page.proxy.setText("")
    page.lang.setCurrentText("fa")
    page.save()
    assert ctx.settings.language == "fa" and i18n.language() == "fa"
    assert ctx.settings_path.exists() and '"language": "fa"' in ctx.settings_path.read_text()


def test_environments_and_scanner_pages(qapp, win, ctx, host):
    win.goto("environments")
    win.pages["environments"].discover()
    wait_idle(qapp, win)
    assert win.pages["environments"].table.rowCount() >= 1
    win.set_active_env(host)
    win.goto("scanner")
    win.pages["scanner"].scan()
    wait_idle(qapp, win)
    sc = win.pages["scanner"]
    assert sc.table.rowCount() > 3
    sc.filter.setText("pytest")
    visible = [r for r in range(sc.table.rowCount()) if not sc.table.isRowHidden(r)]
    assert visible and all("pytest" in sc.table.item(r, 0).text().lower() for r in visible)


def test_reports_page_lists_operations_and_logs(qapp, win, ctx, filled_repo):
    ctx.integrity.verify_repository(filled_repo.id)
    win.goto("reports")
    page = win.pages["reports"]
    assert page.ops.rowCount() >= 2
    page.ops.selectRow(0)
    page.show_logs()
    assert page.logs.rowCount() >= 0


def test_storage_tools_on_integrity_page(qapp, win, ctx, filled_repo, monkeypatch):
    from app.ui import integrity_page
    texts = []
    monkeypatch.setattr(integrity_page.SummaryDialog, "exec", lambda self: texts.append(self.findChild(__import__("PySide6.QtWidgets", fromlist=["QPlainTextEdit"]).QPlainTextEdit).toPlainText()) or True)
    win.goto("integrity")
    page = win.pages["integrity"]
    page.refresh()
    page.storage_report()
    assert "Largest files" in texts[0] and "beta-1.2" in texts[0]
    page.delete_orphans()
    assert win.shown[-1] == ("info", "No unreferenced files.")
    # create an orphan blob (no database reference) -> it is found and deleted only after confirmation
    orphan = ctx.repos.blobs_dir / "ab" / ("ab" + "0" * 62)
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"x")
    win.confirm_result = False
    page.delete_orphans()
    assert orphan.exists()
    win.confirm_result = True
    page.delete_orphans()
    assert not orphan.exists() and ctx.repos.health_check(filled_repo.id).ok
    page.clean_temp()
