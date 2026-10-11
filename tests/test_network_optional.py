"""Real-PyPI checks. Skipped unless POPM_NETWORK_TESTS=1 (they need internet and take a while)."""
import os
import subprocess
from pathlib import Path

import pytest

from app.core.models import CompatStatus, TargetSpec
from app.services.package_downloader import DownloadOptions

pytestmark = pytest.mark.skipif(os.environ.get("POPM_NETWORK_TESTS") != "1", reason="set POPM_NETWORK_TESTS=1 to run")


def test_cross_platform_collect_from_pypi_adds_windows_only_dependency(ctx, host):
    """tqdm needs colorama only on Windows; collecting from Linux for Windows must still fetch it."""
    win = TargetSpec("3.12", "windows", "x86_64")
    r = ctx.repos.create_repository("win_tqdm", win)
    res = ctx.downloader.collect(["tqdm==4.66.5"], r.id, host, win, DownloadOptions(retries=2))
    assert not res.failed, [(x.filename, x.error) for x in res.failed]
    names = {f.name.lower() for f in ctx.repos.list_files(r.id)}
    assert {"tqdm", "colorama"} <= names
    assert all(e.status == CompatStatus.COMPATIBLE for e in ctx.compat.check_files(ctx.repos.list_files(r.id), win))
    assert all(f.hash_origin == "index" for f in ctx.repos.list_files(r.id)), "hashes must come from the index"
    assert ctx.deps.analyze(ctx.repos.list_files(r.id), ["tqdm"], win).ok


def test_collect_from_pypi_then_offline_install_and_import(ctx, host, host_target, tmp_path):
    r = ctx.repos.create_repository("real", host_target)
    res = ctx.downloader.collect(["requests==2.32.3"], r.id, host, host_target, DownloadOptions(retries=2))
    assert not res.failed
    pk = Path(r.path) / "packages"
    # from here on no network is needed: pip is told --no-index
    plan = ctx.installer.plan(host, pk, ["requests"], new_venv=tmp_path / "venv")
    assert plan.can_install, plan.missing
    out = ctx.installer.execute(plan, confirmed=True)
    assert out.ok, out.error
    py = subprocess.run([out.python_path, "-c", "import requests, urllib3, idna, certifi; print(requests.__version__)"],
                        capture_output=True, text=True)
    assert py.stdout.strip() == "2.32.3"
