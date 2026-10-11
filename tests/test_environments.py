import sys
from pathlib import Path

import pytest

from app.core.exceptions import PythonNotFoundError
from app.services.environment_manager import normalize_arch


def test_probe_current_python(ctx):
    env = ctx.envs.probe(sys.executable)
    assert env.valid and env.version.startswith(f"{sys.version_info.major}.{sys.version_info.minor}")
    assert env.pip_version and env.tags and env.os in {"linux", "windows", "macos"}
    assert env.marker_env.get("python_version") == env.short_version


def test_discover_finds_current_and_persists(ctx):
    found = ctx.envs.discover()
    assert found, "at least the running interpreter must be found"
    assert any(Path(e.python_path).exists() for e in found)
    assert len(ctx.envs.list()) == len(found)
    keys = [(e.version, e.kind) for e in found]
    assert len(set(e.python_path for e in found)) == len(found)  # no duplicate paths


def test_add_manual_and_invalid_path(ctx, tmp_path):
    env = ctx.envs.add_manual(sys.executable)
    assert env.manual and env.id
    with pytest.raises(PythonNotFoundError):
        ctx.envs.add_manual(tmp_path / "nope" / "python")


def test_vanished_environment_is_marked_invalid(ctx, tmp_path):
    fake = tmp_path / "python_fake"
    fake.write_text("#!/bin/sh\nexit 1\n")
    fake.chmod(0o755)
    from app.core.models import EnvironmentInfo
    e = EnvironmentInfo(str(fake), "3.12.0", "system", "linux", "x86_64", valid=True)
    ctx.store.upsert_env(e)
    envs = ctx.envs.validate_all()
    assert [x for x in envs if x.python_path == str(fake)][0].valid is False


def test_pip_command_is_bound_to_chosen_interpreter():
    from app.utils.pip_utils import pip_cmd
    assert pip_cmd("/x/python", "list")[:3] == ["/x/python", "-m", "pip"]


def test_normalize_arch():
    assert normalize_arch("AMD64") == "x86_64" and normalize_arch("aarch64") == "arm64"
    assert normalize_arch("AMD64", 32) == "x86"


def test_venv_creation_and_paths_with_spaces(ctx, host, tmp_path):
    venv = ctx.envs.create_venv(host, tmp_path / "my venv" / "env one")
    assert venv.valid and venv.kind == "venv" and " " in venv.python_path
