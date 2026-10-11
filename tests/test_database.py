import sqlite3

import pytest

from app.database.migrations import current_version, migrate


def test_schema_version_and_idempotent_migrate(ctx):
    assert current_version(ctx.db) == 1
    assert migrate(ctx.db) == 1
    tables = {r[0] for r in ctx.db.query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"repositories", "packages", "package_files", "package_versions", "environments", "environment_packages",
            "bundles", "bundle_packages", "operations", "operation_logs", "settings", "file_checksums"} <= tables


def test_foreign_keys_enforced(ctx):
    with pytest.raises(sqlite3.IntegrityError):
        ctx.db.execute("INSERT INTO package_versions(package_id,version) VALUES(999,'1')")


def test_transaction_rolls_back_on_error(ctx):
    with pytest.raises(RuntimeError):
        with ctx.db.transaction():
            ctx.store.set_setting("k", "v")
            raise RuntimeError("boom")
    assert ctx.store.get_setting("k", "missing") == "missing"
    with ctx.db.transaction():
        with ctx.db.transaction():          # nested joins the outer one
            ctx.store.set_setting("k", "v")
    assert ctx.store.get_setting("k") == "v"


def test_interrupted_operations_are_detected(ctx):
    op = ctx.logs.start("download", "will be 'killed'")
    assert ctx.store.list_ops(status="running")
    recovered = ctx.logs.recover_interrupted()
    assert recovered and recovered[0]["op_uid"] == op.uid
    assert ctx.store.list_ops(status="interrupted")
