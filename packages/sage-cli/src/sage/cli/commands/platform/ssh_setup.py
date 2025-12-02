"""SSH Key Setup Tool for SAGE Cluster.

This module provides SSH key generation and distribution utilities.
Only SSH key authentication is supported (no passwords).

Usage:
    sage cluster setup-ssh          # Interactive setup
    sage cluster setup-ssh --verify # Verify existing setup
"""

import os
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def generate_ssh_key(key_path: str, force: bool = False) -> bool:
    """Generate SSH key pair if not exists."""
    key_path = os.path.expanduser(key_path)
    key_file = Path(key_path)

    if key_file.exists() and not force:
        console.print(f"[green]SSH key already exists: {key_path}[/green]")
        return True

    if key_file.exists() and force:
        console.print(f"[yellow]Regenerating SSH key: {key_path}[/yellow]")
        key_file.unlink()
        Path(f"{key_path}.pub").unlink(missing_ok=True)

    console.print("[blue]Generating SSH key pair...[/blue]")

    try:
        ssh_dir = key_file.parent
        ssh_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(ssh_dir, 0o700)

        result = subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "rsa",
                "-b",
                "4096",
                "-f",
                key_path,
                "-N",
                "",
                "-C",
                "sage-cluster-key",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            console.print(f"[red]Failed to generate SSH key: {result.stderr}[/red]")
            return False

        os.chmod(key_path, 0o600)
        os.chmod(f"{key_path}.pub", 0o644)

        console.print(f"[green]SSH key generated: {key_path}[/green]")
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]SSH key generation timed out[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error generating SSH key: {e}[/red]")
        return False


def verify_ssh_connection(host: str, user: str, key_path: str, port: int = 22) -> bool:
    """Test SSH connection without password."""
    key_path = os.path.expanduser(key_path)

    try:
        result = subprocess.run(
            [
                "ssh",
                "-i",
                key_path,
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-p",
                str(port),
                f"{user}@{host}",
                "echo SSH_OK",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0 and "SSH_OK" in result.stdout
    except (subprocess.TimeoutExpired, Exception):
        return False


def deploy_ssh_key(host: str, user: str, key_path: str, port: int = 22) -> bool:
    """Deploy SSH public key to remote host."""
    key_path = os.path.expanduser(key_path)
    pub_key_path = f"{key_path}.pub"

    if verify_ssh_connection(host, user, key_path, port):
        console.print(f"[green]SSH key already deployed to {host}[/green]")
        return True

    console.print(f"[blue]Deploying SSH key to {user}@{host}...[/blue]")

    try:
        with open(pub_key_path) as f:
            pub_key = f.read().strip()
    except FileNotFoundError:
        console.print(f"[red]Public key not found: {pub_key_path}[/red]")
        return False

    console.print(f"[yellow]Please enter password for {user}@{host} when prompted[/yellow]")
    try:
        result = subprocess.run(
            [
                "ssh-copy-id",
                "-i",
                pub_key_path,
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-p",
                str(port),
                f"{user}@{host}",
            ],
            timeout=60,
        )
        if result.returncode == 0:
            console.print(f"[green]SSH key deployed to {host}[/green]")
            return True
    except subprocess.TimeoutExpired:
        console.print("[yellow]ssh-copy-id timed out[/yellow]")
    except FileNotFoundError:
        console.print("[yellow]ssh-copy-id not available[/yellow]")

    console.print(f"\n[yellow]Manual setup required for {host}:[/yellow]")
    console.print(f"1. SSH to the host: ssh -p {port} {user}@{host}")
    console.print("2. Run: mkdir -p ~/.ssh && chmod 700 ~/.ssh")
    console.print(f"3. Add this to ~/.ssh/authorized_keys:\n   {pub_key}")
    console.print("4. Run: chmod 600 ~/.ssh/authorized_keys")
    return False


def test_passwordless_login(host: str, user: str, key_path: str, port: int = 22) -> dict:
    """Test passwordless SSH login and return details."""
    key_path = os.path.expanduser(key_path)

    result = {
        "host": host,
        "user": user,
        "port": port,
        "key_path": key_path,
        "success": False,
        "message": "",
    }

    if not Path(key_path).exists():
        result["message"] = "Private key not found"
        return result

    if not Path(f"{key_path}.pub").exists():
        result["message"] = "Public key not found"
        return result

    if verify_ssh_connection(host, user, key_path, port):
        result["success"] = True
        result["message"] = "Passwordless login works"
    else:
        result["message"] = "Connection failed (key not deployed or host unreachable)"

    return result


def setup_ssh_for_hosts(hosts: list, user: str, key_path: str, generate_key: bool = True) -> dict:
    """Setup SSH keys for multiple hosts."""
    results = {"key_generated": False, "hosts": {}}

    if generate_key:
        results["key_generated"] = generate_ssh_key(key_path)
        if not results["key_generated"]:
            console.print("[red]Failed to generate SSH key[/red]")
            return results

    for host, port in hosts:
        host_key = f"{host}:{port}"
        deployed = deploy_ssh_key(host, user, key_path, port)
        results["hosts"][host_key] = {
            "deployed": deployed,
            "verified": verify_ssh_connection(host, user, key_path, port),
        }

    return results


def print_status_table(results: dict, user: str, key_path: str):
    """Print a formatted status table."""
    table = Table(title="SSH Setup Status")
    table.add_column("Host", style="cyan")
    table.add_column("Port", style="blue")
    table.add_column("Deployed", style="green")
    table.add_column("Verified", style="green")

    for host_key, status in results.get("hosts", {}).items():
        host, port = host_key.rsplit(":", 1)
        deployed = "Y" if status.get("deployed") else "N"
        verified = "Y" if status.get("verified") else "N"
        table.add_row(host, port, deployed, verified)

    console.print(table)
    console.print(f"\n[dim]User: {user}[/dim]")
    console.print(f"[dim]Key: {key_path}[/dim]")
