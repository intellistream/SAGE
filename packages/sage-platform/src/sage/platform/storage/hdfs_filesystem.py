"""HDFS FileSystem Operations

Layer: L2 (Platform Services - Storage Module)

HDFS 文件系统操作封装,提供线程安全的连接池、重试机制和完整的文件操作接口。
"""

import logging
from collections import deque
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from sage.platform.utils import retry_with_config

from .hdfs_config import HDFSConfig

logger = logging.getLogger(__name__)


# ========== 异常定义 / Exception Definitions ==========


class HDFSError(Exception):
    """HDFS 基础异常类 / Base HDFS exception"""

    pass


class HDFSConnectionError(HDFSError):
    """HDFS 连接错误 / HDFS connection error"""

    pass


class HDFSFileNotFoundError(HDFSError):
    """HDFS 文件不存在错误 / HDFS file not found error"""

    pass


class HDFSPermissionError(HDFSError):
    """HDFS 权限错误 / HDFS permission error"""

    pass


class HDFSIOError(HDFSError):
    """HDFS I/O 错误 / HDFS I/O error"""

    pass


# ========== 连接池实现 / Connection Pool Implementation ==========


class HDFSConnectionPool:
    """HDFS 连接池 - 线程安全的连接管理

    管理 HDFS 连接的创建、复用和健康检查,避免频繁建立连接的开销。
    """

    def __init__(self, config: HDFSConfig):
        """初始化连接池

        Args:
            config: HDFS 配置对象
        """
        self.config = config
        self._pool: deque = deque(maxlen=config.max_connections)
        self._lock = Lock()
        self._created_count = 0

        logger.info(f"HDFSConnectionPool initialized: max_connections={config.max_connections}")

    def get_connection(self):
        """从连接池获取连接

        Returns:
            pyarrow.fs.HadoopFileSystem: HDFS 连接对象
        """
        with self._lock:
            # 尝试复用现有连接
            while self._pool:
                conn = self._pool.popleft()
                if self._is_connection_healthy(conn):
                    logger.debug("Reusing existing HDFS connection")
                    return conn
                logger.debug("Discarding unhealthy connection")

            # 创建新连接
            return self._create_new_connection()

    def return_connection(self, conn):
        """将连接返回到连接池

        Args:
            conn: HDFS 连接对象
        """
        if conn is None:
            return

        with self._lock:
            if len(self._pool) < self.config.max_connections:
                self._pool.append(conn)
                logger.debug(f"Connection returned to pool, size={len(self._pool)}")
            else:
                logger.debug("Pool full, discarding connection")

    def _create_new_connection(self):
        """创建新的 HDFS 连接

        Returns:
            pyarrow.fs.HadoopFileSystem: 新创建的 HDFS 连接

        Raises:
            HDFSConnectionError: 连接创建失败时抛出
        """
        try:
            import pyarrow.fs as pafs

            self._created_count += 1
            logger.info(
                f"Creating new HDFS connection #{self._created_count}: "
                f"{self.config.connection_string}"
            )

            # 创建 HDFS 连接
            fs = pafs.HadoopFileSystem(
                host=self.config.namenode_host,
                port=self.config.namenode_port,
                user=self.config.user,
            )

            return fs

        except ImportError as e:
            raise HDFSConnectionError(
                "pyarrow is not installed. Please install it: pip install pyarrow"
            ) from e
        except Exception as e:
            raise HDFSConnectionError(f"Failed to create HDFS connection: {e}") from e

    def _is_connection_healthy(self, conn) -> bool:
        """检查连接是否健康

        Args:
            conn: HDFS 连接对象

        Returns:
            bool: 连接是否健康
        """
        try:
            # 简单的健康检查: 尝试获取根目录信息
            conn.get_file_info(self.config.base_path)
            return True
        except Exception:
            return False

    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            while self._pool:
                self._pool.popleft()
                try:
                    # pyarrow FileSystem 通常不需要显式关闭
                    pass
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")

            logger.info("All HDFS connections closed")


# ========== 重试装饰器 / Retry Decorator ==========

# 使用统一的重试装饰器
# retry_with_config 从 self.config 读取 retry_attempts, retry_delay, retry_backoff
retry_on_failure = retry_with_config


# ========== HDFS 文件系统类 / HDFS FileSystem Class ==========


