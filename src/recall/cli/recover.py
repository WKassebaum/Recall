"""Auto-recovery functionality for Recall Qdrant corruption."""

import subprocess
import sys
import time
from pathlib import Path

import click
import requests
from qdrant_client import QdrantClient
from qdrant_client.http import exceptions as qdrant_exceptions


def check_qdrant_health(host: str = "localhost", port: int = 6337, timeout: int = 5) -> bool:
    """Check if Qdrant is healthy and responsive.

    Args:
        host: Qdrant host
        port: Qdrant port
        timeout: Timeout in seconds

    Returns:
        True if healthy, False otherwise
    """
    try:
        # Qdrant health endpoint returns empty body with 200 status
        response = requests.get(f"http://{host}:{port}/health", timeout=timeout)
        # Also try /collections as fallback
        if response.status_code != 200:
            response = requests.get(f"http://{host}:{port}/collections", timeout=timeout)
        return bool(response.status_code == 200)
    except Exception:
        return False


def check_docker_container_status(container_name: str = "recall-qdrant-6337") -> str:
    """Check Docker container status.

    Args:
        container_name: Name of the Qdrant container

    Returns:
        Status string: 'running', 'exited', 'not_found'
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        status = result.stdout.strip()

        if not status:
            return "not_found"
        elif status.startswith("Up"):
            return "running"
        elif status.startswith("Exited"):
            return "exited"
        else:
            return "unknown"
    except subprocess.CalledProcessError:
        return "not_found"


def check_collection_accessible(
    host: str = "localhost", port: int = 6337, collection: str = "recall_768d"
) -> bool:
    """Check if a collection is accessible (no corruption).

    Args:
        host: Qdrant host
        port: Qdrant port
        collection: Collection name to test

    Returns:
        True if accessible, False if corrupted or inaccessible
    """
    try:
        client = QdrantClient(host=host, port=port, timeout=5)
        # Try to get collection info (will fail if corrupted)
        client.get_collection(collection_name=collection)
        return True
    except qdrant_exceptions.UnexpectedResponse:
        # Collection doesn't exist yet (not an error)
        return True
    except Exception:
        # Corruption or other error
        return False


def get_latest_backup(backup_dir: Path) -> Path | None:
    """Get the latest good backup.

    Args:
        backup_dir: Directory containing backups

    Returns:
        Path to latest backup, or None if not found
    """
    # Check for latest-good-backup symlink first
    symlink = backup_dir / "latest-good-backup.tar.gz"
    if symlink.exists() and symlink.is_symlink():
        target = symlink.resolve()
        if target.exists():
            return target

    # Fall back to most recent backup in automated/recent/
    recent_dir = backup_dir / "automated" / "recent"
    if recent_dir.exists():
        backups = sorted(recent_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            return backups[0]

    # Fall back to any backup in backup root
    backups = sorted(backup_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    if backups:
        return backups[0]

    return None


def auto_recover_from_backup(
    backup_file: Path,
    container_name: str = "recall-qdrant-6337",
    volume_name: str = "recall-qdrant-data",
    compose_file: Path | None = None,
) -> bool:
    """Automatically recover Qdrant from backup.

    Args:
        backup_file: Path to backup tarball
        container_name: Docker container name
        volume_name: Docker volume name
        compose_file: Path to docker-compose.yml

    Returns:
        True if recovery succeeded, False otherwise
    """
    click.echo(f"🔄 Auto-recovery initiated from: {backup_file.name}")

    try:
        # Step 1: Stop container
        click.echo("   Stopping Qdrant container...")
        if compose_file and compose_file.exists():
            subprocess.run(
                ["docker-compose", "-f", str(compose_file), "down"],
                cwd=compose_file.parent,
                check=True,
                capture_output=True,
            )
        else:
            subprocess.run(["docker", "stop", container_name], check=True, capture_output=True)

        # Step 2: Remove corrupted volume
        click.echo("   Removing corrupted volume...")
        subprocess.run(["docker", "volume", "rm", volume_name], check=True, capture_output=True)

        # Step 3: Create new volume
        click.echo("   Creating new volume...")
        subprocess.run(["docker", "volume", "create", volume_name], check=True, capture_output=True)

        # Step 4: Restore from backup
        click.echo("   Restoring from backup...")
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{volume_name}:/data",
                "-v",
                f"{backup_file.parent}:/backup",
                "alpine",
                "tar",
                "xzf",
                f"/backup/{backup_file.name}",
                "-C",
                "/",
            ],
            check=True,
            capture_output=True,
        )

        # Step 5: Start container
        click.echo("   Starting Qdrant container...")
        if compose_file and compose_file.exists():
            subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d"],
                cwd=compose_file.parent,
                check=True,
                capture_output=True,
            )
        else:
            subprocess.run(["docker", "start", container_name], check=True, capture_output=True)

        # Step 6: Wait for startup
        click.echo("   Waiting for Qdrant to start...")
        time.sleep(5)

        # Step 7: Verify health
        if check_qdrant_health():
            click.echo("✅ Auto-recovery successful!")
            return True
        else:
            click.echo("⚠️  Container started but health check failed")
            return False

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Auto-recovery failed: {e}", err=True)
        return False


@click.command()
@click.option("--force", is_flag=True, help="Force recovery even if health checks pass")
@click.option(
    "--backup",
    type=click.Path(exists=True, path_type=Path),
    help="Specific backup file to restore from",
)
def recover(force: bool, backup: Path | None) -> None:
    """Check Qdrant health and auto-recover if needed.

    This command:
    1. Checks if Qdrant container is running
    2. Checks if Qdrant is responding to health checks
    3. Checks if collections are accessible (no corruption)
    4. Auto-recovers from latest backup if corruption detected

    Examples:
        recall recover              # Check health, auto-recover if needed
        recall recover --force      # Force recovery from latest backup
        recall recover --backup backups/recall-backup-20251018.tar.gz
    """
    click.echo("🔍 Running Recall health diagnostics...")
    click.echo()

    # Find project root and backup directory
    project_root = Path(__file__).parent.parent.parent.parent
    backup_dir = project_root / "backups"
    compose_file = project_root / "docker-compose.yml"

    # Check 1: Container status
    click.echo("1️⃣  Checking Docker container...")
    container_status = check_docker_container_status()
    click.echo(f"   Status: {container_status}")

    if container_status == "not_found":
        click.echo("❌ Qdrant container not found. Run: docker-compose up -d")
        sys.exit(1)

    # Check 2: Qdrant health
    click.echo("\n2️⃣  Checking Qdrant health...")
    is_healthy = check_qdrant_health()
    click.echo(f"   Healthy: {is_healthy}")

    # Check 3: Collection accessibility
    click.echo("\n3️⃣  Checking collection accessibility...")
    is_accessible = check_collection_accessible()
    click.echo(f"   Accessible: {is_accessible}")

    # Determine if recovery needed
    needs_recovery = force or not is_healthy or not is_accessible

    if not needs_recovery:
        click.echo("\n✅ All health checks passed! No recovery needed.")
        sys.exit(0)

    # Recovery needed
    click.echo("\n⚠️  Issues detected. Recovery needed.")

    # Find backup to use
    backup_file: Path | None
    if backup:
        backup_file = backup
    else:
        click.echo("\n4️⃣  Finding latest backup...")
        backup_file = get_latest_backup(backup_dir)

        if not backup_file:
            click.echo("❌ No backups found. Cannot auto-recover.")
            click.echo("   Create a backup first: ./scripts/backup-qdrant.sh")
            sys.exit(1)

    click.echo(f"   Using backup: {backup_file.name}")
    backup_age = time.time() - backup_file.stat().st_mtime
    click.echo(f"   Backup age: {backup_age / 3600:.1f} hours")

    # Confirm recovery
    if not force:
        click.echo()
        click.echo("⚠️  This will REPLACE current data with backup.")
        if not click.confirm("Continue with recovery?"):
            click.echo("Recovery cancelled.")
            sys.exit(0)

    # Perform recovery
    click.echo()
    success = auto_recover_from_backup(backup_file=backup_file, compose_file=compose_file)

    if success:
        click.echo()
        click.echo("🎉 Recovery complete! Qdrant is healthy.")
        sys.exit(0)
    else:
        click.echo()
        click.echo("❌ Recovery failed. Check logs: docker logs recall-qdrant-6337")
        sys.exit(1)
