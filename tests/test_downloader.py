import http.server
import threading
from pathlib import Path

import pytest

from app.core.exceptions import InsufficientDiskSpaceError, NoCompatibleWheelError, NoInternetError, ValidationError
from app.core.models import DownloadPlan, ResolvedFile
from app.services.package_downloader import DownloadOptions
from app.utils.hashing import sha256_file
from app.utils.subprocess_utils import CancelToken


@pytest.fixture()
def server(index):
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(index), **k)

        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path.startswith("/short/"):                      # claims more bytes than it sends
                data = (index / self.path.split("/", 2)[2]).read_bytes()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data) + 100))
                self.end_headers()
                self.wfile.write(data)
                self.close_connection = True
                return
            super().do_GET()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def opts(index, **kw):
    return DownloadOptions(no_index=True, find_links=[str(index)], retries=1, **kw)


def test_collect_with_dependencies_and_dedup(ctx, host, repo, index, host_target):
    res = ctx.downloader.collect(["alpha"], repo.id, host, host_target, opts(index))
    assert {r.filename for r in res.added} == {"alpha-1.0-py3-none-any.whl", "beta-1.2-py3-none-any.whl"}
    assert all(r.sha256 for r in res.results)
    again = ctx.downloader.collect(["alpha"], repo.id, host, host_target, opts(index))
    assert {r.status for r in again.results} == {"skipped"}                       # nothing downloaded twice
    f = ctx.repos.list_files(repo.id, name="alpha")[0]
    assert f.source_url.startswith("file://") and f.hash_origin in ("index", "computed")


def test_cross_target_adds_target_only_dependency_and_skips_wrong_platform(ctx, host, index, win_target):
    r = ctx.repos.create_repository("win", win_target)
    res = ctx.downloader.collect(["alpha", "winonly"], r.id, host, win_target, opts(index))
    names = {f.filename for f in ctx.repos.list_files(r.id)}
    assert "colorama-0.4-py3-none-any.whl" in names, "marker only true on the target must still be collected"
    assert "winonly-1.0-cp312-cp312-win_amd64.whl" in names and not res.failed
    assert ctx.compat.check_files(ctx.repos.list_files(r.id), win_target)[0].status.value == "COMPATIBLE"


def test_multiple_versions_of_one_package(ctx, host, repo, index, host_target):
    res = ctx.downloader.collect(["beta==0.9", "beta==1.2"], repo.id, host, host_target, opts(index))
    assert sorted(f.version for f in ctx.repos.list_files(repo.id, name="beta")) == ["0.9", "1.2"] and not res.failed


def test_no_compatible_wheel_is_reported(ctx, host, index, win_target, repo, host_target):
    r = ctx.repos.create_repository("lin", host_target)
    with pytest.raises(NoCompatibleWheelError):
        ctx.downloader.collect(["foo"], r.id, host, host_target, opts(index))   # only an sdist exists, sdists not allowed
    # with sdists allowed pip would have to *build* the (deliberately empty) sdist: a different, generic failure
    from app.core.exceptions import POPMError
    with pytest.raises(POPMError) as ei:
        ctx.downloader.collect(["foo"], r.id, host, host_target, DownloadOptions(no_index=True, find_links=[str(index)],
                                                                                retries=0, allow_sdist=True))
    assert not isinstance(ei.value, NoCompatibleWheelError)


def test_http_download_progress_and_hash_verification(ctx, repo, index, server):
    fn = "beta-1.2-py3-none-any.whl"
    f = ResolvedFile("beta", "1.2", fn, f"{server}/{fn}", sha256_file(index / fn), (index / fn).stat().st_size)
    events = []
    res = ctx.downloader.download(DownloadPlan(["beta"], [f]), repo.id, DownloadOptions(retries=0), progress=events.append)
    assert res.results[0].status == "added" and events[-1].bytes_done == f.size and events[-1].speed_bps > 0
    assert ctx.repos.list_files(repo.id)[0].hash_origin == "index"