class HDFSFileSystem:
    """HDFS 文件系统操作类

    提供完整的 HDFS 文件操作接口,包括:
    - 文件读写、删除、列表
    - 目录创建、删除
    - 元数据查询
    - 文件复制、移动
    - 连接管理和自动重试
    """

    def __init__(self, config: HDFSConfig):
        """初始化 HDFS 文件系统

        Args:
            config: HDFS 配置对象
        """
        self.config = config
        self.config.validate()  # 验证配置

        self._pool = HDFSConnectionPool(config)
        self._fs = None

        logger.info(f"HDFSFileSystem initialized: {config.connection_string}")

    def connect(self):
        """建立 HDFS 连接"""
        if self._fs is None:
            self._fs = self._pool.get_connection()
            logger.info("HDFS connection established")

    def disconnect(self):
        """断开 HDFS 连接"""
        if self._fs is not None:
            self._pool.return_connection(self._fs)
            self._fs = None
            logger.info("HDFS connection disconnected")

    def is_connected(self) -> bool:
        """检查是否已连接

        Returns:
            bool: 是否已建立连接
        """
        return self._fs is not None

    def _ensure_connected(self):
        """确保已连接,否则抛出异常"""
        if not self.is_connected():
            raise HDFSConnectionError("Not connected to HDFS. Call connect() first.")

    def _normalize_path(self, path: str) -> str:
        """规范化路径 - 添加 base_path 前缀

        Args:
            path: 原始路径

        Returns:
            str: 规范化后的完整路径
        """
        if path.startswith("/"):
            return path
        return f"{self.config.base_path}/{path}".replace("//", "/")

    # ========== 文件操作 / File Operations ==========

    @retry_on_failure()
    def write_file(self, path: str, data: bytes, overwrite: bool = True):
        """写入文件到 HDFS

        Args:
            path: 文件路径 (相对于 base_path)
            data: 文件数据 (字节)
            overwrite: 是否覆盖已存在的文件

        Raises:
            HDFSIOError: 写入失败时抛出
        """
        self._ensure_connected()
        full_path = self._normalize_path(path)

        try:
            with self._fs.open_output_stream(full_path) as f:
                f.write(data)
            logger.info(f"File written: {full_path} ({len(data)} bytes)")
        except Exception as e:
            raise HDFSIOError(f"Failed to write file {full_path}: {e}") from e

    @retry_on_failure()
    def read_file(self, path: str) -> bytes:
        """从 HDFS 读取文件

        Args:
            path: 文件路径 (相对于 base_path)

        Returns:
            bytes: 文件数据

        Raises:
            HDFSFileNotFoundError: 文件不存在时抛出
            HDFSIOError: 读取失败时抛出
        """
        self._ensure_connected()
        full_path = self._normalize_path(path)

        try:
            with self._fs.open_input_stream(full_path) as f:
                data = f.read()
            logger.info(f"File read: {full_path} ({len(data)} bytes)")
            return data
        except FileNotFoundError as e:
            raise HDFSFileNotFoundError(f"File not found: {full_path}") from e
        except Exception as e:
            raise HDFSIOError(f"Failed to read file {full_path}: {e}") from e

    @retry_on_failure()
    def delete_file(self, path: str):
        """删除 HDFS 文件

        Args:
            path: 文件路径 (相对于 base_path)

        Raises:
            HDFSFileNotFoundError: 文件不存在时抛出
            HDFSIOError: 删除失败时抛出
        """
        self._ensure_connected()
        full_path = self._normalize_path(path)

        try:
            self._fs.delete_file(full_path)
            logger.info(f"File deleted: {full_path}")
        except FileNotFoundError as e:
            raise HDFSFileNotFoundError(f"File not found: {full_path}") from e
        except Exception as e:
            raise HDFSIOError(f"Failed to delete file {full_path}: {e}") from e

    @retry_on_failure()
    def exists(self, path: str) -> bool:
        """检查文件或目录是否存在

        Args:
            path: 文件/目录路径 (相对于 base_path)

        Returns:
            bool: 是否存在
        """
        self._ensure_connected()
        full_path = self._normalize_path(path)

        try:
            info = self._fs.get_file_info(full_path)
            return info.type != 0  # 0 = NotFound
        except Exception:
            return False

    @retry_on_failure()
    def list_files(self, path: str = "/", pattern: Optional[str] = None) -> list[str]:
        """列出目录下的文件

        Args:
            path: 目录路径 (相对于 base_path)
            pattern: 文件名模式 (如 "*.txt", 可选)

        Returns:
            list[str]: 文件路径列表

        Raises:
            HDFSFileNotFoundError: 目录不存在时抛出
            HDFSIOError: 列表失败时抛出
        """
        self._ensure_connected()
        full_path = self._normalize_path(path)

        try:
            selector = pafs.FileSelector(full_path, recursive=False)
            file_infos = self._fs.get_file_info(selector)

            files = [info.path for info in file_infos if info.is_file]

            # 应用模式过滤
            if pattern:
                from fnmatch import fnmatch

                files = [f for f in files if fnmatch(Path(f).name, pattern)]

            logger.info(f"Listed {len(files)} files in {full_path}")
            return files
        except FileNotFoundError as e:
            raise HDFSFileNotFoundError(f"Directory not found: {full_path}") from e
        except Exception as e:
            raise HDFSIOError(f"Failed to list files in {full_path}: {e}") from e

    # ========== 目录操作 / Directory Operations ==========

    @retry_on_failure()
    def mkdir(self, path: str, recursive: bool = True):
        """创建目录

        Args:
            path: 目录路径 (相对于 base_path)
            recursive: 是否递归创建父目录

        Raises:
            HDFSIOError: 创建失败时抛出
        """
        self._ensure_connected()
        full_path = self._normalize_path(path)

        try:
            self._fs.create_dir(full_path, recursive=recursive)
            logger.info(f"Directory created: {full_path}")
        except Exception as e:
            raise HDFSIOError(f"Failed to create directory {full_path}: {e}") from e

    @retry_on_failure()
    def rmdir(self, path: str):
        """删除目录

        Args:
            path: 目录路径 (相对于 base_path)

        Raises:
            HDFSFileNotFoundError: 目录不存在时抛出
            HDFSIOError: 删除失败时抛出
        """
        self._ensure_connected()
        full_path = self._normalize_path(path)

        try:
            self._fs.delete_dir(full_path)
            logger.info(f"Directory deleted: {full_path}")
        except FileNotFoundError as e:
            raise HDFSFileNotFoundError(f"Directory not found: {full_path}") from e
        except Exception as e:
            raise HDFSIOError(f"Failed to delete directory {full_path}: {e}") from e

    # ========== 元数据操作 / Metadata Operations ==========

    @retry_on_failure()
    def get_file_info(self, path: str) -> dict[str, Any]:
        """获取文件/目录信息

        Args:
            path: 文件/目录路径 (相对于 base_path)

        Returns:
            dict: 包含文件信息的字典 (type, size, mtime)

        Raises:
            HDFSFileNotFoundError: 文件不存在时抛出
        """
        self._ensure_connected()
        full_path = self._normalize_path(path)

        try:
            info = self._fs.get_file_info(full_path)
            return {
                "path": info.path,
                "type": "file" if info.is_file else "directory",
                "size": info.size,
                "mtime": info.mtime,
            }
        except FileNotFoundError as e:
            raise HDFSFileNotFoundError(f"Path not found: {full_path}") from e

    @retry_on_failure()
    def get_file_size(self, path: str) -> int:
        """获取文件大小

        Args:
            path: 文件路径 (相对于 base_path)

        Returns:
            int: 文件大小(字节)
        """
        info = self.get_file_info(path)
        return info["size"]

    @retry_on_failure()
    def get_modification_time(self, path: str) -> float:
        """获取文件修改时间

        Args:
            path: 文件路径 (相对于 base_path)

        Returns:
            float: 修改时间 (Unix 时间戳)
        """
        info = self.get_file_info(path)
        return info["mtime"]

    # ========== 高级操作 / Advanced Operations ==========

    @retry_on_failure()
    def copy(self, src: str, dst: str, overwrite: bool = False):
        """复制文件

        Args:
            src: 源文件路径 (相对于 base_path)
            dst: 目标文件路径 (相对于 base_path)
            overwrite: 是否覆盖目标文件

        Raises:
            HDFSFileNotFoundError: 源文件不存在时抛出
            HDFSIOError: 复制失败时抛出
        """
        self._ensure_connected()
        src_path = self._normalize_path(src)
        dst_path = self._normalize_path(dst)

        try:
            # pyarrow 不直接支持 copy,使用 read + write
            data = self.read_file(src)
            self.write_file(dst, data, overwrite=overwrite)
            logger.info(f"File copied: {src_path} -> {dst_path}")
        except Exception as e:
            raise HDFSIOError(f"Failed to copy file {src_path} to {dst_path}: {e}") from e

    @retry_on_failure()
    def move(self, src: str, dst: str, overwrite: bool = False):
        """移动文件

        Args:
            src: 源文件路径 (相对于 base_path)
            dst: 目标文件路径 (相对于 base_path)
            overwrite: 是否覆盖目标文件

        Raises:
            HDFSFileNotFoundError: 源文件不存在时抛出
            HDFSIOError: 移动失败时抛出
        """
        self._ensure_connected()
        src_path = self._normalize_path(src)
        dst_path = self._normalize_path(dst)

        try:
            self._fs.move(src_path, dst_path)
            logger.info(f"File moved: {src_path} -> {dst_path}")
        except Exception as e:
            raise HDFSIOError(f"Failed to move file {src_path} to {dst_path}: {e}") from e

    # ========== 上下文管理器 / Context Manager ==========

    def __enter__(self):
        """上下文管理器入口 - 自动连接 HDFS"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口 - 自动断开 HDFS 连接"""
        self.disconnect()
        return False


# 导入 pyarrow FileSelector (需要在模块级别)
try:
    import pyarrow.fs as pafs
except ImportError:
    pafs = None
