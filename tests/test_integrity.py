import json
import zipfile
from pathlib import Path

import pytest

from app.core.exceptions import OverwriteBlockedError, UnsafeArchiveError, CorruptFileError
from app.utils.archive_utils import join_parts, resolve_member, safe_extract_zip, split_file, check_zip
from app.utils.subprocess_utils import CancelToken, redact, run_command


def test_verify_repository_detects_modified_and_missing(ctx, filled_repo):
    ok = ctx.integrity.verify_repository(filled_repo.id)
    assert ok.clean and ok.checked == 4 and ctx.repos.get(filled_repo.id).validation_status == "valid"
    pk = Path(filled_repo.path) / "packages"
    f = pk / "beta-1.2-py3-none-any.whl"
    f.unlink()                                  # hard link: only this path is replaced, the blob stays intact
    f.write_bytes(b"tampered")
    (pk / "colorama-0.4-py3-none-any.whl").unlink()
    rep = ctx.integrity.verify_repository(filled_repo.id)
    assert rep.modified == ["beta-1.2-py3-none-any.whl"] and rep.missing == ["colorama-0.4-py3-none-any.whl"]
    assert rep.status == "invalid" and ctx.repos.get(filled_repo.id).validation_status == "invalid"
    assert ctx.repos.blob_path(ctx.repos.list_files(filled_repo.id, name="beta")[1].sha256).exists()


def test_provenance_records_source(ctx, filled_repo):
    p = ctx.integrity.provenance(filled_repo.id)
    assert len(p) == 4 and all(x["sha256"] and x["downloaded_at"] for x in p)


@pytest.mark.parametrize("name", ["../evil.txt", "a/../../evil.txt", "/abs/evil.txt", "C:\\evil.txt", "..\\evil.txt", "ok/\x00x"])
def test_zip_slip_names_rejected(tmp_path, name):
    with pytest.raises(UnsafeArchiveError):
        resolve_member(tmp_path.resolve(), name)


def test_safe_extract_blocks_zip_slip_and_overwrite(tmp_path):
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("good.txt", "ok")
        zf.writestr("../escaped.txt", "bad")
    dest = tmp_path / "out"
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(evil, dest)
    assert not (tmp_path / "escaped.txt").exists() and not (dest / "good.txt").exists(), "nothing extracted at all"
    good = tmp_path / "good.zip"
    with zipfile.ZipFile(good, "w") as zf:
        zf.writestr("a/b.txt", "1")
    safe_extract_zip(good, dest)
    with pytest.raises(OverwriteBlockedError):
        safe_extract_zip(good, dest)
    safe_extract_zip(good, dest, overwrite=True)


def test_symlink_entries_rejected(tmp_path):
    z = tmp_path / "s.zip"
    with zipfile.ZipFile(z, "w") as zf:
        info = zipfile.ZipInfo("link")
        info.external_attr = (0o120777 << 16)
        zf.writestr(info, "/etc/passwd")
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(z, tmp_path / "o")


def test_corrupt_zip_detected(tmp_path):
    z = tmp_path / "c.zip"
    z.write_bytes(b"PK\x03\x04garbage")
    with pytest.raises(CorruptFileError):
        check_zip(z)
    assert ctx_problems(z)


def ctx_problems(z):
    from app.services.integrity_manager import IntegrityManager
    return IntegrityManager(None, None, None).validate_zip(z)


def test_split_and_join_roundtrip(tmp_path):
    f = tmp_path / "big.zip"
    f.write_bytes(bytes(range(256)) * 100)
    original = f.read_bytes()
    parts = split_file(f, 5000)
    assert len(parts) == 6 and not f.exists()
    out = join_parts(parts[2], tmp_path / "joined.zip")
    assert out.read_bytes() == original


def test_run_command_never_uses_shell_and_can_be_cancelled(tmp_path):
    marker = tmp_path / "pwned"
    r = run_command(["python3", "-c", "import sys;print(sys.argv[1])", f"; touch {marker}"])
    assert r.ok and not marker.exists()
    with pytest.raises(TypeError):
        run_command("echo hi")  # type: ignore[arg-type]
    import threading, time
    tok = CancelToken()
    threading.Timer(0.5, tok.cancel).start()
    t0 = time.monotonic()
    res = run_command(["python3", "-c", "import time; time.sleep(30)"], cancel=tok)
    assert res.cancelled and time.monotonic() - t0 < 10


def test_secrets_are_redacted(ctx):
    assert "hunter2" not in redact("pip --index-url https://bob:hunter2@host/simple password=hunter2")
    op = ctx.logs.start("download", "proxy http://u:s3cret@proxy:8080")
    op.info("using https://u:s3cret@proxy:8080 token=abc123")
    op.finish("success", "done")
    logs = " ".join(r["message"] for r in ctx.store.list_logs())
    assert "s3cret" not in logs and "abc123" not in logs
    assert "s3cret" not in (ctx.data_root / "logs" / "popm.log").read_text()
    out = ctx.logs.export(ctx.data_root / "e.json")
    assert json.loads(out.read_text()) and "s3cret" not in out.read_text()
    ctx.logs.export(ctx.data_root / "e.txt")


def test_settings_validation_and_no_password_on_disk(ctx):
    from app.config import Settings
    from app.core.exceptions import InvalidProxyError, ValidationError
    ctx.settings.proxy_url = "http://proxy.local:8080"
    ctx.settings.proxy_user = "bob"
    ctx.settings.proxy_password = "p@ss"
    ctx.save_settings()
    raw = ctx.settings_path.read_text()
    assert "p@ss" not in raw and "proxy_password" not in raw
    assert "bob:p%40ss@proxy.local" in ctx.settings.proxy_env()["HTTPS_PROXY"]
    assert Settings.load(ctx.settings_path).proxy_password == ""
    assert ctx.settings.ssl_verify is True, "SSL verification must default to ON"
    bad = Settings(proxy_url="socks5://localhost:1080")   # SOCKS unsupported by the built-in downloader
    with pytest.raises(InvalidProxyError):
        bad.validate()
    with pytest.raises(ValidationError):
        Settings(retries=99).validate()
