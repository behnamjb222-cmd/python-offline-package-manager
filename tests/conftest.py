from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from helpers import build_sdist, build_wheel  # noqa: E402

from app.bootstrap import create_context  # noqa: E402
from app.core.models import TargetSpec  # noqa: E402


@pytest.fixture()
def ctx(tmp_path):
    c = create_context(tmp_path / "data")
    c.settings.retries = 1
    c.settings.timeout = 5
    yield c
    c.close()


@pytest.fixture()
def index(tmp_path) -> Path:
    """A local 'package index' folder (find-links) with tiny wheels - no network anywhere."""
    d = tmp_path / "index"
    build_wheel(d, "alpha", "1.0", requires=["beta>=1.0", "colorama; sys_platform == 'win32'"])
    build_wheel(d, "beta", "1.2")
    build_wheel(d, "beta", "0.9")
    build_wheel(d, "colorama", "0.4")
    build_wheel(d, "winonly", "1.0", tag="cp312-cp312-win_amd64")
    build_wheel(d, "futuristic", "1.0", requires_python=">=3.99")
    build_sdist(d, "foo", "1.0")
    return d


@pytest.fixture()
def host(ctx):
    env = ctx.envs.probe(sys.executable)
    assert env.valid, env.error
    env.id = ctx.store.upsert_env(env)
    return env


@pytest.fixture()
def host_target(host) -> TargetSpec:
    return host.to_target()


@pytest.fixture()
def win_target() -> TargetSpec:
    return TargetSpec("3.12", "windows", "x86_64")


@pytest.fixture()
def repo(ctx, host_target):
    return ctx.repos.create_repository("testrepo", host_target)


@pytest.fixture()
def filled_repo(ctx, repo, index):
    for f in sorted(index.glob("*.whl")):
        if f.name.startswith(("winonly", "futuristic")):
            continue
        ctx.repos.add_file(repo.id, f)
    return ctx.repos.get(repo.id)
