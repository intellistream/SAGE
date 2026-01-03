#!/usr/bin/env python3
"""
SAGE Configuration Manager
统一的配置文件管理
"""

from pathlib import Path
from typing import Any

import typer
import yaml  # type: ignore[import-untyped]


def find_project_root() -> Path | None:
    """查找项目根目录（包含 .git 或 pyproject.toml 的目录）"""
    d = Path.cwd()
    root = Path(d.root)
    while d != root:
        if (d / ".git").exists() or (d / "pyproject.toml").exists():
            return d
        d = d.parent
    return None


class ConfigManager:
    """配置管理器"""

    # 配置文件名
    CONFIG_FILENAME = "cluster.yaml"

    def __init__(self, config_path: str | None = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            # 搜索路径优先级：
            # 1. 项目根目录/config/cluster.yaml (推荐)
            # 2. 当前目录/config/cluster.yaml
            # 3. ~/.sage/cluster.yaml (用户级别配置)
            # 4. 兼容旧路径: ~/.sage/config.yaml

            paths_to_check = []

            # 1. 项目根目录
            project_root = find_project_root()
            if project_root:
                paths_to_check.append(project_root / "config" / self.CONFIG_FILENAME)

            # 2. 当前目录
            paths_to_check.append(Path.cwd() / "config" / self.CONFIG_FILENAME)

            # 3. 用户目录 (新路径)
            paths_to_check.append(Path.home() / ".sage" / self.CONFIG_FILENAME)

            # 4. 兼容旧路径
            paths_to_check.append(Path.home() / ".sage" / "config.yaml")

            # 默认值: 项目根目录或用户目录
            if project_root:
                default_path = project_root / "config" / self.CONFIG_FILENAME
            else:
                default_path = Path.home() / ".sage" / self.CONFIG_FILENAME

            selected_path = default_path

            for p in paths_to_check:
                if p.exists():
                    selected_path = p
                    break

            self.config_path = selected_path
        self._config: dict[str, Any] | None = None

    def load_config(self) -> dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {self.config_path}\n请运行 'sage config create' 创建默认配置"
            )

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
        """获取head节点配置"""
        return self.config.get("head", {})

    def get_worker_config(self) -> dict[str, Any]:
        """获取worker配置"""
        return self.config.get("worker", {})

    def get_ssh_config(self) -> dict[str, Any]:
        """获取SSH配置"""
        return self.config.get("ssh", {})

    def get_remote_config(self) -> dict[str, Any]:
        """获取远程路径配置"""
        return self.config.get("remote", {})

    def get_workers_ssh_hosts(self) -> list[tuple[str, int]]:
        """解析worker SSH主机列表"""
        # 先从ssh.workers中读取
        ssh_config = self.get_ssh_config()
        workers = ssh_config.get("workers", [])

        if workers:
            return [(w["host"], w.get("port", 22)) for w in workers]

        # 兼容旧的workers_ssh_hosts格式
        hosts_str = self.config.get("workers_ssh_hosts", "")
        if not hosts_str:
            return []

        # 检查是否为列表格式（新格式测试）
        if isinstance(hosts_str, list):
            return [(item["host"], item.get("port", 22)) for item in hosts_str]

        nodes = []
        for node in hosts_str.split(","):
            node = node.strip()
            if ":" in node:
                host, port = node.split(":", 1)
                port = int(port)
            else:
                host = node
                port = 22  # 默认SSH端口
            nodes.append((host, port))
        return nodes

    def create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            "head": {
                "host": "localhost",
                "head_port": 6379,
                "dashboard_port": 8265,
                "dashboard_host": "0.0.0.0",
                "temp_dir": "/var/tmp/ray",
                "log_dir": "/var/tmp/sage_head_logs",
                "conda_env": "sage",
                "python_path": "",  # 自动检测
                "ray_command": "",  # 自动检测
                "sage_home": "",
            },
            "worker": {
                "bind_host": "localhost",
                "temp_dir": "/tmp/ray_worker",
                "log_dir": "/tmp/sage_worker_logs",
            },
            "ssh": {
                "user": "sage",
                "key_path": "~/.ssh/id_rsa",
                "connect_timeout": 10,
                "workers": [
                    # {"host": "sage2", "port": 22},
                    # {"host": "sage3", "port": 22},
                    # {"host": "sage4", "port": 22},
                ],
            },
            "remote": {
                "sage_home": "/home/sage",
                "python_path": "",  # 自动检测
                "ray_command": "",  # 自动检测
                "conda_env": "sage",
            },
            "daemon": {
                "host": "localhost",
                "port": 19001,
            },
            "output": {
                "format": "table",
                "colors": True,
            },
            "monitor": {
                "refresh_interval": 5,
            },
            "jobmanager": {
                "timeout": 30,
                "retry_attempts": 3,
            },
        }

        self.save_config(default_config)
        return default_config


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
    print(f"配置文件路径: {config_manager.config_path}")
    try:
        config = config_manager.load_config()
        print("\n当前配置:")
        import pprint

        pprint.pprint(config)
    except FileNotFoundError as e:
        print(f"\n{e}")


