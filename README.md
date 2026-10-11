# Python Offline Package Manager (POPM)

A desktop application (PySide6) that collects Python packages on an internet-connected machine, stores them in verified,
de-duplicated **offline repositories**, builds a **portable bundle** you can carry on a USB stick, and installs from it on a
machine **without internet** — through a graphical interface or a standalone `install_offline.py` script.

> Persian documentation: [README_FA.md](README_FA.md) · [docs/USER_GUIDE_FA.md](docs/USER_GUIDE_FA.md)

## What it does

| Area | Implemented |
|---|---|
| Environments | Detect Pythons (PATH, standard install dirs, `py -0p`, registry, pyenv/conda, known venv folders), add manually, probe version/pip/OS/arch/wheel tags, compare two environments, mark vanished ones invalid |
| Scan | Structured inventory via `importlib.metadata` *inside* the chosen interpreter (no text parsing), origin classification (PyPI-likely / local / VCS / URL / editable / unknown), outdated check, filter/sort, export `requirements.txt` / JSON / CSV |
| Download | pip's own resolver (`install --dry-run --report`) decides the file set for the *target* machine; POPM downloads with progress, speed, retries, cancel, index-hash verification, multi-version support, size limits |
| Repositories | Several independent repos, SQLite index, SHA-256 de-duplication across repos (hard-linked blob store), logical/hard delete, health check, duplicates, metadata backup/restore, rebuild from disk |
| Dependencies | Static completeness check (missing / conflict / no compatible file), pip dry-run resolution, trial install in a throw-away venv |
| Install | Plan → explicit confirmation → `pip install --no-index --find-links` into a **new venv** (default) or an existing environment, per-package result, `pip check`, retry, report file |
| Bundles | ZIP with packages, manifests, checksums, compatibility report, `install_offline.py`, FA/EN READMEs; optional split into parts; archive verified after creation; safe extraction (Zip Slip) and import into a repository |
| Safety | No `shell=True`; confirmation for destructive actions; SSL verification on by default; secrets redacted from logs; proxy password never stored |
| UI | 12 pages, light/dark theme, Persian (RTL) and English, background workers, progress, cancel |

A bundle contains **package files only — not a Python interpreter.** See [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).

## Requirements

* Python **3.11+** to run from source (the *target* environments can be Python 3.8+)
* `PySide6-Essentials`, `packaging` (see `requirements-dev.txt`)
* pip **22.2+** inside every environment you scan/download with/install into (needs `--dry-run --report`)

## Run

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
python main.py                    # GUI
python main.py --selftest         # headless smoke test
```

Data (database, settings, logs, repositories) lives in `%APPDATA%\POPM` (Windows), `~/.local/share/popm` (Linux),
`~/Library/Application Support/POPM` (macOS); set `POPM_HOME` to override. Repositories can be placed anywhere.

## Typical workflow

1. **Online machine** – *Python environments* → *Discover*; *Scan packages* → tick packages → *Send to Downloader*;
   choose the **target** (version / OS / architecture of the offline machine) and a repository → *Start download*.
2. *Transfer & export* → *Create bundle* → copy the ZIP to the offline machine.
3. **Offline machine** – either run `python install_offline.py --venv C:\envs\proj` from the extracted bundle, or open POPM →
   *Transfer & export → Import bundle* → *Offline install* → review the summary → confirm.

Details: [docs/USER_GUIDE_EN.md](docs/USER_GUIDE_EN.md).

## Tests

```bash
python -m pytest -q                         # offline suite (uses local wheels, temporary venvs)
POPM_NETWORK_TESTS=1 python -m pytest -q    # + two real-PyPI tests
```
Results of the last run: [docs/TEST_REPORT.md](docs/TEST_REPORT.md).

## Build a Windows EXE

```powershell
.\scripts\build_windows.ps1        # runs tests, builds dist\POPM\POPM.exe, runs POPM.exe --selftest
```
The EXE contains POPM + its Python/Qt runtime only. It does **not** contain your package repositories and does **not** install
Python on other machines. The script has been exercised only partly (see limitations).

## Project layout

```
main.py                 entry point (GUI, --selftest)
app/core                models, exceptions (bilingual messages), validators, constants
app/services            the 11 domain services (no Qt imports)
app/database            SQLite connection, migrations, data-access layer
app/workers             QThread task runner + one factory module per task family
app/ui                  PySide6 pages, dialogs, theme
app/utils               paths, hashing, safe subprocess, archive, pip helpers
tests/                  pytest suite     scripts/  build scripts     docs/  documentation     examples/  sample repo & bundle
```
Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). License: MIT.
