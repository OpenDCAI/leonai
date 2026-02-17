"""CLI command for configuration migration.

Usage:
    leonai migrate-config [--dry-run] [--config-dir PATH]
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from config.migrate import ConfigMigrationError, ConfigMigrator


@click.command("migrate-config")
@click.option("--dry-run", is_flag=True, help="Validate migration without writing files")
@click.option(
    "--config-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Configuration directory (default: ~/.leon)",
)
@click.option("--rollback", is_flag=True, help="Rollback migration by restoring backup files")
def migrate_config_command(dry_run: bool, config_dir: Path | None, rollback: bool) -> None:
    """Migrate old configuration to new models.json + runtime.json format.

    Migrates from old formats:
    - profile.yaml, config.json, settings.json, providers.json

    To new format:
    - models.json (model identity, providers, mapping, pool)
    - runtime.json (memory, tools, mcp, skills, behavior params)

    Old files are backed up with .bak suffix before migration.
    """
    if config_dir is None:
        config_dir = Path.home() / ".leon"

    migrator = ConfigMigrator(config_dir)

    if rollback:
        try:
            click.echo(f"Rolling back migration in {config_dir}...")
            migrator.rollback()
            click.secho("✓ Migration rolled back successfully", fg="green")
            return
        except ConfigMigrationError as e:
            click.secho(f"✗ Rollback failed: {e}", fg="red", err=True)
            sys.exit(1)

    try:
        old_files = migrator.detect_old_config()
    except Exception as e:
        click.secho(f"✗ Error detecting old configuration: {e}", fg="red", err=True)
        sys.exit(1)

    if not old_files:
        click.secho("No old configuration files found. Nothing to migrate.", fg="yellow")
        sys.exit(0)

    click.echo("Detected old configuration files:")
    for file_type, path in old_files.items():
        click.echo(f"  • {file_type}: {path}")
    click.echo()

    if not dry_run:
        if not click.confirm("Proceed with migration?"):
            click.echo("Migration cancelled.")
            sys.exit(0)

    try:
        report = migrator.migrate(dry_run=dry_run)
    except ConfigMigrationError as e:
        click.secho(f"✗ Migration failed: {e}", fg="red", err=True)
        sys.exit(1)

    if dry_run:
        click.secho("✓ Dry run completed successfully", fg="green")
    else:
        click.secho("✓ Migration completed successfully", fg="green")

    if report.get("changes"):
        click.echo("\nChanges:")
        for change in report["changes"]:
            click.echo(f"  • {change}")

    if not dry_run and report.get("new_files"):
        click.echo("\nNew files created:")
        for file_type, path in report["new_files"].items():
            click.echo(f"  • {file_type}: {path}")

    if not dry_run:
        click.echo("\nTo rollback this migration, run:")
        click.echo(f"  leonai migrate-config --rollback --config-dir {config_dir}")


if __name__ == "__main__":
    migrate_config_command()
