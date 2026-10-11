# Architecture

## Layers (dependencies point downwards only)

```
ui/ (PySide6 pages)  ──►  workers/ (QThread + CancelToken)  ──►  services/  ──►  database/ + utils/
```
* `services/` contain **all** logic and import no Qt. Every long method accepts a `CancelToken` and progress/log callbacks.
* `workers/` turn a service call into a `QThread` with signals (`progress`, `message`, `succeeded`, `failed`, `cancelled`).
  `MainWindow.run()` allows one heavy task at a time and drives the shared progress bar / Cancel button.
* `bootstrap.create_context()` builds the service graph (`AppContext`). Tests build one per temp directory.

## Services

| Service | Responsibility |
|---|---|
| `EnvironmentManager` | find/probe interpreters (one inline probe script → JSON incl. wheel tags and marker environment), manual add, validity, venv creation, compare |
| `PackageScanner` | inventory via `importlib.metadata` in the target interpreter, origin classification, outdated, export |
| `PackageDownloader` | **resolve** (pip dry-run report) then **fetch** (own streaming downloader), staging dir, retries, cancel, hash check, gap rounds for foreign targets |
| `RepositoryManager` | repositories, blob store, file registration, removal, health, metadata/manifests, backup/restore, recovery |
| `DependencyManager` | static closure check, pip offline dry-run resolution, trial install in a temp venv |
| `CompatibilityChecker` | wheel-tag matching against probed or generated tags, Requires-Python, marker evaluation, status per file |
| `OfflineInstaller` | plan → confirmation → install → verification → report; environment fingerprint and hash re-check |
| `BundleManager` | create/verify/split/extract/import bundles; template files in `bundle_templates.py` |
| `IntegrityManager` | SHA-256 re-verification, manifest and ZIP validation, provenance |
| `StorageManager` | usage, limits, orphans, temp cleanup, preflight warnings |
| `LoggingManager` | operation journal (SQLite) + rotating file log, secret redaction, TXT/JSON export, interrupted-operation recovery |

## Key design decisions

**No home-made resolver.** What to download/install is decided by pip's resolver (`pip install --dry-run --ignore-installed --report`,
with `--platform/--python-version/--abi/--implementation --target` for a foreign target). POPM only parses the JSON report.
The static `DependencyManager.analyze()` is a planning aid for repositories/bundles and never produces an install set.

**Foreign-target markers.** pip evaluates environment markers for the *machine running pip*. After each download round POPM
reads the downloaded wheels' `Requires-Dist`, evaluates the markers for the *target*, and resolves the missing ones in a follow-up
round (max 3). This fixes cases such as `colorama; sys_platform == "win32"` when collecting on Linux for Windows.

**Storage.** `<data>/blobs/<aa>/<sha256>` stores one physical copy of every unique file. `<repo>/packages/<name>` is a hard link (copy if
linking is impossible), so `pip --find-links <repo>/packages` works directly. File rows reference blobs (`file_checksums`); a blob is
deleted only when its last `package_files` row disappears. Logical removal unlinks the file from `packages/` but keeps the row (reversible).

**Crash safety.** Downloads go to `*.part` in a staging dir and are renamed only when complete and verified; metadata files are written
atomically (temp + `os.replace`); DB writes use `BEGIN IMMEDIATE` transactions with rollback; operations are journaled as `running`
and marked `interrupted` at the next start (the dashboard warns). `rebuild_from_disk` / `discover_repositories` re-register repositories
from `metadata/*.json` and the package files if the database is lost.

**Confirmation by construction.** Destructive or environment-changing service methods take `confirmed: bool` and raise
`ConfirmationRequiredError` otherwise: delete repository, hard-delete file, restore metadata, delete orphans, install, retry install.
The GUI shows the summary (`OfflineInstaller.describe`) *before* calling them.

**Safe subprocesses.** `run_command` takes an argument list, never a shell string (`TypeError` otherwise), merges nothing into a shell,
supports cancel/timeout, and redacts credentials. Every pip call is `<chosen python> -m pip ...` (`pip_cmd`).

**Cancellation.** Cooperative `CancelToken`; child processes are terminated (then killed); partial files are removed; staging dirs are
cleaned in `finally`.

## Database

SQLite, `PRAGMA user_version` migrations (`database/migrations.py`), foreign keys on, WAL, per-thread connections, nested-safe
`transaction()`. Tables: `repositories, packages, package_versions, package_files, file_checksums, environments, environment_packages,
bundles, bundle_packages, operations, operation_logs, settings`. Package bytes are never stored in SQLite.

## Extending to Linux / macOS

Platform differences are isolated in: `utils/paths.data_dir`, `EnvironmentManager.candidate_paths`/`venv_python`,
`compatibility_checker.pip_platforms` (OS/arch → platform tags) and `bundle_templates.INSTALL_SCRIPT`. The code runs on Linux (this is
where it was tested). Adding musllinux or PyPy targets means extending `pip_platforms` / `target_tags`.
