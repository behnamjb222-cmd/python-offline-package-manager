from app.core.models import InstallOptions


def test_analyze_complete_set(ctx, filled_repo, host_target):
    files = ctx.repos.list_files(filled_repo.id)
    rep = ctx.deps.analyze(files, ["alpha"], host_target)
    assert rep.ok and set(rep.selected) == {"alpha", "beta"}
    assert rep.selected["beta"].version == "1.2"                       # highest satisfying
    assert rep.direct == ["alpha"] and any("beta" in r for r in rep.indirect)


def test_analyze_reports_missing_unsatisfied_conflict_and_incompatible(ctx, index, repo, host_target, win_target):
    for f in ("alpha-1.0-py3-none-any.whl", "winonly-1.0-cp312-cp312-win_amd64.whl", "beta-0.9-py3-none-any.whl"):
        ctx.repos.add_file(repo.id, index / f)
    files = ctx.repos.list_files(repo.id)
    rep = ctx.deps.analyze(files, ["alpha"], host_target)
    assert not rep.ok and rep.unsatisfied and "beta" in rep.unsatisfied[0]       # alpha needs beta>=1, only 0.9 present
    assert ctx.deps.analyze(files, ["ghost"], host_target).missing == ["ghost"]
    rep3 = ctx.deps.analyze(files, ["winonly"], host_target)
    assert rep3.no_compatible_file and "winonly" in rep3.no_compatible_file[0]
    assert ctx.deps.analyze(files, ["winonly"], win_target).ok
    conflict = ctx.deps.analyze(ctx.repos.list_files(repo.id), ["beta<1", "beta>=1"], host_target)
    assert conflict.conflicts or conflict.unsatisfied


def test_pip_resolve_offline_matches_pip(ctx, filled_repo, host):
    res = ctx.deps.pip_resolve_offline(host, __import__("pathlib").Path(filled_repo.path) / "packages", ["alpha"],
                                       ignore_installed=True)
    assert res.ok and {n for n, _v, _f in res.packages} == {"alpha", "beta"}
    bad = ctx.deps.pip_resolve_offline(host, __import__("pathlib").Path(filled_repo.path) / "packages", ["alpha>=5"])
    assert not bad.ok and bad.missing


def test_trial_install_does_not_touch_main_environment(ctx, filled_repo, host):
    from pathlib import Path
    before = {p.name for p in ctx.scanner.scan(host)}
    t = ctx.deps.trial_install(host, Path(filled_repo.path) / "packages", ["alpha"])
    assert t.ok and {"alpha", "beta"} <= set(t.installed)
    after = {p.name for p in ctx.scanner.scan(host)}
    assert before == after and "alpha" not in {n.lower() for n in after}
    assert not list((ctx.data_root / "tmp").glob("trial_*")), "temporary venv must be cleaned up"
