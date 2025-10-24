"""
测试日志管理配置

用于统一管理测试过程中的日志输出，避免控制台被大量日志信息污染。
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class LogManager:
    """测试日志管理器"""

    def __init__(self, project_root: str = None):
        from sage.common.config.output_paths import get_sage_paths

        if project_root is None:
            project_root = os.environ.get("SAGE_HOME", ".")

        self.project_root = Path(project_root)

        # Use unified SAGE path management system
        sage_paths = get_sage_paths(self.project_root)
        self.logs_dir = sage_paths.logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 创建今天的日志目录
        today = datetime.now().strftime("%Y%m%d")
        self.daily_log_dir = self.logs_dir / today
        self.daily_log_dir.mkdir(exist_ok=True)

        self._setup_loggers()

    def _setup_loggers(self):
        """设置不同类型的日志记录器"""

        # 测试执行日志
        self.test_logger = self._create_logger(
            "test_execution", self.daily_log_dir / "test_execution.log"
        )

        # Ray 相关日志
        self.ray_logger = self._create_logger("ray_tests", self.daily_log_dir / "ray_tests.log")

        # 性能日志
        self.perf_logger = self._create_logger(
            "performance", self.daily_log_dir / "performance.log"
        )

    def _create_logger(self, name: str, log_file: Path) -> logging.Logger:
        """创建一个日志记录器"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # 避免重复添加处理器
        if logger.handlers:
            return logger

        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 格式器
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        return logger

    def log_test_start(self, test_name: str):
        """记录测试开始"""
        self.test_logger.info(f"开始测试: {test_name}")

    def log_test_end(self, test_name: str, duration: float, passed: bool):
        """记录测试结束"""
        status = "通过" if passed else "失败"
        self.test_logger.info(f"测试结束: {test_name} - {status} ({duration:.2f}s)")

    def log_ray_operation(self, operation: str, details: str = ""):
        """记录 Ray 操作"""
        self.ray_logger.info(f"Ray操作: {operation} - {details}")

    def log_performance(self, metric: str, value: float, unit: str = ""):
        """记录性能指标"""
        self.perf_logger.info(f"性能指标: {metric} = {value} {unit}")

    def get_latest_logs(self, log_type: str = "test_execution", lines: int = 50) -> str:
        """获取最新的日志内容"""
        log_file = self.daily_log_dir / f"{log_type}.log"
        if not log_file.exists():
            return "日志文件不存在"

        try:
            with open(log_file, encoding="utf-8") as f:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
        except Exception as e:
            return f"读取日志失败: {e}"


# 全局实例
_log_manager = None


def get_test_log_manager(project_root: str = None) -> "LogManager":
    """获取测试日志管理器实例"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager(project_root)
    return _log_manager


def setup_quiet_ray_logging():
    """设置安静的 Ray 日志记录"""
    import logging

    # 降低 Ray 相关日志级别
    ray_loggers = [
        "ray",
        "ray.serve",
        "ray.tune",
        "ray.train",
        "ray.data",
        "ray.workflow",
    ]

    for logger_name in ray_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)

    # 设置 Ray 环境变量以减少日志输出
    os.environ["RAY_DISABLE_IMPORT_WARNING"] = "1"
    os.environ["RAY_DEDUP_LOGS"] = "0"
