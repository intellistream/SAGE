# -*- coding: utf-8 -*-
"""
SAGE安装进度跟踪器
提供安装过程的进度显示和状态更新
"""

import time
import threading
from typing import Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class ProgressStep:
    """进度步骤数据类"""
    name: str
    description: str
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None


class ProgressTracker:
    """安装进度跟踪器"""
    
    def __init__(self, total_steps: int = 0, show_spinner: bool = True):
        """
        初始化进度跟踪器
        
        Args:
            total_steps: 总步骤数
            show_spinner: 是否显示加载动画
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.steps = []
        self.show_spinner = show_spinner
        self._spinner_thread = None
        self._spinner_stop = threading.Event()
        self._current_message = ""
        self._step_counter = 0  # 用于跟踪实际执行的步骤数
        
    def add_step(self, name: str, description: str) -> None:
        """
        添加进度步骤
        
        Args:
            name: 步骤名称
            description: 步骤描述
        """
        step = ProgressStep(name=name, description=description)
        self.steps.append(step)
        if self.total_steps == 0:
            self.total_steps = len(self.steps)
    
    def start_step(self, step_name: str, message: str = "") -> None:
        """
        开始执行步骤
        
        Args:
            step_name: 步骤名称
            message: 显示消息
        """
        step = self._find_step(step_name)
        if step:
            step.status = "running"
            step.start_time = time.time()
            self._step_counter += 1
            self.current_step = self._step_counter
        
        display_message = message or f"正在执行: {step_name}"
        self._update_display(display_message)
        
        if self.show_spinner:
            self._start_spinner(display_message)
    
    def complete_step(self, step_name: str, message: str = "") -> None:
        """
        完成步骤
        
        Args:
            step_name: 步骤名称
            message: 完成消息
        """
        self._stop_spinner()
        
        step = self._find_step(step_name)
        if step:
            step.status = "completed"
            step.end_time = time.time()
        
        success_message = message or f"✅ {step_name} 完成"
        print(f"\r{' ' * 80}\r{success_message}")
    
    def fail_step(self, step_name: str, error_message: str = "") -> None:
        """
        步骤失败
        
        Args:
            step_name: 步骤名称
            error_message: 错误消息
        """
        self._stop_spinner()
        
        step = self._find_step(step_name)
        if step:
            step.status = "failed"
            step.end_time = time.time()
            step.error_message = error_message
        
        fail_message = f"❌ {step_name} 失败"
        if error_message:
            fail_message += f": {error_message}"
        
        print(f"\r{' ' * 80}\r{fail_message}")
    
    def update_message(self, message: str) -> None:
        """
        更新当前显示消息
        
        Args:
            message: 新消息
        """
        self._current_message = message
        if not self.show_spinner:
            self._update_display(message)
    
    def _find_step(self, step_name: str) -> Optional[ProgressStep]:
        """查找步骤"""
        for step in self.steps:
            if step.name == step_name:
                return step
        return None
    
    def _update_display(self, message: str) -> None:
        """更新显示"""
        if self.total_steps > 0:
            progress = f"({self.current_step}/{self.total_steps}) "
        else:
            progress = ""
        
        display_text = f"{progress}{message}"
        print(f"\r{' ' * 80}\r{display_text}", end="", flush=True)
    
    def _start_spinner(self, message: str) -> None:
        """开始显示旋转动画"""
        if self._spinner_thread and self._spinner_thread.is_alive():
            return
        
        self._current_message = message
        self._spinner_stop.clear()
        self._spinner_thread = threading.Thread(target=self._spinner_worker)
        self._spinner_thread.daemon = True
        self._spinner_thread.start()
    
    def _stop_spinner(self) -> None:
        """停止旋转动画"""
        if self._spinner_thread and self._spinner_thread.is_alive():
            self._spinner_stop.set()
            self._spinner_thread.join(timeout=1.0)
    
    def _spinner_worker(self) -> None:
        """旋转动画工作线程"""
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        
        while not self._spinner_stop.is_set():
            if self.total_steps > 0:
                progress = f"({self.current_step}/{self.total_steps}) "
            else:
                progress = ""
            
            spinner = spinner_chars[i % len(spinner_chars)]
            display_text = f"{progress}{spinner} {self._current_message}"
            print(f"\r{' ' * 80}\r{display_text}", end="", flush=True)
            
            i += 1
            time.sleep(0.1)
    
    def get_summary(self) -> dict:
        """
        获取进度摘要
        
        Returns:
            进度摘要字典
        """
        completed = sum(1 for step in self.steps if step.status == "completed")
        failed = sum(1 for step in self.steps if step.status == "failed")
        running = sum(1 for step in self.steps if step.status == "running")
        pending = sum(1 for step in self.steps if step.status == "pending")
        
        total_time = 0
        for step in self.steps:
            if step.start_time and step.end_time:
                total_time += step.end_time - step.start_time
        
        return {
            "total_steps": len(self.steps),
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "total_time": total_time,
            "success_rate": completed / len(self.steps) if self.steps else 0
        }
    
    def print_summary(self) -> None:
        """打印进度摘要"""
        summary = self.get_summary()
        
        # 这里不再直接打印，而是通过UI组件处理
        # 主要用于返回摘要数据给UI组件
        pass
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self._stop_spinner()
        if exc_type:
            print(f"\r{' ' * 80}\r❌ 发生错误: {exc_val}")


class SimpleProgressBar:
    """简单的进度条"""
    
    def __init__(self, total: int, width: int = 50, prefix: str = "进度"):
        """
        初始化进度条
        
        Args:
            total: 总量
            width: 进度条宽度
            prefix: 前缀文本
        """
        self.total = total
        self.width = width
        self.prefix = prefix
        self.current = 0
    
    def update(self, count: int = 1, message: str = "") -> None:
        """
        更新进度
        
        Args:
            count: 增加的数量
            message: 附加消息
        """
        self.current += count
        self._render(message)
    
    def set_progress(self, current: int, message: str = "") -> None:
        """
        设置当前进度
        
        Args:
            current: 当前进度
            message: 附加消息
        """
        self.current = current
        self._render(message)
    
    def _render(self, message: str = "") -> None:
        """渲染进度条"""
        percent = min(100, int(100 * self.current / self.total))
        filled = int(self.width * self.current / self.total)
        bar = "█" * filled + "░" * (self.width - filled)
        
        display_text = f"{self.prefix}: |{bar}| {percent}% ({self.current}/{self.total})"
        if message:
            display_text += f" - {message}"
        
        print(f"\r{' ' * 100}\r{display_text}", end="", flush=True)
    
    def finish(self, message: str = "完成") -> None:
        """完成进度条"""
        self.current = self.total
        self._render(message)
        print()  # 换行