@app.command()
def create(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Configuration file path"),
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已存在的配置文件"),
):
    """创建默认配置"""
    config_manager = get_config_manager(config_path)

    if config_manager.config_path.exists() and not force:
        print(f"配置文件已存在: {config_manager.config_path}")
        print("使用 --force 覆盖")
        return

    config_manager.create_default_config()
    print(f"默认配置已创建: {config_manager.config_path}")


@app.command()
def path(
    config_path: str | None = typer.Option(None, "--config", "-c", help="Configuration file path"),
):
    """显示配置文件路径"""
    config_manager = get_config_manager(config_path)
    print(config_manager.config_path)


@app.command("set")
def set_value(
    key: str = typer.Argument(..., help="Configuration key (支持点号分隔，如 head.host)"),
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

        # 尝试转换类型
        try:
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)
            elif "." in value and all(p.isdigit() for p in value.split(".", 1)):
                value = float(value)
        except (ValueError, AttributeError):
            pass

        current[keys[-1]] = value
        config_manager.save_config(config)
        print(f"配置已更新: {key} = {value}")
    except FileNotFoundError as e:
        print(f"{e}")


@app.command()
def add_worker(
    host: str = typer.Argument(..., help="Worker hostname"),
    port: int = typer.Option(22, "--port", "-p", help="SSH port"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Configuration file path"),
):
    """添加 worker 节点"""
    config_manager = get_config_manager(config_path)
    try:
        config = config_manager.load_config()

        # 确保 ssh.workers 存在
        if "ssh" not in config:
            config["ssh"] = {}
        if "workers" not in config["ssh"]:
            config["ssh"]["workers"] = []

        # 检查是否已存在
        for w in config["ssh"]["workers"]:
            if w["host"] == host and w.get("port", 22) == port:
                print(f"Worker 已存在: {host}:{port}")
                return

        config["ssh"]["workers"].append({"host": host, "port": port})
        config_manager.save_config(config)
        print(f"已添加 worker: {host}:{port}")
    except FileNotFoundError as e:
        print(f"{e}")


@app.command()
def remove_worker(
    host: str = typer.Argument(..., help="Worker hostname"),
    port: int = typer.Option(22, "--port", "-p", help="SSH port"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Configuration file path"),
):
    """移除 worker 节点"""
    config_manager = get_config_manager(config_path)
    try:
        config = config_manager.load_config()

        workers = config.get("ssh", {}).get("workers", [])
        original_len = len(workers)

        config["ssh"]["workers"] = [
            w for w in workers if not (w["host"] == host and w.get("port", 22) == port)
        ]

        if len(config["ssh"]["workers"]) < original_len:
            config_manager.save_config(config)
            print(f"已移除 worker: {host}:{port}")
        else:
            print(f"未找到 worker: {host}:{port}")
    except FileNotFoundError as e:
        print(f"{e}")


if __name__ == "__main__":
    app()
