# Test report

Generated from the real pytest run (junit XML) on 2026-10-11.
Environment: Linux x86_64, Python 3.12.3, PySide6 6.12, pytest 9.1 (headless Qt: `QT_QPA_PLATFORM=offscreen`).
Command: `POPM_NETWORK_TESTS=1 python -m pytest -q`

**Result: 106 tests, 106 passed, 0 failed, 0 skipped.**  (The two tests in `test_network_optional.py` use the real PyPI.)

| Test file | Tests | Failed | Seconds |
|---|---:|---:|---:|
| `test_bundles.py` | 9 | 0 | 6.5 |
| `test_compatibility.py` | 15 | 0 | 0.0 |
| `test_database.py` | 4 | 0 | 0.0 |
| `test_dependencies.py` | 4 | 0 | 6.5 |
| `test_downloader.py` | 10 | 0 | 9.8 |
| `test_environments.py` | 7 | 0 | 5.1 |
| `test_installer.py` | 9 | 0 | 24.7 |
| `test_integrity.py` | 15 | 0 | 1.0 |
| `test_network_optional.py` | 2 | 0 | 12.7 |
| `test_repository.py` | 15 | 0 | 3.2 |
| `test_scanner.py` | 3 | 0 | 0.5 |
| `test_ui.py` | 13 | 0 | 50.4 |

## Coverage of the required test list
| # | Required test | Where (actually executed) |
|---|---|---|
| 1 | Python detection | `test_environments` (probe, discover, manual add, invalid/vanished interpreter, arch normalisation) |
| 2 | Package scan | `test_scanner`, `test_ui::test_environments_and_scanner_pages` |
| 3 | Repository creation | `test_repository::test_create_repository_layout_and_metadata` |
| 4 | File registration | `test_repository::test_add_file_registers_hash_and_metadata`, corrupt/unsupported rejection |
| 5 | SHA-256 | `test_repository::test_sha256_helper_and_expected_hash_mismatch`, `test_integrity` |
| 6 | Duplicate detection | `test_repository::test_duplicate_content_detected_and_cross_repo_dedup`, hard-delete reference counting |
| 7 | Manifest creation | `test_bundles::test_bundle_structure_manifest_and_checksums` |
| 8 | Manifest validation | `test_bundles::test_extract_validates_and_detects_tampering` |
| 9 | Wheel compatibility | `test_compatibility` (parametrised tag matrix incl. abi3, manylinux, macOS, Requires-Python) |
| 10 | Missing dependency detection | `test_compatibility::test_missing_dependency_status_and_markers`, `test_dependencies`, `test_installer` |
| 11 | ZIP creation | `test_bundles` (all-files, selected, split) |
| 12 | Zip Slip | `test_integrity::test_zip_slip_names_rejected`, `test_safe_extract_blocks_zip_slip_and_overwrite`, symlink entries |
| 13 | Offline install in a test environment | `test_installer::test_real_offline_install_into_new_venv_with_spaces`, `test_bundles::test_standalone_install_script_in_a_clean_venv`, `test_ui::test_installer_page_*`, `test_network_optional` |
| 14 | Cancellation | `test_integrity::test_run_command_...cancelled`, `test_downloader::test_cancel_before_and_during_download`, `test_ui::test_cancel_button_stops_a_running_task` |
| 15 | Download error handling | `test_downloader` (checksum mismatch, incomplete body, HTTP 404 + retry, size limit, invalid input) |
| 16 | Database | `test_database` (schema, migrations, foreign keys, rollback, interrupted operations) |
| 17 | Repository recovery | `test_repository::test_recovery_after_database_loss`, `test_backup_and_restore_metadata` |
| 18 | Running without internet | `test_downloader::test_works_without_internet`; the whole offline suite uses `--no-index` / local wheels |
| 19 | Paths with spaces | venv paths (`test_environments`, `test_installer`), bundle directories (`test_bundles`) |
| 20 | Unicode file names | `test_repository::test_unicode_repo_name_and_unicode_source_dir`, `test_bundles::test_unicode_paths_in_bundle_output_and_extraction` |

Extra: settings/secret redaction (`test_integrity`), 13 headless GUI tests (all pages in EN/FA × light/dark, Persian coverage, downloader/installer through the real pages,
declined confirmations install nothing, destructive-action confirmation, single task at a time, settings validation).

## Not covered by tests
* Windows and macOS execution (see `KNOWN_LIMITATIONS.md`); `build_windows.ps1`; unsigned-EXE behaviour.
* Real power-loss during writes (only the interrupted-operation bookkeeping and atomic-write design are tested).
* Packages that need compilation, private indexes, authenticated proxies, very large (GB) downloads, musllinux/PyPy targets.
* Visual quality of the GUI beyond manual screenshot inspection.

Manual checks performed once (not automated): PyInstaller one-folder build of `scripts/popm.spec` on Linux (155 MB) and `POPM --selftest` of that build → OK.
