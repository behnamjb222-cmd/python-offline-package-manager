"""Builds examples/sample_repository, examples/sample_bundle and example manifests using POPM itself (no network)."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from helpers import build_wheel  # noqa: E402

from app.bootstrap import create_context  # noqa: E402
from app.core.models import TargetSpec  # noqa: E402


def main() -> None:
    out = ROOT / "examples"
    for d in ("sample_repository", "sample_bundle"):
        shutil.rmtree(out / d, ignore_errors=True)
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / "wheels"
        build_wheel(src, "popm_demo_app", "1.0", requires=["popm_demo_lib>=1.0", "popm_demo_colors; sys_platform == 'win32'"])
        build_wheel(src, "popm_demo_lib", "1.0")
        build_wheel(src, "popm_demo_lib", "1.1")
        build_wheel(src, "popm_demo_colors", "0.4")
        ctx = create_context(tmp / "data")
        repo = ctx.repos.create_repository("sample_repository", TargetSpec("3.12", "windows", "x86_64"),
                                           "Tiny demo packages (no real functionality)", base_path=out)
        for w in sorted(src.glob("*.whl")):
            ctx.repos.add_file(repo.id, w, source_url=f"local-demo://{w.name}")
        res = ctx.bundles.create_bundle(repo.id, tmp / "sample_bundle.zip", requirements=["popm_demo_app"])
        ctx.bundles.extract_bundle(res.paths[0], out / "sample_bundle")
        (out / "requirements.txt").write_text("popm_demo_app\n", encoding="utf-8")
        ctx.close()
    print("sample repository and bundle written to", out)


if __name__ == "__main__":
    main()
