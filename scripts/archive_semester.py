"""Archive a completed semester by compressing vaults and marking config.

Usage:
    python scripts/archive_semester.py --config config/classes.json [--root .] [--output archives/]

Creates a timestamped zip archive of all class vaults and marks the
semester as archived in the config. Idempotent: won't re-archive if
the semester is already marked as archived.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.loader import load_config
from src.config.schemas import ClassesConfig


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list (defaults to sys.argv).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Archive a completed semester (zip vaults, mark config)"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to classes.json config file",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--output",
        default="archives",
        help="Output directory for archive zip (default: archives/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force archive even if semester is already marked archived",
    )
    return parser.parse_args(argv)


def archive_vaults(
    vaults_root: Path,
    output_dir: Path,
    semester_name: str,
) -> Path | None:
    """Create a zip archive of all vault directories.

    Args:
        vaults_root: Path to the vaults directory.
        output_dir: Directory to write the archive into.
        semester_name: Semester name for the archive filename.

    Returns:
        Path to the created zip file, or None if no vaults exist.
    """
    if not vaults_root.exists() or not any(vaults_root.iterdir()):
        print("  No vaults to archive.")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    # Create a safe filename from semester name
    safe_name = semester_name.lower().replace(" ", "-")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archive_name = f"{safe_name}-{timestamp}"
    archive_path = output_dir / archive_name

    # shutil.make_archive returns the full path with extension
    result = shutil.make_archive(
        str(archive_path),
        "zip",
        root_dir=str(vaults_root.parent),
        base_dir=vaults_root.name,
    )
    return Path(result)


def mark_semester_archived(config_path: Path) -> None:
    """Set the semester's ``archived`` flag to true in the config file.

    Modifies the JSON file in-place.

    Args:
        config_path: Path to the classes.json config file.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["semester"]["archived"] = True

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
        f.write("\n")

    print(f"  Marked semester as archived in {config_path}")


def run(config_path: str, root: str, output: str, force: bool = False) -> int:
    """Execute the semester archive.

    Args:
        config_path: Path to the classes.json config.
        root: Project root directory.
        output: Output directory for the archive.
        force: Force archive even if already archived.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    config_file = Path(config_path)
    root_path = Path(root).resolve()

    config = load_config(config_file, ClassesConfig)

    if config.semester.archived and not force:
        print(
            f"Semester '{config.semester.name}' is already archived. "
            "Use --force to re-archive."
        )
        return 0

    print(f"Archiving semester: {config.semester.name}")
    print(f"  Period: {config.semester.start} to {config.semester.end}")

    active_classes = [c for c in config.classes if c.active]
    print(f"  Classes: {len(active_classes)} active")

    # Archive vaults
    vaults_root = root_path / "vaults"
    output_dir = root_path / output
    archive_path = archive_vaults(vaults_root, output_dir, config.semester.name)

    if archive_path:
        size_mb = archive_path.stat().st_size / (1024 * 1024)
        print(f"  Archive created: {archive_path} ({size_mb:.1f} MB)")
    else:
        print("  No vaults found to archive.")

    # Mark semester as archived in config
    mark_semester_archived(config_file)

    # Deactivate all classes
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    for cls in data.get("classes", []):
        cls["active"] = False
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
        f.write("\n")
    print("  Deactivated all classes.")

    print(f"\nArchive complete. Run init_semester.py with new config to start fresh.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the archive_semester script.

    Args:
        argv: Optional argument list for testing.

    Returns:
        Exit code.
    """
    args = parse_args(argv)
    return run(args.config, args.root, args.output, args.force)


if __name__ == "__main__":
    sys.exit(main())
