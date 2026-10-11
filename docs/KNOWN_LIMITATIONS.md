# Known limitations (honest list)

**Testing scope**
1. All automated tests were run on **Linux** (Python 3.12). The Windows-specific code (`py -0p`, registry discovery, `Scripts\python.exe`
   paths, NTFS hard links, `CREATE_NO_WINDOW`) is written but **not exercised on Windows**; `scripts/build_windows.ps1` was **not run on Windows**.
   The PyInstaller spec was built and its output passed `--selftest` on Linux only. macOS: not tested.
2. GUI tests run headless (`offscreen`); layouts/RTL were inspected via screenshots only. No Persian font is bundled (system fonts are used).

**Scope not implemented**
3. A **standalone bundle containing a Python interpreter** is *not* implemented (the specification asked for it as a separate, designed
   feature). Constraints to respect if added: Python's licence terms, the interpreter must match target OS + architecture + minor version,
   installers/embeddable zips differ per OS, and security updates become your responsibility.
4. Resuming partial downloads is not supported (a cancelled/failed download restarts that file).
5. No dedicated "Storage" page (the Storage actions live on *File validation*); no scheduled cleanup.

**Dependency / compatibility semantics**
6. For a *foreign* target pip evaluates environment markers for the host. POPM compensates with follow-up rounds based on the downloaded
   wheels' `Requires-Dist`, but only for dependencies of files it actually downloaded (`extra` requirements are never requested).
   Always run **Compatibility check** and, if possible, a **Trial install** on the target before relying on a bundle.
7. Foreign targets assume **CPython** and, for Linux, glibc (`manylinux`) tags; **musllinux (Alpine) and PyPy targets are not generated**
   (they work only when the target interpreter was probed directly, which provides its real tags).
8. Source distributions cannot be cross-built. With `allow_sdist` they are downloaded only for the *host-equivalent* target and must be built
   on the target; their build dependencies (setuptools, wheel, ...) are **not** collected, so offline builds frequently fail.
   Prefer wheels (`--only-binary`).
9. `DependencyManager.analyze` is a static check, not a resolver; pip has the last word. `Requires-Python` is compared with `major.minor`.
10. Compatibility judges tags and metadata only. It cannot know about system libraries, CPU features or GPU drivers; a successful install
    does not guarantee correct behaviour at run time.

**Network**
11. The fetch phase uses Python's `urllib` (not pip's networking): it honours POPM's proxy/SSL/CA settings but **not** `pip.conf`
    credentials or private-index authentication. Use a local folder (`--find-links`) for private indexes. Only HTTP(S) proxies are supported
    (SOCKS is rejected). Resolution still goes through pip and therefore honours `pip.conf`/environment.
12. Download size limits use `Content-Length` from HEAD requests; servers that do not answer give an unknown size (the limit cannot apply).

**Security notes**
13. SHA-256 proves integrity since the hash was recorded (and, when `hash_origin = index`, equality with what the index published);
    it does **not** authenticate the publisher. POPM does not verify PyPI attestations/signatures.
14. Installing a package means trusting it; sdists run build code, and even wheels can run code when imported. POPM never executes
    package code itself, but `pip install` does what pip does.
15. SSL verification can be disabled in Settings (off by default → on); doing so makes downloads interceptable.

**Other**
16. *Rename repository* changes the display name only (the folder keeps its name).
17. Two POPM instances can share a database (SQLite locking, `DatabaseLockedError` on contention) but concurrent edits of the same repository
    are not coordinated beyond that.
18. Hard-linked storage assumes `<data>/blobs` and the repository folder are on one volume; otherwise files are copied (more disk use, still correct).
