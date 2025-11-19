"""HDFS Configuration

Layer: L2 (Platform Services - Storage Module)

HDFS 连接配置类,用于管理 HDFS 集群连接参数。
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HDFSConfig:
    """HDFS 连接配置类 / HDFS Connection Configuration

    用于配置 HDFS 集群的连接参数,支持从环境变量、字典等多种方式初始化。
    """

    # 核心参数 / Core Parameters
    namenode_host: str = "localhost"  # HDFS NameNode 主机地址
    namenode_port: int = 9000  # HDFS NameNode 端口 (默认 9000)
    user: str = field(default_factory=lambda: os.getenv("USER", "hdfs"))  # HDFS 用户名

    # 存储参数 / Storage Parameters
    base_path: str = "/sage"  # HDFS 基础路径前缀
    replication: int = 3  # HDFS 副本数量 (建议 3-5)
    block_size: int = 134217728  # HDFS 块大小 128 MB

    # 连接池参数 / Connection Pool Parameters
    max_connections: int = 10  # 最大连接数
    connection_timeout: int = 30  # 连接超时时间(秒)

    # 重试参数 / Retry Parameters
    retry_attempts: int = 3  # 最大重试次数
    retry_delay: float = 1.0  # 初始重试延迟(秒)
    retry_backoff: float = 2.0  # 重试退避因子 (指数退避)

    # 安全参数 / Security Parameters
    kerberos_enabled: bool = False  # 是否启用 Kerberos 认证
    kerberos_principal: Optional[str] = None  # Kerberos 主体名称
    kerberos_keytab: Optional[str] = None  # Kerberos keytab 文件路径

    # 高可用参数 / High Availability Parameters
    ha_enabled: bool = False  # 是否启用 HDFS HA
    nameservice: Optional[str] = None  # HDFS NameService ID (HA 模式)
    namenodes: Optional[list[str]] = None  # NameNode 节点列表 (HA 模式)

    # 性能参数 / Performance Parameters
    buffer_size: int = 4096  # I/O 缓冲区大小 4 KB
    read_timeout: int = 60  # 读取超时时间(秒)
    write_timeout: int = 60  # 写入超时时间(秒)

    def validate(self) -> None:
        """验证配置参数的有效性 / Validate configuration parameters"""
        if not 1 <= self.namenode_port <= 65535:
            raise ValueError(f"Invalid namenode_port: {self.namenode_port}")
        if not 1 <= self.replication <= 10:
            raise ValueError(f"Invalid replication: {self.replication}")
        if self.block_size < 1048576:  # 至少 1MB
            raise ValueError(f"Invalid block_size: {self.block_size}")
        if self.max_connections < 1:
            raise ValueError(f"Invalid max_connections: {self.max_connections}")
        if self.connection_timeout <= 0:
            raise ValueError(f"Invalid connection_timeout: {self.connection_timeout}")
        if self.retry_attempts < 0:
            raise ValueError(f"Invalid retry_attempts: {self.retry_attempts}")
        if self.retry_delay < 0:
            raise ValueError(f"Invalid retry_delay: {self.retry_delay}")
        if self.retry_backoff < 1.0:
            raise ValueError(f"Invalid retry_backoff: {self.retry_backoff}")
        if self.buffer_size < 512:
            raise ValueError(f"Invalid buffer_size: {self.buffer_size}")
        if self.read_timeout <= 0:
            raise ValueError(f"Invalid read_timeout: {self.read_timeout}")
        if self.write_timeout <= 0:
            raise ValueError(f"Invalid write_timeout: {self.write_timeout}")
        if self.ha_enabled:
            if not self.nameservice:
                raise ValueError("HA enabled but nameservice not specified")
            if not self.namenodes or len(self.namenodes) == 0:
                raise ValueError("HA enabled but namenodes list is empty")
        if self.kerberos_enabled and not self.kerberos_principal:
            raise ValueError("Kerberos enabled but principal not specified")

    @classmethod
    def from_env(cls) -> "HDFSConfig":
        """从环境变量创建配置 / Create configuration from environment variables"""

        def parse_bool(value: Optional[str], default: bool) -> bool:
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes")

        def parse_int(value: Optional[str], default: int) -> int:
            if value is None:
                return default
            try:
                return int(value)
            except ValueError:
                return default

        def parse_float(value: Optional[str], default: float) -> float:
            if value is None:
                return default
            try:
                return float(value)
            except ValueError:
                return default

        namenodes_str = os.getenv("HDFS_NAMENODES")
        namenodes = (
            [nn.strip() for nn in namenodes_str.split(",") if nn.strip()] if namenodes_str else None
        )

        return cls(
            namenode_host=os.getenv("HDFS_NAMENODE_HOST", "localhost"),
            namenode_port=parse_int(os.getenv("HDFS_NAMENODE_PORT"), 9000),
            user=os.getenv("HDFS_USER", os.getenv("USER", "hdfs")),
            base_path=os.getenv("HDFS_BASE_PATH", "/sage"),
            replication=parse_int(os.getenv("HDFS_REPLICATION"), 3),
            block_size=parse_int(os.getenv("HDFS_BLOCK_SIZE"), 134217728),
            max_connections=parse_int(os.getenv("HDFS_MAX_CONNECTIONS"), 10),
            connection_timeout=parse_int(os.getenv("HDFS_CONNECTION_TIMEOUT"), 30),
            retry_attempts=parse_int(os.getenv("HDFS_RETRY_ATTEMPTS"), 3),
            retry_delay=parse_float(os.getenv("HDFS_RETRY_DELAY"), 1.0),
            retry_backoff=parse_float(os.getenv("HDFS_RETRY_BACKOFF"), 2.0),
            kerberos_enabled=parse_bool(os.getenv("HDFS_KERBEROS_ENABLED"), False),
            kerberos_principal=os.getenv("HDFS_KERBEROS_PRINCIPAL"),
            kerberos_keytab=os.getenv("HDFS_KERBEROS_KEYTAB"),
            ha_enabled=parse_bool(os.getenv("HDFS_HA_ENABLED"), False),
            nameservice=os.getenv("HDFS_NAMESERVICE"),
            namenodes=namenodes,
            buffer_size=parse_int(os.getenv("HDFS_BUFFER_SIZE"), 4096),
            read_timeout=parse_int(os.getenv("HDFS_READ_TIMEOUT"), 60),
            write_timeout=parse_int(os.getenv("HDFS_WRITE_TIMEOUT"), 60),
        )

    @classmethod
    def from_dict(cls, config_dict: dict) -> "HDFSConfig":
        """从字典创建配置 / Create configuration from dictionary"""
        return cls(**config_dict)

    def to_dict(self) -> dict:
        """转换为字典 / Convert to dictionary"""
        return {
            "namenode_host": self.namenode_host,
            "namenode_port": self.namenode_port,
            "user": self.user,
            "base_path": self.base_path,
            "replication": self.replication,
            "block_size": self.block_size,
            "max_connections": self.max_connections,
            "connection_timeout": self.connection_timeout,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "retry_backoff": self.retry_backoff,
            "kerberos_enabled": self.kerberos_enabled,
            "kerberos_principal": self.kerberos_principal,
            "kerberos_keytab": self.kerberos_keytab,
            "ha_enabled": self.ha_enabled,
            "nameservice": self.nameservice,
            "namenodes": self.namenodes,
            "buffer_size": self.buffer_size,
            "read_timeout": self.read_timeout,
            "write_timeout": self.write_timeout,
        }

    @property
    def connection_string(self) -> str:
        """生成 HDFS 连接字符串 / Generate HDFS connection string

        标准模式: "hdfs://{host}:{port}"
        HA 模式: "hdfs://{nameservice}"
        """
        if self.ha_enabled and self.nameservice:
            return f"hdfs://{self.nameservice}"
        return f"hdfs://{self.namenode_host}:{self.namenode_port}"
