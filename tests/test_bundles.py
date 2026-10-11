import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from app.core.exceptions import (ChecksumMismatchError, MissingDependencyError, OverwriteBlockedError, ValidationError)
from app.utils.hashing import sha256_file


def test_bundle_structure_manifest_and_checksums(ctx, filled_repo, tmp_path):
    res = ctx.bundles.create_bundle(filled_repo.id, tmp_path / "out", requirements=["alpha"])
    assert res.file_count == 2 and res.paths[0].suffix == ".zip" and res.sha256 == sha256_file(res.paths[0])
    with zipfile.ZipFile(res.paths[0]) as zf:
        names = set(zf.namelist())
        assert {"packages/alpha-1.0-py3-none-any.whl", "packages/beta-1.2-py3-none-any.whl", "manifests/requirements.txt",
                "manifests/environment.json", "metadata/bundle.json", "metadata/checksums.json",
                "reports/compatibility_report.json", "install_offline.py", "README_FA.md", "README_EN.md"} <= names
        assert "packages/beta-0.9-py3-none-any.whl" not in names, "only the needed packages are included"
        bj = json.loads(zf.read("metadata/bundle.json"))
        assert bj["contains_python_interpreter"] is False and "NOT" in bj["note"]
        assert "alpha==1.0" in zf.read("manifests/requirements.txt").decode()
        assert "Python interpreter" in zf.read("README_EN.md").decode() and "مفسر" in zf.read("README_FA.md").decode()
        sums = json.loads(zf.read("metadata/checksums.json"))
        assert sums["packages/alpha-1.0-py3-none-any.whl"] == sha256_file(filled_repo.packages_dir / "alpha-1.0-py3-none-any.whl")
    assert ctx.store.count_bundles() == 1


def test_all_files_bundle_and_estimate(ctx, filled_repo, tmp_path, host_target):
    res = ctx.bundles.create_bundle(filled_repo.id, tmp_path / "all.zip")
    assert res.file_count == 4
    assert ctx.bundles.estimate(filled_repo.id, ["alpha"], host_target) < ctx.bundles.estimate(filled_repo.id, None, host_target)


def test_incomplete_dependencies_block_bundle_unless_allowed(ctx, repo, index, tmp_path):
    ctx.repos.add_file(repo.id, index / "alpha-1.0-py3-none-any.whl")
    with pytest.raises(MissingDependencyError):
        ctx.bundles.create_bundle(repo.id, tmp_path / "x.zip", requirements=["alpha"])
    assert not list(tmp_path.glob("x.zip*"))
    res = ctx.bundles.create_bundle(repo.id, tmp_path / "x.zip", requirements=["alpha"], allow_incomplete=True)
    assert res.warnings


def test_split_bundle_and_extract_from_parts(ctx, filled_repo, tmp_path):
    res = ctx.bundles.create_bundle(filled_repo.id, tmp_path / "s.zip", split_bytes=3000)
    assert len(res.paths) > 1 and (tmp_path / "s.zip.parts.json").exists()
    out = ctx.bundles.extract_bundle(res.paths[0], tmp_path / "joined_out")
    assert out.ok and (out.dest / "packages").is_dir()


def test_extract_validates_and_detects_tampering(ctx, filled_repo, tmp_path):
    res = ctx.bundles.create_bundle(filled_repo.id, tmp_path / "b.zip")
    ex = ctx.bundles.extract_bundle(res.paths[0], tmp_path / "ex")
    assert ex.ok and ctx.integrity.validate_manifest(ex.dest) == []
    with pytest.raises(OverwriteBlockedError):
        ctx.bundles.extract_bundle(res.paths[0], tmp_path / "ex")                   # no silent overwrite
    (ex.dest / "packages" / "beta-1.2-py3-none-any.whl").write_bytes(b"x")
    (ex.dest / "packages" / "extra-1.0-py3-none-any.whl").write_bytes(b"y")
    problems = ctx.integrity.validate_manifest(ex.dest)
    assert any("checksum mismatch" in p for p in problems) and any("unlisted" in p for p in problems)
    (ex.dest / "metadata" / "bundle.json").write_text("{}")
    assert any("missing field" in p for p in ctx.integrity.validate_manifest(ex.dest))


def test_import_bundle_into_other_repository_and_tampered_bundle_rejected(ctx, filled_repo, tmp_path):
    res = ctx.bundles.create_bundle(filled_repo.id, tmp_path / "b.zip")
    target = ctx.repos.create_repository("offline_machine")
    r = ctx.bundles.import_bundle(res.paths[0], target.id)
    assert r == {"added": 4, "skipped": 0} and ctx.repos.get(target.id).target_python == filled_repo.target_python
    assert ctx.bundles.import_bundle(res.paths[0], target.id) == {"added": 0, "skipped": 4}
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(res.paths[0]) as zin, zipfile.ZipFile(bad, "w") as zout:
        for i in zin.infolist():
            data = zin.read(i)
            zout.writestr(i, b"tampered" if i.filename == "packages/beta-1.2-py3-none-any.whl" else data)
    with pytest.raises(ChecksumMismatchError):
        ctx.bundles.import_bundle(bad, ctx.repos.create_repository("other2").id)


def test_bundle_needs_a_target(ctx, tmp_path, index):
    r = ctx.repos.create_repository("notarget")
    ctx.repos.add_file(r.id, index / "beta-1.2-py3-none-any.whl")
    with pytest.raises(ValidationError):
        ctx.bundles.create_bundle(r.id, tmp_path / "t.zip")


def test_unicode_paths_in_bundle_output_and_extraction(ctx, filled_repo, tmp_path):
    out = tmp_path / "خروجی ها" / "بسته ی من"
    res = ctx.bundles.create_bundle(filled_repo.id, out / "bundle.zip")
    ex = ctx.bundles.extract_bundle(res.paths[0], tmp_path / "استخراج شده" / "with space")
    assert ex.ok


def test_standalone_install_script_in_a_clean_venv(ctx, filled_repo, tmp_path):
    """The generated install_offline.py (stdlib only) installs from the bundle with --no-index into a NEW venv."""
    res = ctx.bundles.create_bundle(filled_repo.id, tmp_path / "b.zip", requirements=["alpha"])
    ex = ctx.bundles.extract_bundle(res.paths[0], tmp_path / "bundle dir")
    venv = tmp_path / "new venv"
    run = lambda *a: subprocess.run([sys.executable, str(ex.dest / "install_offline.py"), *a], capture_output=True, text=True)
    dry = run("--dry-run", "--yes")
    assert dry.returncode == 0 and "Would install" in dry.stdout and not venv.exists()
    r = run("--venv", str(venv), "--yes")
    assert r.returncode == 0, r.stdout + r.stderr
    py = venv / "bin" / "python"
    out = subprocess.run([str(py), "-c", "import alpha, beta; print(alpha.VERSION, beta.VERSION)"], capture_output=True, text=True)
    assert out.stdout.strip() == "1.0 1.2"
    (ex.dest / "packages" / "alpha-1.0-py3-none-any.whl").write_bytes(b"tampered")
    bad = run("--venv", str(tmp_path / "v2"), "--yes")
    assert bad.returncode == 2 and "INTEGRITY" in bad.stdout and not (tmp_path / "v2").exists()
    nonconfirm = subprocess.run([sys.executable, str(ex.dest / "install_offline.py"), "--skip-verify", "--venv", str(tmp_path / "v3")],
                                input="no\n", capture_output=True, text=True)
    assert nonconfirm.returncode == 3 and not (tmp_path / "v3").exists()
