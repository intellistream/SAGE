"""
Cache Miss Profiler

使用 perf 工具监测 cache miss 性能指标
针对 WSL 环境优化，提供简单的 API 用于启动/停止监测和获取统计数据

Usage:
    profiler = CacheProfiler()

    # 启动监测
    if profiler.start():
        # 执行需要监测的代码
        do_some_work()

        # 停止监测并获取结果
        stats = profiler.stop()
        print(f"Cache misses: {stats['cache_misses']}")
        print(f"Cache miss rate: {stats['cache_miss_rate']:.2%}")
"""

import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class CacheMissStats:
    """Cache miss 统计数据"""

    cache_misses: int = 0  # L1 + LLC cache misses
    cache_references: int = 0  # cache references
    cache_miss_rate: float = 0.0  # cache miss 率
    l1_dcache_loads: int = 0  # L1 数据缓存加载
    l1_dcache_load_misses: int = 0  # L1 数据缓存加载 miss
    llc_loads: int = 0  # LLC (Last Level Cache) 加载
    llc_load_misses: int = 0  # LLC 加载 miss
    instructions: int = 0  # 指令数
    cycles: int = 0  # CPU 周期数
    duration_seconds: float = 0.0  # 监测时长（秒）

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "cache_misses": self.cache_misses,
            "cache_references": self.cache_references,
            "cache_miss_rate": self.cache_miss_rate,
            "l1_dcache_loads": self.l1_dcache_loads,
            "l1_dcache_load_misses": self.l1_dcache_load_misses,
            "llc_loads": self.llc_loads,
            "llc_load_misses": self.llc_load_misses,
            "instructions": self.instructions,
            "cycles": self.cycles,
            "duration_seconds": self.duration_seconds,
        }


