import json
import os
import shutil
from pathlib import Path

import pytest

from app.bootstrap import create_context
from app.core.exceptions import (ChecksumMismatchError, ConfirmationRequiredError, CorruptFileError, ValidationError)
from app.utils.hashing import sha256_bytes, sha256_file
from helpers import build_wheel


def test_create_repository_layout_and_metadata(ctx, repo):
    base = Path(repo.path)
    for sub in ("packages", "metadata", "manifests", "logs", "exports"):
        assert (base / sub).is_dir()
    meta = json.loads((base / "metadata" / "repository.json").read_text())
    assert meta["name"] == "testrepo" and meta["uid"] == repo.uid
    with pytest.raises(ValidationError):
        ctx.repos.create_repository("testrepo")
    with pytest.raises(ValidationError):
        ctx.repos.create_repository("bad/name")


def test_add_file_registers_hash_and_metadata(ctx, repo, index):
    rec = ctx.repos.add_file(repo.id, index / "alpha-1.0-py3-none-any.whl", source_url="file://x")
    assert rec.sha256 == sha256_file(index / "alpha-1.0-py3-none-any.whl")
    assert rec.name == "alpha" and rec.kind == "wheel" and rec.requires_dist[0].startswith("beta")
    assert (Path(repo.path) / "packages" / rec.filename).exists()
    pj = json.loads((Path(repo.path) / "metadata" / "packages.json").read_text())
    assert pj[0]["source_url"] == "file://x" and pj[0]["sha256"] == rec.sha256
    again = ctx.repos.add_file(repo.id, index / "alpha-1.0-py3-none-any.whl")      # idempotent
    assert again.id == rec.id and ctx.repos.get(repo.id).files == 1


def test_sha256_helper_and_expected_hash_mismatch(ctx, repo, index, tmp_path):
    f = tmp_path / "x.bin"; f.write_bytes(b"hello")
    assert sha256_file(f) == sha256_bytes(b"hello")
    with pytest.raises(ChecksumMismatchError):
        ctx.repos.add_file(repo.id, index / "beta-1.2-py3-none-any.whl", expected_sha256="0" * 64)
    assert ctx.repos.get(repo.id).files == 0                                        # nothing registered


def test_rejects_corrupt_and_unsupported_files(ctx, repo, tmp_path):
    bad = tmp_path / "bad-1.0-py3-none-any.whl"; bad.write_bytes(b"not a zip")
    with pytest.raises(CorruptFileError):
        ctx.repos.add_file(repo.id, bad)
    txt = tmp_path / "notes.txt"; txt.write_text("x")
    with pytest.raises(ValidationError):
        ctx.repos.add_file(repo.id, txt)


def test_duplicate_content_detected_and_cross_repo_dedup(ctx, repo, index, host_target):
    src = index / "beta-1.2-py3-none-any.whl"
    ctx.repos.add_file(repo.id, src)
    twin = index / "betatwin-1.2-py3-none-any.whl"
    shutil.copy(src, twin)                                                          # same bytes, other name
    ctx.repos.add_file(repo.id, twin)
    assert ctx.repos.find_duplicates(repo.id) == [sorted(["beta-1.2-py3-none-any.whl", "betatwin-1.2-py3-none-any.whl"])] \
        or len(ctx.repos.find_duplicates(repo.id)[0]) == 2
    other = ctx.repos.create_repository("other", host_target)
    rec = ctx.repos.add_file(other.id, src)
    assert len(list((ctx.repos.blobs_dir).glob(f"*/{rec.sha256}"))) == 1            # one physical blob for 3 references
    assert ctx.store.checksum_refs(rec.sha256) == 3


def test_hard_delete_respects_references_and_needs_confirmation(ctx, repo, index, host_target):
    src = index / "beta-1.2-py3-none-any.whl"
    r1 = ctx.repos.add_file(repo.id, src)
    other = ctx.repos.create_repository("other", host_target)
    ctx.repos.add_file(other.id, src)
    with pytest.raises(ConfirmationRequiredError):
        ctx.repos.remove_file(repo.id, r1.id, hard=True)
    ctx.repos.remove_file(repo.id, r1.id, hard=True, confirmed=True)
    assert ctx.repos.blob_path(r1.sha256).exists(), "blob is still referenced by the other repository"
    r2 = ctx.repos.list_files(other.id)[0]
    ctx.repos.remove_file(other.id, r2.id, hard=True, confirmed=True)
    assert not ctx.repos.blob_path(r1.sha256).exists(), "last reference gone -> blob removed"


