from __future__ import annotations

from pathlib import Path

from sage.runtime.flownet.node import cli as node_cli


def test_cluster_up_dry_run_uses_in_repo_node_cli_module(
    tmp_path: Path,
    capsys,
) -> None:
    identity_file = tmp_path / "id_ed25519"
    identity_file.write_text("test-key", encoding="utf-8")

    inventory_path = tmp_path / "inventory.yaml"
    inventory_path.write_text(
        "\n".join(
            [
                "ssh:",
                "  user: root",
                f"  identity_file: {identity_file}",
                "nodes:",
                "  - node_id: node-a",
                "    ssh_target: localhost",
                "    bind_address: 127.0.0.1:19001",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = node_cli.main(
        [
            "cluster",
            "up",
            "--dry-run",
            "--inventory",
            str(inventory_path),
            "--remote-repo-root",
            "/tmp/remote-repo",
            "--remote-inventory-path",
            str(inventory_path),
            "--remote-python",
            "/usr/bin/python3",
            "--ssh-user",
            "root",
            "--ssh-identity-file",
            str(identity_file),
        ]
    )

    assert exit_code == 0

    stdout = capsys.readouterr().out
    assert "/usr/bin/python3 -m sage.runtime.flownet.node.cli cluster start" in stdout
    assert "/usr/bin/python3 -m flownet.node.cli cluster start" not in stdout
    assert "ConnectTimeout=10" in stdout
    assert "ConnectTimeout=10.0" not in stdout
