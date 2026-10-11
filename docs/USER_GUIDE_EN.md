# User guide (English)

## 1. Install and start
See [INSTALL.md](INSTALL.md). Start with `python main.py` (or `POPM.exe`). Switch language/theme in **Settings**.
The status bar shows: internet state, active Python + pip, repositories folder, repository size / free disk, running task (with **Cancel**).

## 2. Build an offline repository (online machine)
1. **Python environments → Discover environments.** If your Python is not listed, *Add Python manually…*. Select one and *Use as active*.
   POPM runs every pip command as `<that python> -m pip`, never a global `pip`.
2. **Scan packages → Scan active environment.** Tick what you want (or *Select all*). Packages that were installed from a local
   folder / VCS / editable cannot be downloaded from an index; they are listed under *Unknown-origin report* and skipped.
3. **Send selected to Downloader** (or type/load requirements yourself, e.g. `requests==2.32.3`; two lines of the same package with
   different versions collect both versions).
4. **Download & collect**
   * **Target machine** — *Same as selected environment*, *Repository target*, or *Custom* (Python version, OS, architecture of the
     **offline** machine). Wheels depend on these; choose them correctly.
   * **Destination repository** — pick one or *New…* (name, folder, target).
   * Options: include dependencies, allow sdist (source packages that must be built on the target — off by default),
     retries, parallel downloads, max size, optional local index folder (`--find-links`) instead of the internet.
   * *Preview (resolve)* shows the exact file list, sizes and warnings; *Start download* runs it. Failed files can be retried.
   * If no compatible wheel exists for the target you get a clear message instead of a silent source build.
5. **File validation → Verify all files** re-hashes everything. **Compatibility check** judges every file against the target.
6. **Transfer & export → Create bundle**: choose the repository, optionally list packages (dependencies are added automatically),
   target, split size, output. The ZIP is verified after creation. Copy it to a USB drive.

## 3. Install on the offline machine
**Option A — standalone script (no POPM needed, Python must exist):**
```
unzip bundle.zip -d bundle        (or any extractor)
cd bundle
python install_offline.py --dry-run                      # see what would happen
python install_offline.py --venv C:\envs\myproject        # recommended: new virtual environment
```
It verifies checksums, warns when the Python version differs from the bundle target, asks for confirmation (`--yes` to skip),
runs `pip install --no-index --find-links packages -r manifests/requirements.txt` and then `pip check`.

**Option B — POPM GUI:**
1. *Transfer & export → Import bundle* (select the `.zip`, or the first `.zip.001` part) into a repository.
2. *Offline install*: select the repository, tick packages (or paste requirements), choose **New virtual environment** (path + base
   Python) or an existing environment, set options, press **Check & show summary**.
3. Read the summary (packages, versions, compatibility, options, warnings). Nothing has changed yet. Press **Install now** to confirm.
4. Results are listed per package; the report file path is shown; *Retry failed* and *Verify installation* are available.
   *Trial install* tests the whole set in a temporary venv that is deleted afterwards.

Option explanations: `--only-binary` refuses source builds (no compiling on the target); `--no-deps` skips dependencies (not recommended;
POPM warns); `--upgrade`/`--force-reinstall` as in pip. Installing into a system-wide Python can need administrator rights — prefer a new venv.

## 4. Other pages
* **Offline repositories** – list/search/filter files, add files manually, hide/restore/delete (permanent delete asks for confirmation),
  health check, duplicates, metadata backup/restore, import an existing repository folder, report, open folder.
* **File validation** – SHA-256 verification, provenance (source URL, hash origin), storage report, clean temp files, delete unreferenced files.
* **Reports** – every operation (type, status, summary) with its log; export TXT/JSON; delete old reports.
* **Settings** – folders, retries, parallelism, limits, language, theme, log level, retention, proxy (password is session-only), timeout,
  SSL verification (keep on), CA bundle, default Python, sdist policy.

## 5. Good to know
* A checksum shows a file was not changed after it was added; it does not prove who published it. The provenance list marks hashes that
  came from the package index (`index`).
* Successful installation does not guarantee a package works at run time (system libraries, GPU drivers, ...).
* A bundle does **not** contain Python. The same Python minor version, OS and architecture as the target must exist on the offline machine.
