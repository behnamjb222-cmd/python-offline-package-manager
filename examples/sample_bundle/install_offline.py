#!/usr/bin/env python3
"""Offline installer for a POPM bundle. Standard library only; never touches the network.

Examples:
    python install_offline.py --venv C:\envs\myproject          (recommended: new virtual environment)
    python install_offline.py --python C:\Python312\python.exe --venv .\venv
    python install_offline.py --dry-run                         (show what pip would do, change nothing)
Exit codes: 0 ok, 1 install failed, 2 integrity problem, 3 cancelled / not confirmed.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(python):
    code = "import platform,sys;print(platform.python_version()+'|'+platform.system()+'|'+platform.machine()+'|'+str(sys.prefix!=getattr(sys,'base_prefix',sys.prefix)))"
    r = subprocess.run([python, "-c", code], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("Cannot run Python: " + python)
    ver, system, machine, is_venv = r.stdout.strip().split("|")
    return ver, system, machine, is_venv == "True"


def main():
    ap = argparse.ArgumentParser(description="Install a POPM offline bundle (no internet needed).")
    ap.add_argument("--python", default=sys.executable, help="Python interpreter to use (default: the one running this script)")
    ap.add_argument("--venv", help="create this virtual environment and install into it (recommended)")
    ap.add_argument("--requirements", default=str(HERE / "manifests" / "requirements.txt"))
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    ap.add_argument("--dry-run", action="store_true", help="only show what pip would install")
    ap.add_argument("--skip-verify", action="store_true", help="skip SHA-256 verification (not recommended)")
    ap.add_argument("--only-binary", action="store_true", help="refuse source distributions (no compiling)")
    a = ap.parse_args()

    bundle = json.loads((HERE / "metadata" / "bundle.json").read_text(encoding="utf-8"))
    if not a.skip_verify:
        sums = json.loads((HERE / "metadata" / "checksums.json").read_text(encoding="utf-8"))
        bad = [rel for rel, s in sums.items() if not (HERE / rel).is_file() or sha256(HERE / rel) != s]
        if bad:
            print("INTEGRITY PROBLEM - these files are missing or changed:")
            for b in bad:
                print("  -", b)
            return 2
        print("Integrity OK (%d files verified)." % len(sums))

    ver, system, machine, is_venv = probe(a.python)
    t = bundle.get("target", {})
    print("Bundle target : Python %s / %s / %s" % (t.get("python") or "?", t.get("os") or "?", t.get("arch") or "?"))
    print("This machine  : Python %s / %s / %s" % (ver, system, machine))
    if t.get("python") and ".".join(ver.split(".")[:2]) != t["python"]:
        print("WARNING: Python version differs from the bundle target; compiled packages may not install.")
    print("Note: this bundle contains package files only, NOT a Python interpreter.")
    reqs = [ln.strip() for ln in Path(a.requirements).read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    print("Packages requested: %d  | files in bundle: %d" % (len(reqs), len(bundle.get("files", []))))
    where = ("NEW virtual environment: " + a.venv) if a.venv else (("existing virtual environment" if is_venv else "GLOBAL Python (system-wide!)") + ": " + a.python)
    print("Install target: " + where)
    if not a.yes and not a.dry_run:
        warn = "" if (a.venv or is_venv) else "This changes the global Python environment. "
        if input(warn + "Proceed? type 'yes': ").strip().lower() != "yes":
            print("Cancelled.")
            return 3
    py = a.python
    if a.venv and not a.dry_run:
        r = subprocess.run([a.python, "-m", "venv", a.venv])
        if r.returncode != 0:
            print("Could not create the virtual environment.")
            return 1
        py = str(Path(a.venv) / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
    cmd = [py, "-m", "pip", "--disable-pip-version-check", "--no-input", "install", "--no-index",
           "--find-links", str(HERE / "packages"), "-r", a.requirements]
    if a.only_binary:
        cmd.append("--only-binary=:all:")
    if a.dry_run:
        cmd.append("--dry-run")
    print("Running:", " ".join(cmd))
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        print("pip failed (exit %d)." % rc)
        return 1
    if not a.dry_run:
        subprocess.run([py, "-m", "pip", "--disable-pip-version-check", "check"])
        print("Done. Interpreter: " + py)
    return 0


if __name__ == "__main__":
    sys.exit(main())