def test_checksum_mismatch_and_incomplete_download_fail_cleanly(ctx, repo, index, server):
    fn = "beta-1.2-py3-none-any.whl"
    bad = ResolvedFile("beta", "1.2", fn, f"{server}/{fn}", "0" * 64)
    short = ResolvedFile("beta", "0.9", "beta-0.9-py3-none-any.whl", f"{server}/short/beta-0.9-py3-none-any.whl")
    res = ctx.downloader.download(DownloadPlan(["beta"], [bad, short]), repo.id, DownloadOptions(retries=1))
    by = {r.filename: r for r in res.results}
    assert by[fn].status == "failed" and "index hash" in by[fn].error.lower()
    assert by["beta-0.9-py3-none-any.whl"].status == "failed" and "bytes" in by["beta-0.9-py3-none-any.whl"].error
    assert by["beta-0.9-py3-none-any.whl"].attempts == 2                          # retried once
    assert ctx.repos.list_files(repo.id) == [] and not list((ctx.data_root / "tmp").glob("dl_*"))


def test_unreachable_file_url_and_retry_failed(ctx, repo, index, server):
    fn = "beta-1.2-py3-none-any.whl"
    f = ResolvedFile("beta", "1.2", fn, f"{server}/nope/{fn}")
    plan = DownloadPlan(["beta"], [f])
    res = ctx.downloader.download(plan, repo.id, DownloadOptions(retries=0))
    assert res.failed and "404" in res.failed[0].error
    f.url = f"{server}/{fn}"                                                       # "fix" the problem, then retry
    res2 = ctx.downloader.retry_failed(res, plan, repo.id, DownloadOptions(retries=0))
    assert res2.added and len(ctx.repos.list_files(repo.id)) == 1


def test_cancel_before_and_during_download(ctx, repo, index, server):
    fn = "beta-1.2-py3-none-any.whl"
    f = ResolvedFile("beta", "1.2", fn, f"{server}/{fn}")
    tok = CancelToken(); tok.cancel()
    res = ctx.downloader.download(DownloadPlan(["beta"], [f]), repo.id, DownloadOptions(retries=0), cancel=tok)
    assert [r.status for r in res.results] == ["cancelled"] and ctx.repos.list_files(repo.id) == []
    tok2 = CancelToken()
    res = ctx.downloader.download(DownloadPlan(["beta"], [f]), repo.id, DownloadOptions(retries=0), cancel=tok2,
                                  progress=lambda p: tok2.cancel())              # cancel on first progress event
    assert res.results[0].status in ("cancelled", "added")
    assert not list((ctx.data_root / "tmp").glob("dl_*")), "staging cleaned after cancel"


def test_size_limit_and_validation(ctx, host, repo, index, host_target):
    with pytest.raises(InsufficientDiskSpaceError):
        ctx.downloader.download(DownloadPlan(["x"], [ResolvedFile("x", "1", "x-1-py3-none-any.whl", "http://x/x", None, 50 * 1024 * 1024)]),
                                repo.id, DownloadOptions(max_size_mb=1))
    with pytest.raises(ValidationError):
        ctx.downloader.collect([], repo.id, host, host_target, opts(index))
    with pytest.raises(ValidationError):
        ctx.downloader.collect(["not a requirement!!"], repo.id, host, host_target, opts(index))


def test_works_without_internet(ctx, host, repo, host_target):
    """No index reachable (closed local port): a clear NoInternetError, nothing half-written, app keeps working."""
    ctx.settings.retries = 0
    ctx.settings.timeout = 3
    with pytest.raises(NoInternetError):
        ctx.downloader.collect(["alpha"], repo.id, host, host_target,
                               DownloadOptions(index_url="http://127.0.0.1:9/simple", retries=0))
    assert ctx.repos.list_files(repo.id) == [] and ctx.repos.health_check(repo.id).ok
    assert ctx.store.list_ops(status="failed")                                       # failure was journaled
