"""Build tiny but valid wheels / sdists for tests and for the sample repository (no network needed)."""
from __future__ import annotations

import base64
import hashlib
import io
import tarfile
import zipfile
from pathlib import Path


def _record_line(path: str, data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"{path},sha256={digest},{len(data)}"


def build_wheel(dest: Path, name: str, version: str = "1.0", requires: list[str] | None = None,
                requires_python: str | None = None, tag: str = "py3-none-any", extra_files: dict[str, str] | None = None) -> Path:
    """Create ``<name>-<version>-<tag>.whl`` containing a trivial importable module."""
    dest.mkdir(parents=True, exist_ok=True)
    mod = name.replace("-", "_").lower()
    dist = f"{mod}-{version}.dist-info"
    meta = ["Metadata-Version: 2.1", f"Name: {name}", f"Version: {version}"]
    if requires_python:
        meta.append(f"Requires-Python: {requires_python}")
    meta += [f"Requires-Dist: {r}" for r in (requires or [])]
    pure = tag.endswith("none-any")
    files = {f"{mod}/__init__.py": f"VERSION = {version!r}\n".encode(),
             f"{dist}/METADATA": ("\n".join(meta) + "\n").encode(),
             f"{dist}/WHEEL": (f"Wheel-Version: 1.0\nGenerator: popm-test\nRoot-Is-Purelib: {'true' if pure else 'false'}\n"
                               f"Tag: {tag}\n").encode()}
    for k, v in (extra_files or {}).items():
        files[k] = v.encode()
    record = [_record_line(k, v) for k, v in files.items()] + [f"{dist}/RECORD,,"]
    files[f"{dist}/RECORD"] = ("\n".join(record) + "\n").encode()
    out = dest / f"{mod}-{version}-{tag}.whl"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for k, v in files.items():
            zf.writestr(k, v)
    return out


def build_sdist(dest: Path, name: str, version: str = "1.0", requires: list[str] | None = None) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    base = f"{name}-{version}"
    meta = ["Metadata-Version: 2.1", f"Name: {name}", f"Version: {version}"] + [f"Requires-Dist: {r}" for r in (requires or [])]
    out = dest / f"{base}.tar.gz"
    with tarfile.open(out, "w:gz") as tf:
        data = ("\n".join(meta) + "\n").encode()
        ti = tarfile.TarInfo(f"{base}/PKG-INFO")
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))
    return out
