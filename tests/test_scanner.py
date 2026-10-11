import csv
import json

from app.core.models import InstalledPackage


def test_scan_returns_structured_packages(ctx, host):
    pkgs = ctx.scanner.scan(host)
    names = {p.name.lower() for p in pkgs}
    assert {"pip", "packaging", "pytest"} <= names
    assert all(p.version for p in pkgs)
    assert ctx.store.get_env(host.id).package_count == len(pkgs)
    assert [p.name for p in ctx.store.get_env_packages(host.id)]


def test_filter_sort_and_origin_report(ctx):
    pk = [InstalledPackage("Zed", "1.10", "PYPI_LIKELY"), InstalledPackage("apple", "1.2", "PYPI_LIKELY"),
          InstalledPackage("loc", "0.1", origin="LOCAL"), InstalledPackage("conda-pkg", "2", origin="UNKNOWN")]
    s = ctx.scanner
    assert [p.name for p in s.filter_sort(pk, "a")] == ["apple", "conda-pkg"]
    assert [p.name for p in s.filter_sort(pk, key="version")][:2] == ["loc", "apple"]
    assert [p.name for p in s.unknown_origin(pk)] == ["loc", "conda-pkg"]


def test_exports(ctx, host, tmp_path):
    pk = [InstalledPackage("alpha", "1.0", "PYPI_LIKELY"), InstalledPackage("mine", "0.1", "EDITABLE")]
    r = ctx.scanner.export(host, pk, tmp_path / "r.txt", "requirements").read_text()
    assert "alpha==1.0" in r and "# skipped mine==0.1" in r
    j = json.loads(ctx.scanner.export(host, pk, tmp_path / "r.json", "json").read_text())
    assert j["environment"]["python"] == host.version and len(j["packages"]) == 2
    rows = list(csv.reader(ctx.scanner.export(host, pk, tmp_path / "r.csv", "csv").open(encoding="utf-8")))
    assert rows[0][:3] == ["name", "version", "origin"] and len(rows) == 3
