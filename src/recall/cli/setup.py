"""Interactive setup wizard for Recall configuration."""

import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import yaml
from qdrant_client import QdrantClient
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


class SetupWizard:
    """Interactive setup wizard for Recall."""

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".recall"
        self.config_dir.mkdir(exist_ok=True)

        self.env_file = self.config_dir / ".env"
        self.instances_file = self.config_dir / "instances.yaml"

    def detect_system(self) -> dict[str, Any]:
        """Detect system capabilities."""
        console.print("\n[bold]Detecting system...[/bold]")

        detection = {
            "python_version": self._get_python_version(),
            "docker_installed": self._check_docker(),
            "qdrant_running": self._check_qdrant_running(),
        }

        if detection["python_version"]:
            console.print(f"✅ Python {detection['python_version']}")

        if detection["docker_installed"]:
            console.print(f"✅ Docker installed ({detection['docker_installed']})")
        else:
            console.print("⚠️  Docker not installed")

        if detection["qdrant_running"]:
            console.print(f"✅ Qdrant detected: {detection['qdrant_running']}")

        return detection

    def _check_docker(self) -> str | None:
        """Check if Docker is installed and running."""
        try:
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Extract version from "Docker version 24.0.7, build afdd53b"
                parts = result.stdout.strip().split()
                if len(parts) >= 3:
                    return parts[2].rstrip(",")
                return "installed"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def _check_qdrant_running(self) -> str | None:
        """Check if Qdrant is accessible on common ports."""
        for port in [6333, 6334, 6335, 6336]:
            try:
                client = QdrantClient(host="localhost", port=port, timeout=2)
                # Quick health check
                client.get_collections()
                return f"localhost:{port}"
            except Exception:
                continue
        return None

    def _get_python_version(self) -> str:
        """Get Python version."""
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def choose_mode(self, detection: dict[str, Any]) -> str:
        """Present mode choice with explanations."""
        console.print("\n" + "─" * 70)

        table = Table(title="Choose Qdrant Storage Mode", show_header=True)
        table.add_column("Mode", style="cyan", width=20)
        table.add_column("Pros", style="green")
        table.add_column("Cons", style="yellow")

        table.add_row(
            "1. 🐳 Network (Docker)\nRECOMMENDED",
            "✅ Multiple projects\n✅ Multiple windows\n✅ Team ready\n✅ Scalable",
            "⚠️  Requires Docker",
        )

        table.add_row(
            "2. 📦 Embedded (Local)",
            "✅ Zero setup\n✅ Slightly faster",
            "⚠️  ONE PROJECT AT A TIME\n⚠️  File locking\n⚠️  Single window only",
        )

        console.print(table)

        # Warning panel for embedded mode
        warning = Panel(
            "[bold yellow]⚠️  EMBEDDED MODE LIMITATION:[/bold yellow]\n\n"
            "Embedded mode uses file locking, which means:\n"
            "• You can only use Recall in ONE Claude Code window at a time\n"
            "• You CANNOT work on multiple projects simultaneously\n"
            "• Opening a second window will result in 'database locked' errors\n\n"
            "[bold]Recommended:[/bold] Use Network mode for normal usage",
            title="Important",
            border_style="yellow",
        )

        console.print(warning)

        default_choice = "1" if detection["docker_installed"] else "2"

        choice = Prompt.ask("\nYour choice", choices=["1", "2"], default=default_choice)

        return "network" if choice == "1" else "embedded"

    def configure_network_mode(self, detection: dict[str, Any]) -> dict[str, Any]:
        """Configure network mode settings."""
        console.print("\n[bold]Network Mode Configuration[/bold]\n")

        if detection["qdrant_running"]:
            console.print(f"We detected Qdrant running on {detection['qdrant_running']}")
            console.print("\nDo you want to:")
            console.print("1. Use existing Qdrant ✅ Shared with other projects")
            console.print("2. Create new dedicated Qdrant instance (different port)")

            choice = Prompt.ask("Your choice", choices=["1", "2"], default="1")

            if choice == "1":
                host, port = detection["qdrant_running"].split(":")
                return {"host": host, "port": int(port)}

        # Create new instance
        return self._create_new_qdrant_instance()

    def _create_new_qdrant_instance(self) -> dict[str, Any]:
        """Create new Docker Qdrant instance on available port."""
        console.print("\n[bold]Creating new Qdrant instance...[/bold]")

        # Find available port
        port = self._find_available_port(start=6334)
        console.print(f"Using port: {port}")

        # Docker command
        container_name = f"recall-qdrant-{port}"
        data_dir = self.config_dir / f"docker-{port}"
        data_dir.mkdir(exist_ok=True)

        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{port}:6333",
            "-v",
            f"{data_dir}:/qdrant/storage",
            "qdrant/qdrant:latest",
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            console.print(f"✅ Container '{container_name}' created")
            console.print(f"📁 Data directory: {data_dir}")

            # Wait for startup
            console.print("Waiting for Qdrant to start...", end="")
            time.sleep(3)
            console.print(" ✅")

            return {"host": "localhost", "port": port}

        except subprocess.CalledProcessError as e:
            console.print("[red]❌ Failed to create Qdrant container:[/red]")
            console.print(e.stderr)
            raise

    def _find_available_port(self, start: int = 6334) -> int:
        """Find an available port starting from 'start'."""
        for port in range(start, start + 20):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", port)) != 0:
                    return port
        raise RuntimeError("No available ports found in range")

    def test_connection(self, mode: str, config: dict[str, Any]) -> bool:
        """Test the Qdrant connection."""
        console.print("\n[bold]Testing connection...[/bold]")

        try:
            if mode == "network":
                client = QdrantClient(host=config["host"], port=config["port"], timeout=5)
                console.print(f"✅ Connected to {config['host']}:{config['port']}")
            else:
                path = os.path.expanduser(config["path"])
                client = QdrantClient(path=path)
                console.print(f"✅ Embedded Qdrant at {path}")

            # Health check
            collections = client.get_collections()
            console.print(f"✅ Health check passed ({len(collections.collections)} collections)")

            return True

        except Exception as e:
            console.print(f"[red]❌ Connection failed: {e}[/red]")
            return False

    def save_config(self, mode: str, config: dict[str, Any]) -> None:
        """Save configuration to .env and instances.yaml."""
        console.print("\n[bold]Saving configuration...[/bold]")

        # Write .env file
        env_content = self._generate_env_content(mode, config)
        self.env_file.write_text(env_content)
        console.print(f"✅ Config saved to {self.env_file}")

        # Update instances.yaml
        self._update_instances(mode, config)
        console.print(f"✅ Instance registered in {self.instances_file}")

    def _generate_env_content(self, mode: str, config: dict[str, Any]) -> str:
        """Generate .env file content."""
        lines = [
            "# Recall Configuration",
            "# Generated by: recall setup",
            f"# Last updated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "# QDRANT MODE",
            f"RECALL_QDRANT_MODE={mode}",
            "",
        ]

        if mode == "network":
            lines.extend(
                [
                    "# Network Mode Settings (Docker)",
                    f"RECALL_QDRANT_HOST={config['host']}",
                    f"RECALL_QDRANT_PORT={config['port']}",
                    "# RECALL_QDRANT_API_KEY=  # Optional for Qdrant Cloud",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "# Embedded Mode Settings",
                    f"RECALL_QDRANT_PATH={config['path']}",
                    "",
                ]
            )

        lines.extend(
            [
                "# Embedder Settings",
                "RECALL_EMBEDDER_MODEL=Snowflake/snowflake-arctic-embed-m",
                "RECALL_FALLBACK_ENABLED=true",
                "RECALL_FALLBACK_MODEL=all-MiniLM-L6-v2",
            ]
        )

        return "\n".join(lines) + "\n"

    def _update_instances(self, mode: str, config: dict[str, Any]) -> None:
        """Update instances.yaml with new instance."""
        if self.instances_file.exists():
            with open(self.instances_file) as f:
                instances = yaml.safe_load(f) or {}
        else:
            instances = {"active": "default", "instances": {}}

        instances["instances"]["default"] = {
            "name": f"Recall {'Network' if mode == 'network' else 'Embedded'}",
            "mode": mode,
            "created": datetime.now(timezone.utc).isoformat(),
            "projects": [],
        }

        if mode == "network":
            instances["instances"]["default"].update(
                {"host": config["host"], "port": config["port"]}
            )
        else:
            instances["instances"]["default"]["path"] = config["path"]

        with open(self.instances_file, "w") as f:
            yaml.dump(instances, f, default_flow_style=False)

    def show_summary(self, mode: str, config: dict[str, Any]) -> None:
        """Display configuration summary."""
        console.print("\n" + "─" * 70)
        console.print("\n[bold green]✅ Setup complete![/bold green]\n")

        summary = Table(title="Configuration Summary", show_header=False)
        summary.add_column("Setting", style="cyan", width=15)
        summary.add_column("Value", style="white")

        summary.add_row(
            "Mode", f"{'Network (Docker)' if mode == 'network' else 'Embedded (Local)'}"
        )

        if mode == "network":
            summary.add_row("Host", config["host"])
            summary.add_row("Port", str(config["port"]))
            summary.add_row("Data", "Docker volume 'qdrant_storage'")
            summary.add_row("Benefits", "✅ Multi-project ✅ Multi-window ✅ No file locking")
        else:
            summary.add_row("Path", config["path"])
            summary.add_row("Warning", "⚠️  ONE PROJECT AT A TIME (file locking)")

        console.print(summary)

        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Restart Claude Code (Cmd/Ctrl + Q)")
        console.print("2. Run: [cyan]/recall-setup[/cyan] (to verify MCP tools work)")
        console.print("3. Start storing memories: [cyan]/recall-store[/cyan]")
        console.print(
            "\n[dim]Note: You can reconfigure anytime with: recall setup --reconfigure[/dim]"
        )
        console.print("─" * 70 + "\n")

    def run(self) -> None:
        """Run the interactive setup wizard."""
        console.print(
            Panel.fit(
                "[bold]Recall Setup Wizard[/bold]\n\n"
                "Configure Qdrant storage mode for Recall memory system",
                border_style="cyan",
            )
        )

        # Detect system
        detection = self.detect_system()

        # Choose mode
        mode = self.choose_mode(detection)

        # Configure based on mode
        if mode == "network":
            if not detection["docker_installed"]:
                console.print("[red]❌ Docker is required for network mode but not installed[/red]")
                console.print("Install Docker from: https://www.docker.com/get-started")
                raise click.Abort()

            config = self.configure_network_mode(detection)
        else:
            config = {"path": "~/.recall/qdrant/"}

        # Test connection
        if not self.test_connection(mode, config):
            console.print("[red]Setup failed - connection test unsuccessful[/red]")
            raise click.Abort()

        # Save configuration
        self.save_config(mode, config)

        # Show summary
        self.show_summary(mode, config)


@click.command()
@click.option("--reconfigure", is_flag=True, help="Reconfigure existing setup")
def setup(reconfigure: bool) -> None:
    """Interactive setup wizard for Recall configuration."""
    wizard = SetupWizard()

    if wizard.env_file.exists() and not reconfigure:
        console.print("[yellow]⚠️  Configuration already exists[/yellow]")
        if not Confirm.ask("Do you want to reconfigure?"):
            console.print("Setup cancelled. Use --reconfigure to force reconfiguration.")
            return

    wizard.run()


if __name__ == "__main__":
    setup()
