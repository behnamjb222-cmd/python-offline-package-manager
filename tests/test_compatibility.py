import pytest

from app.core.models import CompatStatus, FileRecord, TargetSpec
from app.services.compatibility_checker import CompatibilityChecker, marker_environment, pip_platforms, target_tags
from app.utils.dist_utils import classify_filename

C = CompatibilityChecker()


def rec(fn, rp="", rd=None):
    k, n, v, t = classify_filename(fn)
    return FileRecord(1, 1, n, v, fn, k, "x", 1, tags=t, requires_python=rp, requires_dist=rd or [])


@pytest.mark.parametrize("fn,spec,expected", [
    ("numpy-1.26.4-cp312-cp312-win_amd64.whl", TargetSpec("3.12", "windows", "x86_64"), CompatStatus.COMPATIBLE),
    ("numpy-1.26.4-cp312-cp312-win_amd64.whl", TargetSpec("3.11", "windows", "x86_64"), CompatStatus.INCOMPATIBLE),
    ("numpy-1.26.4-cp312-cp312-win_amd64.whl", TargetSpec("3.12", "linux", "x86_64"), CompatStatus.INCOMPATIBLE),
    ("numpy-1.26.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl", TargetSpec("3.12", "linux", "x86_64"), CompatStatus.COMPATIBLE),
    ("numpy-1.26.4-cp312-cp312-manylinux_2_17_x86_64.whl", TargetSpec("3.12", "linux", "arm64"), CompatStatus.INCOMPATIBLE),
    ("six-1.16.0-py2.py3-none-any.whl", TargetSpec("3.12", "macos", "arm64"), CompatStatus.COMPATIBLE),
    ("cryptography-42-cp39-abi3-win_amd64.whl", TargetSpec("3.13", "windows", "x86_64"), CompatStatus.COMPATIBLE),
    ("pkg-1.0-cp312-cp312-macosx_11_0_arm64.whl", TargetSpec("3.12", "macos", "arm64"), CompatStatus.COMPATIBLE),
    ("pkg-1.0-cp312-cp312-macosx_11_0_arm64.whl", TargetSpec("3.12", "macos", "x86_64"), CompatStatus.INCOMPATIBLE),
    ("foo-1.0.tar.gz", TargetSpec("3.12", "linux", "x86_64"), CompatStatus.UNKNOWN),
])
def test_wheel_tag_compatibility(fn, spec, expected):
    assert C.check_file(rec(fn), spec).status == expected


def test_not_decided_by_name_alone():
    """A file named like a 'win' wheel but with 'any' tag is still universal; judgement uses tags."""
    assert C.check_file(rec("win_helper-1.0-py3-none-any.whl"), TargetSpec("3.12", "linux", "x86_64")).status == CompatStatus.COMPATIBLE


def test_requires_python_is_enforced():
    r = C.check_file(rec("x-1.0-py3-none-any.whl", rp=">=3.99"), TargetSpec("3.12", "linux", "x86_64"))
    assert r.status == CompatStatus.INCOMPATIBLE and "Requires-Python" in r.reasons[0]


def test_missing_dependency_status_and_markers():
    spec_lin, spec_win = TargetSpec("3.12", "linux", "x86_64"), TargetSpec("3.12", "windows", "x86_64")
    alpha = rec("alpha-1.0-py3-none-any.whl", rd=["beta>=1.0", "colorama; sys_platform == 'win32'"])
    beta = rec("beta-1.2-py3-none-any.whl")
    on_linux = {e.filename: e for e in C.check_files([alpha, beta], spec_lin)}
    assert on_linux[alpha.filename].status == CompatStatus.COMPATIBLE             # colorama marker is false on linux
    on_win = {e.filename: e for e in C.check_files([alpha, beta], spec_win)}
    assert on_win[alpha.filename].status == CompatStatus.MISSING_DEPENDENCY
    assert "colorama" in on_win[alpha.filename].reasons[0]
    no_beta = C.check_files([alpha], spec_lin)[0]
    assert no_beta.status == CompatStatus.MISSING_DEPENDENCY and "beta" in no_beta.reasons[0]
    old_beta = C.check_files([alpha, rec("beta-0.5-py3-none-any.whl")], spec_lin)
    assert old_beta[0].status == CompatStatus.MISSING_DEPENDENCY                  # version constraint not satisfied


def test_summary_and_report(tmp_path):
    spec = TargetSpec("3.12", "linux", "x86_64")
    es = C.check_files([rec("a-1-py3-none-any.whl"), rec("b-1-cp312-cp312-win_amd64.whl"), rec("c-1.tar.gz")], spec)
    s = C.summarize(es)
    assert s == {"COMPATIBLE": 1, "INCOMPATIBLE": 1, "UNKNOWN": 1, "MISSING_DEPENDENCY": 0}
    out = C.export_report(C.report(es, spec, "r"), tmp_path / "rep.json")
    assert out.exists()


def test_platform_tag_generation():
    assert pip_platforms("windows", "x86_64") == ["win_amd64"]
    assert "manylinux2014_aarch64" in pip_platforms("linux", "arm64")
    assert any(t.startswith("macosx_") and t.endswith("arm64") for t in pip_platforms("macos", "arm64"))
    assert target_tags(TargetSpec("3.12", "windows", "x86_64"))[0] == "cp312-cp312-win_amd64"
    assert marker_environment(TargetSpec("3.12", "windows", "x86_64"))["sys_platform"] == "win32"
