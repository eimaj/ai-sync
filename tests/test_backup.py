"""Tests for the non-destructive backup system."""

import json
import sys

from tests.conftest import make_args, seed_manifest

mod = sys.modules["sync_agent_rules"]


class TestInitBackup:
    def test_creates_timestamped_dir(self, fake_home):
        backup_dir = mod.init_backup("test-cmd")
        assert backup_dir.exists()
        assert backup_dir.parent == mod.BACKUPS_DIR

        meta = json.loads((backup_dir / "meta.json").read_text())
        assert meta["command"] == "test-cmd"
        assert "created" in meta


class TestBackupFile:
    def test_copies_file(self, fake_home):
        mod.init_backup("test")
        target = fake_home / "somefile.txt"
        target.write_text("original")

        mod.backup_file(target, make_args())

        backed_up = mod._backup_dest(target)
        assert backed_up.exists()
        assert backed_up.read_text() == "original"

    def test_dry_run_skips(self, fake_home):
        mod.init_backup("test")
        target = fake_home / "somefile.txt"
        target.write_text("original")

        mod.backup_file(target, make_args(dry_run=True))

        backed_up = mod._backup_dest(target)
        assert not backed_up.exists()

    def test_skips_symlinks(self, fake_home):
        mod.init_backup("test")
        real = fake_home / "real.txt"
        real.write_text("data")
        link = fake_home / "link.txt"
        link.symlink_to(real)

        mod.backup_file(link, make_args())

        backed_up = mod._backup_dest(link)
        assert backed_up is not None
        assert not backed_up.exists()

    def test_skips_nonexistent(self, fake_home):
        mod.init_backup("test")
        mod.backup_file(fake_home / "nope.txt", make_args())


class TestLatestBackup:
    def test_returns_most_recent(self, fake_home):
        mod.init_backup("first")
        first = mod._current_backup

        import time
        time.sleep(1.1)

        mod.init_backup("second")
        second = mod._current_backup

        result = mod.latest_backup()
        assert result == second
        assert result != first

    def test_returns_none_when_empty(self, fake_home):
        assert mod.latest_backup() is None


class TestRestoreFromBackup:
    def test_restores_targeted_files(self, fake_home):
        target = fake_home / "restore-me.txt"
        target.write_text("original content")

        mod.init_backup("test")
        mod.backup_file(target, make_args())

        target.write_text("overwritten")

        restored = mod.restore_from_backup(
            mod._current_backup, [target], make_args()
        )
        assert restored == 1
        assert target.read_text() == "original content"

    def test_dry_run_skips_restore(self, fake_home):
        target = fake_home / "file.txt"
        target.write_text("original")

        mod.init_backup("test")
        mod.backup_file(target, make_args())
        target.write_text("changed")

        restored = mod.restore_from_backup(
            mod._current_backup, [target], make_args(dry_run=True, verbose=True)
        )
        assert restored == 1
        assert target.read_text() == "changed"


class TestWriteFileBackup:
    def test_backs_up_before_overwrite(self, fake_home):
        mod.init_backup("test")
        target = fake_home / "file.txt"
        target.write_text("original")

        mod.write_file(target, "new content", make_args())

        assert target.read_text() == "new content"
        backed_up = mod._backup_dest(target)
        assert backed_up.exists()
        assert backed_up.read_text() == "original"


class TestRemoveFileBackup:
    def test_backs_up_before_unlink(self, fake_home):
        mod.init_backup("test")
        target = fake_home / "file.txt"
        target.write_text("preserve me")

        mod.remove_file(target, make_args())

        assert not target.exists()
        backed_up = mod._backup_dest(target)
        assert backed_up.exists()
        assert backed_up.read_text() == "preserve me"
