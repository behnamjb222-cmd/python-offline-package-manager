# Examples

* `sample_repository/` – a repository created by POPM (4 tiny demo wheels, target Python 3.12 / windows / x86_64). In POPM: *Offline repositories → Import folder…*
* `sample_bundle/` – the extracted transfer bundle of `popm_demo_app` (note the windows-only `popm_demo_colors`, which is only needed because the target is Windows).
  Try it (Python 3.12 on the offline machine): `python sample_bundle/install_offline.py --venv demo_venv` (add `--dry-run` to only look). On other Python versions/OSes the script warns that the bundle target differs.
* `requirements.txt` – sample requirements file.
* `sample_bundle/metadata/bundle.json` – sample manifest; `sample_bundle/metadata/checksums.json` – sample checksum list.

Regenerate everything with `python scripts/make_sample_repo.py`.
