# Offline package bundle (POPM)

Created: 2026-10-11T13:12:47+00:00
Repository: sample_repository
Target: Python 3.12 / windows / x86_64
Package files: 3

**This bundle contains Python package files only. It does NOT contain a Python interpreter.**
Python 3.12 (matching OS/architecture) must already be installed on the offline machine.

## Install (no internet needed)
1. Copy this folder (or extract the ZIP) to the offline machine.
2. Open a terminal in this folder and run (recommended, creates a new virtual environment):

       python install_offline.py --venv C:\envs\myproject

   Use `--dry-run` first to see what would be installed. Add `--yes` to skip the confirmation question.
3. The script verifies SHA-256 checksums (metadata/checksums.json), installs with
   `pip install --no-index --find-links packages -r manifests/requirements.txt`, then runs `pip check`.

You can also import the bundle into POPM (Transfer page) and install from the graphical interface.

Note: a checksum proves the files were not changed after the bundle was made; it does not prove who published them.
