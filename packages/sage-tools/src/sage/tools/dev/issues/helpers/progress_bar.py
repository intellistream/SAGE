#!/usr/bin/env python3
"""
from sage.common.utils.logging.custom_logger import CustomLogger
通用进度条组件
提供动态和固定两种模式的进度条显示
"""

import time


class ProgressBar:
    """简单的文本进度条类"""

    def __init__(self, total=None, description="处理中"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
        self.last_print_time = 0
        self.update_frequency = 0.2  # 每0.2秒最多更新一次

        if self.total:
            self.logger.info(f"🔄 {self.description}: 0/{self.total}")
        else:
            self.logger.info(f"🔄 {self.description}: 开始...")

    def update(self, current=None, message=""):
        """更新进度"""
        current_time = time.time()

        # 频率限制：至少间隔0.2秒才更新显示
        if current_time - self.last_print_time < self.update_frequency:
            if current is not None:
                self.current = current
            return

        if current is not None:
            self.current = current
        else:
            self.current += 1

        elapsed = current_time - self.start_time

        if self.total:
            # 固定模式：显示进度百分比
            percentage = min(100, (self.current / self.total) * 100)
            bar_length = 20
            filled_length = int(bar_length * self.current // self.total)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)

            self.logger.info(
                f"  📊 {self.description}: {self.current}/{self.total} [{bar}] {percentage:.1f}% ({elapsed:.1f}s)",
                end="",
            )
        else:
            # 动态模式：显示当前数量和时间
            spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[self.current % 10]
            self.logger.info(
                f"  📊 {self.description}: {self.current} 个 ({elapsed:.1f}s) {spinner}",
                end="",
            )

        if message:
            self.logger.info(f" {message}", end="")

        self.logger.info(f"\r", end="", flush=True)
        self.last_print_time = current_time

    def finish(self):
        """完成进度条"""
        elapsed = time.time() - self.start_time
        if self.total:
            self.logger.info(
                f"  ✅ {self.description}: {self.current}/{self.total} (100%) ({elapsed:.1f}s)"
            )
        else:
            self.logger.info(
                f"  ✅ {self.description}: 完成，共 {self.current} 个 ({elapsed:.1f}s)"
            )
