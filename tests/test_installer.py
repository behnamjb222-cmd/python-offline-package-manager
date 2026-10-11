import subprocess
from pathlib import Path

import pytest

from app.core.exceptions import (ChecksumMismatchError, ConfirmationRequiredError, EnvironmentChangedError,
                                 MissingDependencyError, ValidationError)
from app.core.models import CompatStatus, InstallOptions


def pk(repo) -> Path:
    return Path(repo.path) / "packages"


def test_plan_shows_packages_and_nothing_is_changed(ctx, host, filled_repo, tmp_path):
    venv = tmp_path / "pl an" / "venv"
    plan = ctx.installer.plan(host, pk(filled_repo), ["alpha"], new_venv=venv)
    assert plan.can_install and {p.name for p in plan.packages} == {"alpha", "beta"}
    assert all(p.status == CompatStatus.COMPATIBLE for p in plan.packages)
    assert not venv.exists(), "planning must not create the venv"
    text = ctx.installer.describe(plan)
    assert "alpha 1.0" in text and "--no-index" in text and str(venv) in text
    assert "نصب آفلاین" in ctx.installer.describe(plan, "fa")


def test_install_requires_explicit_confirmation(ctx, host, filled_repo, tmp_path):
    plan = ctx.installer.plan(host, pk(filled_repo), ["alpha"], new_venv=tmp_path / "v")
    with pytest.raises(ConfirmationRequiredError):
        ctx.installer.execute(plan)
    assert not (tmp_path / "v").exists()


def test_missing_dependency_is_reported_before_install(ctx, host, repo, index, tmp_path):
    ctx.repos.add_file(repo.id, index / "alpha-1.0-py3-none-any.whl")              # beta is NOT in the repo
    plan = ctx.installer.plan(host, pk(repo), ["alpha"], new_venv=tmp_path / "v")
    assert not plan.can_install and plan.missing and any("beta" in m for m in plan.missing)
    with pytest.raises(MissingDependencyError):
        ctx.installer.execute(plan, confirmed=True)
    assert not (tmp_path / "v").exists()
    nope = ctx.installer.plan(host, pk(repo), ["alpha>=9"], new_venv=tmp_path / "w")
    assert nope.missing


def test_real_offline_install_into_new_venv_with_spaces(ctx, host, filled_repo, tmp_path):
    venv = tmp_path / "my envs" / "proj one"
    plan = ctx.installer.plan(host, pk(filled_repo), ["alpha"], new_venv=venv)
    logs = []
    res = ctx.installer.execute(plan, confirmed=True, on_log=lambda l, m: logs.append(m))
    assert res.ok, res.error
    assert res.per_package == {"alpha": "1.0", "beta": "1.2"}
    assert "No broken requirements" in res.pip_check
    assert Path(res.report_path).exists() and "alpha" in Path(res.report_path).read_text()
    out = subprocess.run([res.python_path, "-c", "import alpha; print(alpha.VERSION)"], capture_output=True, text=True)
    assert out.stdout.strip() == "1.0"
    assert ctx.installer.verify_installation(res.python_path, plan) == {"alpha": "1.0", "beta": "1.2"}
    assert "alpha" not in {p.name.lower() for p in ctx.scanner.scan(host)}, "main environment untouched"
    assert any("Processing" in m or "Installing" in m or "Successfully" in m for m in logs)


def test_install_into_existing_venv(ctx, host, filled_repo, tmp_path):
    venv = ctx.envs.create_venv(host, tmp_path / "existing")
    plan = ctx.installer.plan(venv, pk(filled_repo), ["beta==0.9"] if False else ["beta"])
    res = ctx.installer.execute(plan, confirmed=True)
    assert res.ok and res.per_package["beta"] == "1.2"
    again = ctx.installer.plan(venv, pk(filled_repo), ["beta"])
    assert not again.packages and any("already satisfied" in w for w in again.warnings)


def test_options_are_explained_in_warnings(ctx, host, filled_repo, tmp_path):
    plan = ctx.installer.plan(host, pk(filled_repo), ["alpha"], InstallOptions(no_deps=True, only_binary=True),
                              new_venv=tmp_path / "o")
    assert any("--no-deps" in w for w in plan.warnings) and any("--only-binary" in w for w in plan.warnings)
    assert {p.name for p in plan.packages} == {"alpha"}
    sys_plan = ctx.installer.plan(host, pk(filled_repo), ["alpha"])
    assert (host.kind == "venv") or any("system-wide" in w for w in sys_plan.warnings)


def test_environment_change_and_tampered_file_block_execution(ctx, host, filled_repo, tmp_path):
    plan = ctx.installer.plan(host, pk(filled_repo), ["alpha"], new_venv=tmp_path / "v")
    plan.fingerprint = "something-else"
    with pytest.raises(EnvironmentChangedError):
        ctx.installer.execute(plan, confirmed=True)
    hashes = {f.filename: f.sha256 for f in ctx.repos.list_files(filled_repo.id)}
    plan2 = ctx.installer.plan(host, pk(filled_repo), ["alpha"], new_venv=tmp_path / "v2", expected_hashes=hashes)
    f = pk(filled_repo) / "beta-1.2-py3-none-any.whl"
    f.unlink(); f.write_bytes(b"tampered")
    with pytest.raises(ChecksumMismatchError):
        ctx.installer.execute(plan2, confirmed=True)
    assert not (tmp_path / "v2").exists()


def test_failed_install_is_reported_and_retry_works(ctx, host, filled_repo, tmp_path):
    plan = ctx.installer.plan(host, pk(filled_repo), ["alpha"], new_venv=tmp_path / "rv")
    res = ctx.installer.execute(plan, confirmed=True)
    assert res.ok
    res.per_package["beta"] = "FAILED"; res.ok = False                                # simulate a failed package
    retry = ctx.installer.retry_failed(plan, res, confirmed=True)
    assert retry.ok or retry.per_package["beta"] != "FAILED"
    with pytest.raises(ConfirmationRequiredError):
        ctx.installer.retry_failed(plan, res)


def test_plan_validation(ctx, host, filled_repo, tmp_path):
    with pytest.raises(ValidationError):
        ctx.installer.plan(host, tmp_path / "does-not-exist", ["alpha"])
    with pytest.raises(ValidationError):
        ctx.installer.plan(host, pk(filled_repo), [])