def test_logical_remove_hides_file_from_pip_folder_and_can_restore(ctx, repo, index):
    rec = ctx.repos.add_file(repo.id, index / "beta-1.2-py3-none-any.whl")
    ctx.repos.remove_file(repo.id, rec.id)
    assert not (Path(repo.path) / "packages" / rec.filename).exists()
    assert ctx.repos.list_files(repo.id) == [] and ctx.repos.get(repo.id).files == 0
    ctx.repos.restore_file(repo.id, rec.id)
    assert (Path(repo.path) / "packages" / rec.filename).exists() and len(ctx.repos.list_files(repo.id)) == 1


def test_delete_repository_requires_confirmation(ctx, filled_repo):
    with pytest.raises(ConfirmationRequiredError):
        ctx.repos.delete_repository(filled_repo.id)
    ctx.repos.delete_repository(filled_repo.id, confirmed=True)
    assert ctx.repos.list() == [] and not list(ctx.repos.blobs_dir.glob("*/*"))


def test_health_check_finds_missing_unknown_modified(ctx, filled_repo):
    pk = Path(filled_repo.path) / "packages"
    (pk / "colorama-0.4-py3-none-any.whl").unlink()
    (pk / "stray.txt").write_text("?")
    h = ctx.repos.health_check(filled_repo.id)
    assert h.missing == ["colorama-0.4-py3-none-any.whl"] and h.unknown_files == ["stray.txt"] and h.status == "invalid"
    assert (pk / "stray.txt").exists(), "unknown files must never be deleted automatically"


def test_filters_search_and_version(ctx, filled_repo):
    assert [f.name for f in ctx.repos.list_files(filled_repo.id, name="bet")] == ["beta", "beta"]
    assert [f.version for f in ctx.repos.list_files(filled_repo.id, name="beta", version="1.")] == ["1.2"]
    assert all(f.kind == "wheel" for f in ctx.repos.list_files(filled_repo.id, kind="wheel"))


def test_recovery_after_database_loss(ctx, filled_repo, tmp_path):
    ctx.repos.write_metadata(filled_repo.id)
    root = ctx.data_root
    ctx.close()
    for f in root.glob("popm.db*"):
        f.unlink()                                                                   # simulate a lost/corrupt database
    c2 = create_context(root)
    found = c2.repos.discover_repositories()
    assert [r.name for r in found] == ["testrepo"] and found[0].files == 4
    rec = c2.repos.list_files(found[0].id, name="alpha")[0]
    assert rec.requires_dist and rec.sha256
    c2.close()


def test_backup_and_restore_metadata(ctx, filled_repo):
    bk = ctx.repos.backup_metadata(filled_repo.id)
    ctx.store.db.execute("DELETE FROM package_files WHERE repo_id=?", (filled_repo.id,))
    assert ctx.repos.get(filled_repo.id).files == 0
    with pytest.raises(ConfirmationRequiredError):
        ctx.repos.restore_metadata(filled_repo.id, bk)
    assert ctx.repos.restore_metadata(filled_repo.id, bk, confirmed=True) == 4
    assert ctx.repos.health_check(filled_repo.id).ok


def test_unicode_repo_name_and_unicode_source_dir(ctx, index, tmp_path, host_target):
    uni = tmp_path / "پوشه ی ورودی" / "ünï"
    uni.mkdir(parents=True)
    w = build_wheel(uni, "alpha", "2.0")
    r = ctx.repos.create_repository("مخزن آزمایشی", host_target, base_path=tmp_path / "مسیر با فاصله")
    rec = ctx.repos.add_file(r.id, w)
    assert (Path(r.path) / "packages" / rec.filename).exists() and "مخزن" in r.path
    assert ctx.repos.get(r.id).name == "مخزن آزمایشی"


def test_rename_is_display_only(ctx, repo):
    r = ctx.repos.rename(repo.id, "renamed")
    assert r.name == "renamed" and r.path == repo.path


def test_storage_limit_blocks_adds(ctx, repo, index):
    from app.core.exceptions import InsufficientDiskSpaceError
    ctx.settings.storage_limit_mb = 0
    ctx.repos.add_file(repo.id, index / "beta-1.2-py3-none-any.whl")
    # emulate a tiny limit by patching used bytes
    ctx.settings.storage_limit_mb = 1
    ctx.repos.total_blob_bytes = lambda: 1024 * 1024  # type: ignore[method-assign]
    with pytest.raises(InsufficientDiskSpaceError):
        ctx.repos.add_file(repo.id, index / "beta-0.9-py3-none-any.whl")
