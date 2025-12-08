#!/usr/bin/env python3
"""
SAGE Configuration Manager
统一的配置文件管理

Configuration search priority:
1. Explicitly provided config_path
2. Project-level: <project_root>/config/config.yaml
3. Fallback: ~/.config/sage/config.yaml (XDG standard)
"""

from pathlib import Path
from typing import Any

import typer
import yaml  # type: ignore[import-untyped]


def _find_project_root() -> Path | None:
    """Find SAGE project root by looking for characteristic markers."""
    d = Path.cwd()
    root = Path(d.root)
    while d != root:
        # Check for SAGE project markers
        if (d / "packages" / "sage-common").exists() or (d / "quickstart.sh").exists():
            return d
        d = d.parent
    return None


def _get_default_config_path() -> Path:
    """Get default config path (XDG fallback)."""
    xdg_config = Path.home() / ".config" / "sage"
    xdg_config.mkdir(parents=True, exist_ok=True)
    return xdg_config / "config.yaml"


class ConfigManager:
    """配置管理器

    Configuration search priority:
    1. Explicitly provided config_path
    2. Project-level: <project_root>/config/config.yaml
    3. Fallback: ~/.config/sage/config.yaml (XDG standard)
    """

    def __init__(self, config_path: str | None = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            # 搜索路径优先级：
            # 1. 项目根目录 config/config.yaml
            # 2. XDG 标准: ~/.config/sage/config.yaml (回退)

            paths_to_check = []

            # 1. 查找项目根目录的 config/
            project_root = _find_project_root()
            if project_root:
                paths_to_check.append(project_root / "config" / "config.yaml")

            # 2. XDG 标准用户配置目录（回退）
            default_config = _get_default_config_path()
            paths_to_check.append(default_config)

            # 默认使用 XDG 标准路径
            selected_path = default_config

            for p in paths_to_check:
                if p.exists():
                    selected_path = p
                    break

            self.config_path = selected_path
        self._config: dict[str, Any] | None = None

    def load_config(self) -> dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        try:
            with open(self.config_path, encoding="utf-8") as f:
                loaded_config: dict[str, Any] = yaml.safe_load(f) or {}
                self._config = loaded_config
            return loaded_config
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {e}")

    def save_config(self, config: dict[str, Any]):
        """保存配置文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            self._config = config
        except Exception as e:
            raise RuntimeError(f"保存配置文件失败: {e}")

    @property
    def config(self) -> dict[str, Any]:
        """获取配置"""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def get_head_config(self) -> dict[str, Any]:
        """获取head节点配置

        Maps new config structure to expected format:
        - provider.head_ip -> host
        - ray.* -> head_port, dashboard_port, etc.
        """
        provider = self.config.get("provider", {})
        ray_config = self.config.get("ray", {})
        remote = self.config.get("remote", {})

        return {
            "host": provider.get("head_ip", "localhost"),
            "head_port": ray_config.get("head_port", 6379),
            "dashboard_port": ray_config.get("dashboard_port", 8265),
            "dashboard_host": ray_config.get("dashboard_host", "0.0.0.0"),
            "temp_dir": ray_config.get("temp_dir", "/tmp/ray"),
            "log_dir": ray_config.get("log_dir", "/tmp/sage_head_logs"),
            "ray_command": remote.get("ray_command"),
            "conda_env": remote.get("conda_env", "sage"),
        }

    def get_worker_config(self) -> dict[str, Any]:
        """获取worker配置"""
        ray_config = self.config.get("ray", {})
        return {
            "bind_host": ray_config.get("worker_bind_host", "0.0.0.0"),
            "temp_dir": ray_config.get("worker_temp_dir", "/tmp/ray_worker"),
            "log_dir": ray_config.get("worker_log_dir", "/tmp/sage_worker_logs"),
        }

    def get_ssh_config(self) -> dict[str, Any]:
        """获取SSH配置

        Maps new config structure:
        - auth.ssh_user -> user
        - auth.ssh_private_key -> key_path
        """
        auth = self.config.get("auth", {})
        return {
            "user": auth.get("ssh_user", "sage"),
            "key_path": auth.get("ssh_private_key", "~/.ssh/id_rsa"),
            "connect_timeout": auth.get("connect_timeout", 10),
        }

    def get_remote_config(self) -> dict[str, Any]:
        """获取远程路径配置"""
        return self.config.get("remote", {})

    def get_workers_ssh_hosts(self) -> list[tuple[str, int]]:
        """解析worker SSH主机列表

        Reads from provider.worker_ips (new format)
        """
        provider = self.config.get("provider", {})
        worker_ips = provider.get("worker_ips", [])

        if not worker_ips:
            return []

        # worker_ips is a list of IP strings
        return [(ip, 22) for ip in worker_ips]

    def add_worker_ip(self, ip: str) -> bool:
        """添加新的worker IP"""
        provider = self.config.get("provider", {})
        worker_ips = provider.get("worker_ips", [])

        if ip in worker_ips:
            return False

        worker_ips.append(ip)
        provider["worker_ips"] = worker_ips
        self.config["provider"] = provider
        self.save_config(self.config)
        return True

    def remove_worker_ip(self, ip: str) -> bool:
        """移除worker IP"""
        provider = self.config.get("provider", {})
        worker_ips = provider.get("worker_ips", [])

        if ip not in worker_ips:
            return False

        worker_ips.remove(ip)
        provider["worker_ips"] = worker_ips
        self.config["provider"] = provider
        self.save_config(self.config)
        return True


def get_config_manager(config_path: str | None = None) -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager(config_path)


# Typer应用
app = typer.Typer(help="SAGE configuration management")


@app.command()
def show(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Configuration file path"),
):
    """显示当前配置"""
    config_manager = get_config_manager(config_path)
    try:
        config = config_manager.load_config()
        print(f"配置文件: {config_manager.config_path}")
        print("当前配置:")
        import pprint

        pprint.pprint(config)
    except FileNotFoundError:
        print(f"配置文件不存在: {config_manager.config_path}")
        print("请运行 'sage cluster init' 创建配置")


@app.command()
def path(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Configuration file path"),
):
    """显示配置文件路径"""
    config_manager = get_config_manager(config_path)
    print(config_manager.config_path)


@app.command("set")
def set_value(
    key: str = typer.Argument(..., help="Configuration key (dot notation: provider.head_ip)"),
    value: str = typer.Argument(..., help="Configuration value"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Configuration file path"),
):
    """设置配置值"""
    config_manager = get_config_manager(config_path)
    try:
        config = config_manager.load_config()
        # Simple dot notation support for nested keys
        keys = key.split(".")
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        config_manager.save_config(config)
        print(f"配置已更新: {key} = {value}")
    except FileNotFoundError:
        print("配置文件不存在，请运行 'sage cluster init' 创建配置")


if __name__ == "__main__":
    app()
