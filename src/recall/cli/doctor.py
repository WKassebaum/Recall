"""Diagnostic command to validate Recall installation health."""

import os
import subprocess
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def check_python_version() -> tuple[bool, str]:
    """Check if Python version meets requirements."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major == 3 and version.minor >= 10:
        return (True, f"Python {version_str}")
    return (False, f"Python {version_str} (requires 3.10+)")


def check_virtual_environment() -> tuple[bool, str]:
    """Check if running in a virtual environment."""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if in_venv:
        venv_path = sys.prefix
        return (True, f"Virtual environment detected: {venv_path}")
    return (False, "Not in virtual environment (recommended for installation)")


def check_qdrant_connection() -> tuple[bool, str]:
    """Check Qdrant connectivity."""
    # Load .env configuration
    env_file = Path.home() / ".recall" / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    mode = os.environ.get("RECALL_QDRANT_MODE", "embedded")

    try:
        if mode == "network":
            host = os.environ.get("RECALL_QDRANT_HOST", "localhost")
            port = int(os.environ.get("RECALL_QDRANT_PORT", "6333"))
            client = QdrantClient(host=host, port=port, timeout=3)
            client.get_collections()
            return (True, f"Qdrant running: {host}:{port} ({mode} mode)")
        else:
            path = os.environ.get("RECALL_QDRANT_PATH", "~/.recall/qdrant")
            expanded_path = os.path.expanduser(path)
            client = QdrantClient(path=expanded_path, timeout=3)
            client.get_collections()
            return (True, f"Qdrant embedded: {expanded_path}")
    except Exception as e:
        return (False, f"Qdrant connection failed: {e}")


def check_config_file() -> tuple[bool, str]:
    """Check if configuration file exists."""
    env_file = Path.home() / ".recall" / ".env"
    config_file = Path("config.yaml")

    if env_file.exists():
        return (True, f"Config valid: {env_file}")
    elif config_file.exists():
        return (True, f"Config valid: {config_file}")
    return (False, "No configuration found - run 'recall setup'")


def check_embedder_model() -> tuple[bool, str]:
    """Check if embedding model is available."""
    try:
        from sentence_transformers import SentenceTransformer

        # Try to load the default model
        model_name = os.environ.get("RECALL_EMBEDDER_MODEL", "Snowflake/snowflake-arctic-embed-m")
        model = SentenceTransformer(model_name)
        dimension = model.get_sentence_embedding_dimension()

        return (True, f"Embedder model available: {model_name.split('/')[-1]} ({dimension}D)")
    except Exception as e:
        return (False, f"Embedder model error: {e}")


def check_mcp_config() -> tuple[bool, str | None]:
    """Check MCP configuration for common issues."""
    mcp_file = Path.home() / ".mcp.json"

    if not mcp_file.exists():
        return (False, "MCP config not found: ~/.mcp.json")

    try:
        import json

        with open(mcp_file) as f:
            config = json.load(f)

        if "mcpServers" not in config:
            return (False, "MCP config missing 'mcpServers' section")

        if "recall" not in config["mcpServers"]:
            return (False, "Recall not configured in MCP servers")

        recall_config = config["mcpServers"]["recall"]
        command = recall_config.get("command", "")

        # Check if using system Python instead of venv
        if command == "python" or command == "python3":
            return (
                False,
                "⚠️  MCP config uses 'python' instead of venv path\n"
                "   Fix: Update .mcp.json command to full venv path:\n"
                f'   "command": "{sys.prefix}/bin/python"',
            )

        return (True, "MCP configuration valid")

    except Exception as e:
        return (False, f"Error reading MCP config: {e}")


def find_datetime_deprecations() -> tuple[bool, str | None]:
    """Check for datetime.utcnow() usage (deprecated in Python 3.12+)."""
    project_root = Path.cwd()
    src_dir = project_root / "src" / "recall"

    if not src_dir.exists():
        return (True, None)  # Not in project directory, skip check

    try:
        result = subprocess.run(
            ["grep", "-r", "datetime.utcnow()", str(src_dir)],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout:
            count = len(result.stdout.strip().split("\n"))
            return (
                False,
                f"Found {count} datetime.utcnow() calls (deprecated in Python 3.12+)\n"
                "   Fix: Use datetime.now(timezone.utc) instead",
            )

        return (True, None)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return (True, None)  # grep not available or timeout, skip


def check_docker_available() -> tuple[bool, str]:
    """Check if Docker is available (for network mode)."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            version = result.stdout.strip().split()[2].rstrip(",")
            return (True, f"Docker available: {version}")
        return (False, "Docker not available")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return (False, "Docker not installed")


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed diagnostic information",
)
def doctor(verbose: bool) -> None:
    """Run diagnostic checks on Recall installation.

    Validates:
    - Python version compatibility
    - Virtual environment setup
    - Qdrant connectivity
    - Configuration files
    - Embedding model availability
    - MCP server configuration
    - Common installation issues
    """
    console.print(
        Panel.fit(
            "[bold]Recall Installation Diagnostics[/bold]\n\n"
            "Checking system health and configuration...",
            border_style="cyan",
        )
    )
    print()

    # Run all checks
    checks = [
        ("Python Version", check_python_version()),
        ("Virtual Environment", check_virtual_environment()),
        ("Qdrant Connection", check_qdrant_connection()),
        ("Configuration", check_config_file()),
        ("Embedder Model", check_embedder_model()),
        ("MCP Configuration", check_mcp_config()),
        ("Docker Availability", check_docker_available()),
    ]

    # Add optional checks
    if verbose:
        checks.append(("Datetime Deprecations", find_datetime_deprecations()))

    # Display results
    table = Table(title="Diagnostic Results", show_header=True)
    table.add_column("Check", style="cyan", width=25)
    table.add_column("Status", width=10)
    table.add_column("Details", style="dim")

    all_passed = True
    warnings = []
    errors = []

    for check_name, (passed, message) in checks:
        if passed:
            status = "[green]✅ PASS[/green]"
            table.add_row(check_name, status, message or "")
        else:
            status = "[red]❌ FAIL[/red]"
            all_passed = False
            table.add_row(check_name, status, message or "")

            if message and "⚠️" in message:
                warnings.append((check_name, message))
            else:
                errors.append((check_name, message))

    console.print(table)
    print()

    # Show summary
    if all_passed:
        summary = Panel(
            "[bold green]✅ All checks passed![/bold green]\n\n"
            "Your Recall installation is healthy and ready to use.",
            title="Summary",
            border_style="green",
        )
    elif errors:
        error_msg = "\n".join([f"• {name}: {msg}" for name, msg in errors])
        summary = Panel(
            f"[bold red]❌ {len(errors)} critical issue(s) found:[/bold red]\n\n"
            f"{error_msg}\n\n"
            "[bold]Next steps:[/bold]\n"
            "1. See INSTALLATION.md for detailed troubleshooting\n"
            "2. Run 'recall setup' to reconfigure\n"
            "3. Check https://github.com/WKassebaum/Recall/issues",
            title="Summary",
            border_style="red",
        )
    else:
        warning_msg = "\n".join([f"• {name}" for name, _ in warnings])
        summary = Panel(
            f"[bold yellow]⚠️  {len(warnings)} warning(s) found:[/bold yellow]\n\n"
            f"{warning_msg}\n\n"
            "Recall should work but some features may be limited.",
            title="Summary",
            border_style="yellow",
        )

    console.print(summary)
    print()

    # Show suggestions
    if not all_passed:
        console.print("[bold]💡 Suggestions:[/bold]")

        for check_name, (passed, message) in checks:
            if not passed and message:
                console.print(f"\n[yellow]{check_name}:[/yellow]")
                console.print(f"  {message}")

        print()

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    doctor()
