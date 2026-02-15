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
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate migration without writing files",
)
@click.option(
    "--config-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Configuration directory (default: ~/.leon)",
)
@click.option(
    "--rollback",
    is_flag=True,
    help="Rollback migration by restoring backup files",
)
def migrate_config_command(dry_run: bool, config_dir: Path | None, rollback: bool) -> None:
    """Migrate old profile.yaml configuration to new config.json format.

    This command migrates from the old configuration format:
    - profile.yaml (agent/tool/mcp/skills sections)
    - config.env (environment variables)

    To the new format:
    - config.json (unified configuration)
    - .env (environment variables)

    Old files are backed up with .bak suffix before migration.
    """
    # Default to ~/.leon
    if config_dir is None:
        config_dir = Path.home() / ".leon"

    migrator = ConfigMigrator(config_dir)

    # Handle rollback
    if rollback:
        try:
            click.echo(f"Rolling back migration in {config_dir}...")
            migrator.rollback()
            click.secho("✓ Migration rolled back successfully", fg="green")
            return
        except ConfigMigrationError as e:
            click.secho(f"✗ Rollback failed: {e}", fg="red", err=True)
            sys.exit(1)

    # Detect old configuration
    try:
        old_files = migrator.detect_old_config()
    except Exception as e:
        click.secho(f"✗ Error detecting old configuration: {e}", fg="red", err=True)
        sys.exit(1)

    if not old_files:
        click.secho("No old configuration files found. Nothing to migrate.", fg="yellow")
        sys.exit(0)

    # Show detected files
    click.echo("Detected old configuration files:")
    for file_type, path in old_files.items():
        click.echo(f"  • {file_type}: {path}")
    click.echo()

    # Confirm migration
    if not dry_run:
        if not click.confirm("Proceed with migration?"):
            click.echo("Migration cancelled.")
            sys.exit(0)

    # Run migration
    try:
        report = migrator.migrate(dry_run=dry_run)
    except ConfigMigrationError as e:
        click.secho(f"✗ Migration failed: {e}", fg="red", err=True)
        if "validation" in str(e):
            click.echo("\nValidation errors found. Please fix the configuration and try again.")
        sys.exit(1)

    # Show migration report
    if dry_run:
        click.secho("✓ Dry run completed successfully", fg="green")
        click.echo("\nMigration preview:")
    else:
        click.secho("✓ Migration completed successfully", fg="green")
        click.echo("\nMigration summary:")

    # Show changes
    if report["changes"]["renamed_sections"]:
        click.echo("\nRenamed sections:")
        for change in report["changes"]["renamed_sections"]:
            click.echo(f"  • {change}")

    if report["changes"]["new_fields"]:
        click.echo("\nNew fields:")
        for field in report["changes"]["new_fields"]:
            click.echo(f"  + {field}")

    if report["changes"]["removed_fields"]:
        click.echo("\nRemoved fields:")
        for field in report["changes"]["removed_fields"]:
            click.echo(f"  - {field}")

    # Show new files
    if not dry_run and report["new_files"]:
        click.echo("\nNew files created:")
        for file_type, path in report["new_files"].items():
            click.echo(f"  • {file_type}: {path}")

    # Show backups
    if not dry_run and "backups" in report:
        click.echo("\nBackup files created:")
        for file_type, path in report["backups"].items():
            click.echo(f"  • {file_type}: {path}")

    # Show validation results
    if report["validation"]["errors"]:
        click.echo("\nValidation errors:")
        for error in report["validation"]["errors"]:
            click.secho(f"  ✗ {error}", fg="red")
        sys.exit(1)

    if not dry_run:
        click.echo("\nTo rollback this migration, run:")
        click.echo(f"  leonai migrate-config --rollback --config-dir {config_dir}")


if __name__ == "__main__":
    migrate_config_command()
