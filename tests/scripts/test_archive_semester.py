"""Tests for the archive_semester script."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.archive_semester import (
    archive_vaults,
    mark_semester_archived,
    parse_args,
    run,
)


@pytest.fixture()
def project_dir() -> Path:
    """Create a temporary project directory with config and vaults."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        # Create a minimal config file
        config = {
            "semester": {
                "name": "Spring 2026",
                "start": "2026-01-20",
                "end": "2026-05-15",
                "archived": False,
            },
            "classes": [
                {
                    "id": "test-class",
                    "name": "Test Class",
                    "code": "TEST",
                    "tools": [],
                    "active": True,
                },
            ],
        }
        config_path = root / "config"
        config_path.mkdir()
        with open(config_path / "classes.json", "w") as f:
            json.dump(config, f)

        # Create a vault directory with some content
        vault_dir = root / "vaults" / "test-class"
        vault_dir.mkdir(parents=True)
        (vault_dir / "notes.md").write_text("# Test Notes\nSome content.")
        (vault_dir / "context.md").write_text("# Context\nRecent interactions.")

        yield root


class TestParseArgs:
    """Tests for argument parsing."""

    def test_required_config(self) -> None:
        """--config is required."""
        with pytest.raises(SystemExit):
            parse_args([])

    def test_config_only(self) -> None:
        """Parses with only --config."""
        args = parse_args(["--config", "config/classes.json"])
        assert args.config == "config/classes.json"
        assert args.root == "."
        assert args.output == "archives"
        assert args.force is False

    def test_all_args(self) -> None:
        """Parses all arguments."""
        args = parse_args([
            "--config", "my.json",
            "--root", "/tmp",
            "--output", "out/",
            "--force",
        ])
        assert args.config == "my.json"
        assert args.root == "/tmp"
        assert args.output == "out/"
        assert args.force is True


class TestArchiveVaults:
    """Tests for the archive_vaults function."""

    def test_creates_zip(self, project_dir: Path) -> None:
        """Creates a zip archive of vaults."""
        vaults_root = project_dir / "vaults"
        output_dir = project_dir / "archives"
        result = archive_vaults(vaults_root, output_dir, "Spring 2026")

        assert result is not None
        assert result.exists()
        assert result.suffix == ".zip"
        assert result.stat().st_size > 0

    def test_no_vaults_returns_none(self, project_dir: Path) -> None:
        """Returns None when vaults directory is empty."""
        empty_vaults = project_dir / "empty_vaults"
        empty_vaults.mkdir()
        output_dir = project_dir / "archives"
        result = archive_vaults(empty_vaults, output_dir, "Spring 2026")
        assert result is None

    def test_nonexistent_dir_returns_none(self, project_dir: Path) -> None:
        """Returns None when vaults directory doesn't exist."""
        output_dir = project_dir / "archives"
        result = archive_vaults(
            project_dir / "nonexistent", output_dir, "Spring 2026"
        )
        assert result is None

    def test_archive_filename_contains_semester(
        self, project_dir: Path
    ) -> None:
        """Archive filename includes a sanitized semester name."""
        vaults_root = project_dir / "vaults"
        output_dir = project_dir / "archives"
        result = archive_vaults(vaults_root, output_dir, "Spring 2026")
        assert result is not None
        assert "spring-2026" in result.name.lower()


class TestMarkSemesterArchived:
    """Tests for the mark_semester_archived function."""

    def test_sets_archived_true(self, project_dir: Path) -> None:
        """Sets the archived flag to true in config."""
        config_path = project_dir / "config" / "classes.json"
        mark_semester_archived(config_path)

        with open(config_path) as f:
            data = json.load(f)
        assert data["semester"]["archived"] is True

    def test_preserves_other_fields(self, project_dir: Path) -> None:
        """Other config fields are preserved."""
        config_path = project_dir / "config" / "classes.json"
        mark_semester_archived(config_path)

        with open(config_path) as f:
            data = json.load(f)
        assert data["semester"]["name"] == "Spring 2026"
        assert len(data["classes"]) == 1


class TestRun:
    """Integration tests for the run function."""

    def test_full_archive(self, project_dir: Path) -> None:
        """Full archive creates zip and marks config."""
        config_path = str(project_dir / "config" / "classes.json")
        exit_code = run(
            config_path=config_path,
            root=str(project_dir),
            output="archives",
        )

        assert exit_code == 0
        # Config should be marked archived
        with open(project_dir / "config" / "classes.json") as f:
            data = json.load(f)
        assert data["semester"]["archived"] is True
        # All classes should be deactivated
        for cls in data["classes"]:
            assert cls["active"] is False
        # Archive zip should exist
        archive_dir = project_dir / "archives"
        assert archive_dir.exists()
        zips = list(archive_dir.glob("*.zip"))
        assert len(zips) == 1

    def test_already_archived_skips(self, project_dir: Path) -> None:
        """Skips archival when semester is already archived."""
        config_path = project_dir / "config" / "classes.json"
        # Mark as already archived
        with open(config_path) as f:
            data = json.load(f)
        data["semester"]["archived"] = True
        with open(config_path, "w") as f:
            json.dump(data, f)

        exit_code = run(
            config_path=str(config_path),
            root=str(project_dir),
            output="archives",
        )

        assert exit_code == 0
        # No archive should be created
        archive_dir = project_dir / "archives"
        assert not archive_dir.exists()

    def test_force_re_archives(self, project_dir: Path) -> None:
        """--force re-archives even when already archived."""
        config_path = project_dir / "config" / "classes.json"
        # Mark as already archived
        with open(config_path) as f:
            data = json.load(f)
        data["semester"]["archived"] = True
        with open(config_path, "w") as f:
            json.dump(data, f)

        exit_code = run(
            config_path=str(config_path),
            root=str(project_dir),
            output="archives",
            force=True,
        )

        assert exit_code == 0
        archive_dir = project_dir / "archives"
        assert archive_dir.exists()
        zips = list(archive_dir.glob("*.zip"))
        assert len(zips) == 1
