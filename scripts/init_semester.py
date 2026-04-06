"""Scaffold vault and class directories from classes.json config.

Usage:
    python scripts/init_semester.py --config config/classes.json [--root .]

For each active class, creates:
  - vaults/<class-id>/ with subdirs and template files
  - classes/<class-id>/ with standard subdirs

Idempotent: will not overwrite existing files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.defaults import CLASS_SUBDIRS, VAULT_SUBDIRS, VAULT_TEMPLATE_FILES
from src.config.loader import load_config
from src.config.schemas import ClassConfig, ClassesConfig


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument list (defaults to sys.argv).

    Returns:
        Parsed namespace with config and root attributes.
    """
    parser = argparse.ArgumentParser(
        description="Scaffold semester directories from classes.json"
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
    return parser.parse_args(argv)


def scaffold_vault(class_cfg: ClassConfig, vaults_root: Path) -> None:
    """Create vault directory structure for a single class.

    Args:
        class_cfg: The class configuration.
        vaults_root: Root path for all vaults.
    """
    vault_dir = vaults_root / class_cfg.id
    vault_dir.mkdir(parents=True, exist_ok=True)

    for subdir in VAULT_SUBDIRS:
        (vault_dir / subdir).mkdir(exist_ok=True)

    for filename in VAULT_TEMPLATE_FILES:
        filepath = vault_dir / filename
        if not filepath.exists():
            _write_template(filepath, class_cfg, filename)


def scaffold_class(class_cfg: ClassConfig, classes_root: Path) -> None:
    """Create class directory structure for a single class.

    Args:
        class_cfg: The class configuration.
        classes_root: Root path for all class directories.
    """
    class_dir = classes_root / class_cfg.id
    class_dir.mkdir(parents=True, exist_ok=True)

    for subdir in CLASS_SUBDIRS:
        (class_dir / subdir).mkdir(exist_ok=True)


def _write_template(
    filepath: Path, class_cfg: ClassConfig, filename: str
) -> None:
    """Write a blank template file for a vault.

    Args:
        filepath: Absolute path to write.
        class_cfg: Class configuration for template content.
        filename: Template filename for content selection.
    """
    templates: dict[str, str] = {
        "_index.md": f"# {class_cfg.name}\n\nClass code: {class_cfg.code}\n",
        "topics.md": f"# {class_cfg.name} -- Topics\n\n",
        "context.md": f"# {class_cfg.name} -- Context\n\n",
    }
    content = templates.get(filename, f"# {filename}\n")
    filepath.write_text(content, encoding="utf-8")


def run(config_path: str, root: str) -> int:
    """Execute the semester scaffold.

    Args:
        config_path: Path to the classes.json config.
        root: Project root directory.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    root_path = Path(root).resolve()
    config = load_config(config_path, ClassesConfig)

    active = [c for c in config.classes if c.active]
    if not active:
        print("No active classes found in config.")
        return 0

    vaults_root = root_path / "vaults"
    classes_root = root_path / "classes"

    for class_cfg in active:
        scaffold_vault(class_cfg, vaults_root)
        scaffold_class(class_cfg, classes_root)
        print(f"  Scaffolded: {class_cfg.id} ({class_cfg.name})")

    print(f"\nDone. Scaffolded {len(active)} classes.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the init_semester script.

    Args:
        argv: Optional argument list for testing.

    Returns:
        Exit code.
    """
    args = parse_args(argv)
    return run(args.config, args.root)


if __name__ == "__main__":
    sys.exit(main())