class CacheProfiler:
    """
    Cache Miss 监测器

    使用 Linux perf 工具监测 cache miss 事件
    支持两种模式：
    1. 进程模式：监测当前进程的 cache miss
    2. 系统模式：监测整个系统的 cache miss（需要 root 权限）
    """

    def __init__(self, pid: Optional[int] = None, enable_system_wide: bool = False):
        """
        Args:
            pid: 要监测的进程 ID，None 表示监测当前进程
            enable_system_wide: 是否启用系统级监测（需要 root 权限）
        """
        self.pid = pid if pid is not None else os.getpid()
        self.enable_system_wide = enable_system_wide
        self.perf_process: Optional[subprocess.Popen] = None
        self.output_file: Optional[str] = None
        self.start_time: Optional[float] = None
        self._available = None  # 缓存可用性检查结果
        self._perf_cmd = None  # 缓存找到的 perf 命令路径

    def is_available(self) -> bool:
        """
        检查 perf 工具是否可用

        Returns:
            True 如果 perf 可用，False 否则
        """
        if self._available is not None:
            return self._available

        try:
            # 尝试找到可用的 perf 命令
            perf_cmd = self._find_perf_command()
            if perf_cmd is None:
                print("  ⚠️  perf 工具未安装")
                self._available = False
                return False

            # 检查 perf 权限（尝试运行一个简单的命令）
            result = subprocess.run(
                [perf_cmd, "stat", "--", "echo", "test"], capture_output=True, timeout=5
            )
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="ignore")
                if "perf_event_paranoid" in stderr or "Permission denied" in stderr:
                    print("  ⚠️  perf 权限不足")
                    print("  提示: 尝试运行以下命令解决权限问题:")
                    print("    sudo sysctl -w kernel.perf_event_paranoid=-1")
                    print(
                        "    或在 WSL 中: echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid"
                    )
                self._available = False
                return False

            # 缓存找到的 perf 命令
            self._perf_cmd = perf_cmd
            self._available = True
            return True

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"  ⚠️  perf 工具检查失败: {e}")
            self._available = False
            return False

    def _find_perf_command(self) -> Optional[str]:
        """
        查找可用的 perf 命令

        在 WSL 中，/usr/bin/perf 可能因为内核版本不匹配而无法工作，
        但可以直接使用 /usr/lib/linux-tools/ 下安装的版本

        Returns:
            perf 命令路径，如果找不到返回 None
        """
        # 1. 尝试直接使用 perf 命令
        try:
            result = subprocess.run(["perf", "version"], capture_output=True, timeout=2)
            if result.returncode == 0:
                return "perf"
        except Exception:
            pass

        # 2. 在 WSL 中，尝试查找 /usr/lib/linux-tools/ 下的版本
        import glob

        perf_paths = glob.glob("/usr/lib/linux-tools/*/perf")
        if perf_paths:
            # 使用找到的第一个版本
            perf_cmd = perf_paths[0]
            try:
                result = subprocess.run([perf_cmd, "version"], capture_output=True, timeout=2)
                if result.returncode == 0:
                    return perf_cmd
            except Exception:
                pass

        return None

    def start(self) -> bool:
        """
        启动 cache miss 监测

        Returns:
            True 如果启动成功，False 否则
        """
        # 检查是否已经在运行
        if self.perf_process is not None:
            print("  ⚠️  Cache profiler 已经在运行")
            return False

        # 检查 perf 可用性
        if not self.is_available():
            return False

        # 获取 perf 命令路径
        perf_cmd = self._perf_cmd or self._find_perf_command()
        if perf_cmd is None:
            return False

        # 创建临时文件用于存储输出
        fd, self.output_file = tempfile.mkstemp(prefix="perf_cache_", suffix=".txt")
        os.close(fd)

        # 构建 perf 命令
        # 监测的事件:
        # - cache-misses: 总 cache miss
        # - cache-references: cache 访问次数
        # - L1-dcache-loads: L1 数据缓存加载
        # - L1-dcache-load-misses: L1 数据缓存加载 miss
        # - LLC-loads: Last Level Cache 加载
        # - LLC-load-misses: Last Level Cache 加载 miss
        # - instructions: 指令数
        # - cycles: CPU 周期数

        events = [
            "cache-misses",
            "cache-references",
            "L1-dcache-loads",
            "L1-dcache-load-misses",
            "LLC-loads",
            "LLC-load-misses",
            "instructions",
            "cycles",
        ]

        cmd = [perf_cmd, "stat", "-e", ",".join(events)]

        if self.enable_system_wide:
            # 系统级监测（需要 root 权限）
            cmd.extend(["-a"])
        else:
            # 进程级监测
            cmd.extend(["-p", str(self.pid)])

        # 不使用 -o 参数，而是直接捕获 stderr
        # 在 WSL2 中，-o 参数可能无法正常工作
        # cmd.extend(['-o', self.output_file])

        try:
            # 启动 perf 进程
            # 注意: perf stat 的输出在 stderr，我们需要捕获它
            self.perf_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # 捕获 stderr
            )
            self.start_time = time.time()

            # 等待 perf 启动
            time.sleep(0.1)

            # 检查进程是否还在运行
            if self.perf_process.poll() is not None:
                print(f"  ✗ perf 进程启动失败 (返回码: {self.perf_process.returncode})")
                self._cleanup()
                return False

            return True

        except Exception as e:
            print(f"  ✗ 启动 cache profiler 失败: {e}")
            self._cleanup()
            return False

    def stop(self) -> Optional[CacheMissStats]:
        """
        停止 cache miss 监测并获取统计数据

        Returns:
            CacheMissStats 对象，如果失败返回 None
        """
        if self.perf_process is None:
            print("  ⚠️  Cache profiler 未运行")
            return None

        duration = time.time() - self.start_time if self.start_time else 0

        try:
            # 发送 SIGINT 信号（相当于 Ctrl+C）来终止 perf
            # perf stat 只有在收到 SIGINT 时才会输出统计信息
            import signal

            self.perf_process.send_signal(signal.SIGINT)

            # 等待进程结束并获取输出
            try:
                stdout, stderr = self.perf_process.communicate(timeout=5)
                output = stderr.decode("utf-8", errors="ignore")
            except subprocess.TimeoutExpired:
                # 强制杀死
                self.perf_process.kill()
                stdout, stderr = self.perf_process.communicate()
                output = stderr.decode("utf-8", errors="ignore")

            # 解析输出
            if output:
                stats = self._parse_perf_output(output, duration)
            else:
                print("  ⚠️  perf 输出为空（这在WSL2中使用-p参数时是正常的）")
                print(f"  调试信息 - stdout: {len(stdout)} bytes, stderr: {len(stderr)} bytes")
                if stdout:
                    print(f"  stdout内容: {stdout[:200]}")
                if stderr:
                    print(f"  stderr内容: {stderr[:200]}")
                stats = None

            # 清理
            self._cleanup()

            return stats

        except Exception as e:
            print(f"  ✗ 停止 cache profiler 失败: {e}")
            self._cleanup()
            return None

    def _parse_perf_output(self, output: str, duration: float) -> CacheMissStats:
        """
        解析 perf stat 输出

        Args:
            output: perf stat 输出文本
            duration: 监测时长（秒）

        Returns:
            CacheMissStats 对象
        """
        stats = CacheMissStats(duration_seconds=duration)

        # 正则表达式匹配 perf 输出行
        # 示例行:
        #     1,234,567      cache-misses              #   12.34% of all cache refs
        #    12,345,678      cache-references

        patterns = {
            "cache_misses": r"([\d,]+)\s+cache-misses",
            "cache_references": r"([\d,]+)\s+cache-references",
            "l1_dcache_loads": r"([\d,]+)\s+L1-dcache-loads",
            "l1_dcache_load_misses": r"([\d,]+)\s+L1-dcache-load-misses",
            "llc_loads": r"([\d,]+)\s+LLC-loads",
            "llc_load_misses": r"([\d,]+)\s+LLC-load-misses",
            "instructions": r"([\d,]+)\s+instructions",
            "cycles": r"([\d,]+)\s+cycles",
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                # 移除逗号并转换为整数
                value_str = match.group(1).replace(",", "")
                try:
                    value = int(value_str)
                    setattr(stats, field, value)
                except ValueError:
                    pass

        # 计算 cache miss 率
        if stats.cache_references > 0:
            stats.cache_miss_rate = stats.cache_misses / stats.cache_references

        return stats

    def _cleanup(self):
        """清理资源"""
        self.perf_process = None
        self.start_time = None

        if self.output_file and os.path.exists(self.output_file):
            try:
                os.remove(self.output_file)
            except OSError:
                pass
        self.output_file = None

    def __enter__(self):
        """上下文管理器：进入"""
        if self.start():
            return self
        else:
            raise RuntimeError("Failed to start cache profiler")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：退出"""
        self.stop()
        return False


def check_perf_availability() -> tuple[bool, str]:
    """
    检查 perf 工具的可用性和配置

    Returns:
        (is_available, message): 可用性和提示信息
    """
    profiler = CacheProfiler()

    if profiler.is_available():
        return True, "perf 工具可用"
    else:
        message = (
            "perf 工具不可用。请按照以下步骤配置:\n"
            "1. 安装 perf (如果未安装):\n"
            "   Ubuntu/Debian: sudo apt-get install linux-tools-generic\n"
            "   RHEL/CentOS: sudo yum install perf\n"
            "2. 配置权限 (WSL 或 Linux):\n"
            "   sudo sysctl -w kernel.perf_event_paranoid=-1\n"
            "   或永久配置: echo 'kernel.perf_event_paranoid=-1' | sudo tee -a /etc/sysctl.conf\n"
            "3. 在 WSL2 中，确保内核版本 >= 5.10.16.3"
        )
        return False, message


if __name__ == "__main__":
    # 测试代码
    print("Testing Cache Profiler...")
    print("=" * 60)

    # 检查可用性
    is_available, message = check_perf_availability()
    print(message)
    print()

    if is_available:
        print("Running test...")
        profiler = CacheProfiler()

        if profiler.start():
            print("  ✓ Cache profiler started")

            # 模拟一些工作
            import numpy as np

            data = np.random.rand(10000, 128)
            result = np.dot(data, data.T)

            time.sleep(1)

            stats = profiler.stop()
            if stats:
                print("  ✓ Cache profiler stopped")
                print()
                print("Statistics:")
                print(f"  Duration: {stats.duration_seconds:.2f}s")
                print(f"  Cache misses: {stats.cache_misses:,}")
                print(f"  Cache references: {stats.cache_references:,}")
                print(f"  Cache miss rate: {stats.cache_miss_rate:.2%}")
                print(f"  L1 D-cache loads: {stats.l1_dcache_loads:,}")
                print(f"  L1 D-cache load misses: {stats.l1_dcache_load_misses:,}")
                print(f"  LLC loads: {stats.llc_loads:,}")
                print(f"  LLC load misses: {stats.llc_load_misses:,}")
                print(f"  Instructions: {stats.instructions:,}")
                print(f"  Cycles: {stats.cycles:,}")
        else:
            print("  ✗ Failed to start cache profiler")

    print("=" * 60)
