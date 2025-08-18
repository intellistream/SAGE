#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE Curses用户界面工具
基于curses的交互式界面，用于替代传统的命令行交互
"""

import curses
import time
import threading
import locale
import os
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class Message:
    """消息类"""
    content: str
    msg_type: str = "info"  # info, success, warning, error, progress
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class CursesUserInterface:
    """基于Curses的用户界面管理器"""
    
    def __init__(self, quiet_mode: bool = False):
        """
        初始化curses用户界面
        
        Args:
            quiet_mode: 静默模式（在curses模式下忽略，因为需要显示界面）
        """
        self.quiet_mode = False  # curses模式下不支持静默模式
        self.stdscr = None
        self.info_window = None      # 上方栏：信息和总结
        self.progress_window = None  # 中间栏：当前步骤
        self.input_window = None     # 下方栏：用户输入
        
        # 界面状态
        self.info_messages = []      # 上方栏消息
        self.progress_messages = []  # 中间栏消息  
        self.current_step_info = ""  # 当前步骤信息
        self.current_input = ""
        self.input_mode = False
        self.input_prompt = ""
        self.input_validator = None
        self.input_result = None
        self.input_event = None
        self.menu_options = []
        self.menu_default = None
        self.menu_result = None
        
        # 进度和动画状态
        self.spinner_chars = ["⠁", "⠃", "⠇", "⠧", "⠷", "⠿", "⠟", "⠏"]
        self.spinner_index = 0
        self.spinner_active = False
        self.current_operation = ""      # 当前操作描述
        self.overall_progress = {"current": 0, "total": 0}  # 整体进度
        self.current_step_desc = ""      # 当前步骤描述
        self.last_spinner_update = time.time()
        self.spinner_thread = None       # 动画线程
        self.spinner_running = False     # 动画运行状态
        
        # 滚动状态
        self.info_scroll_offset = 0
        self.max_scroll_offset = 0
        self.scroll_mode_enabled = False  # 只在特定情况下启用滚动
        
        # 颜色配置
        self.colors = {}
        
        # 界面尺寸
        self.height = 0
        self.width = 0
        
        # 设置UTF-8编码
        import os
        os.environ.setdefault('LANG', 'zh_CN.UTF-8')
        os.environ.setdefault('LC_ALL', 'zh_CN.UTF-8')
        
        # 启动curses
        self._init_curses()
    
    def _init_curses(self):
        """初始化curses"""
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        
        # 设置UTF-8编码支持
        import locale
        try:
            locale.setlocale(locale.LC_ALL, '')
        except:
            pass
        
        # 初始化颜色
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            
            # 定义颜色对
            curses.init_pair(1, curses.COLOR_RED, -1)      # error
            curses.init_pair(2, curses.COLOR_GREEN, -1)    # success
            curses.init_pair(3, curses.COLOR_YELLOW, -1)   # warning
            curses.init_pair(4, curses.COLOR_BLUE, -1)     # info
            curses.init_pair(5, curses.COLOR_CYAN, -1)     # progress
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # prompt
            curses.init_pair(7, curses.COLOR_BLUE, -1)     # welcome (蓝色)
            
            self.colors = {
                'error': curses.color_pair(1),
                'success': curses.color_pair(2),
                'warning': curses.color_pair(3),
                'info': curses.color_pair(4),
                'progress': curses.color_pair(5),
                'prompt': curses.color_pair(6),
                'welcome': curses.color_pair(7)
            }
        
        # 获取终端尺寸
        self.height, self.width = self.stdscr.getmaxyx()
        
        # 创建窗口布局
        self._create_windows()
        
        # 显示初始界面
        self._refresh_all()
        
        # 启动后台刷新线程，用于动画显示
        self.start_background_refresh()
    
    def _create_windows(self):
        """创建窗口布局"""
        # 确保最小尺寸
        if self.height < 15 or self.width < 60:
            raise RuntimeError("终端尺寸太小，至少需要 60x15")
        
        # 计算三栏窗口尺寸 - 给上方栏更多空间
        input_height = 5    # 下方输入栏紧凑高度（3行文字+边框）
        progress_height = 6 # 中间进度栏固定高度
        info_height = self.height - input_height - progress_height  # 上方信息栏使用剩余空间
        
        # 确保各窗口有足够空间
        if info_height < 4:
            info_height = 4
            progress_height = 4
            input_height = self.height - info_height - progress_height
        
        # 创建三个窗口：信息区、进度区、输入区
        self.info_window = curses.newwin(info_height, self.width, 0, 0)
        self.progress_window = curses.newwin(progress_height, self.width, info_height, 0)
        self.input_window = curses.newwin(input_height, self.width, info_height + progress_height, 0)
        
        # 设置滚动
        self.info_window.scrollok(True)
        self.info_window.idlok(True)
        self.info_window.leaveok(False)
        
        self.progress_window.scrollok(True)
        self.progress_window.idlok(True)
        self.progress_window.leaveok(False)
        
        # 绘制边框
        self.progress_window.box()
        self.input_window.box()
        
        # 清空所有窗口
        self.info_window.clear()
        self.progress_window.clear() 
        self.input_window.clear()
    
    def _refresh_all(self):
        """刷新所有窗口"""
        # 检查curses是否还有效
        if not self.stdscr:
            return
            
        # 使用锁防止多线程刷新冲突
        if not hasattr(self, '_refresh_lock'):
            self._refresh_lock = threading.Lock()
            
        with self._refresh_lock:
            try:
                self._refresh_info_window()
                self._refresh_progress_window()
                self._refresh_input_window()
                
                # 刷新顺序很重要，先刷新stdscr，再刷新子窗口
                self.stdscr.refresh()
                self.info_window.refresh()
                self.progress_window.refresh()
                self.input_window.refresh()
            except (curses.error, AttributeError):
                # curses已经被清理，忽略错误
                pass
    
    def refresh_if_active(self):
        """如果界面活跃且有动画，则刷新界面"""
        if self.stdscr and self.spinner_active:
            # 使用锁防止与主刷新冲突
            if not hasattr(self, '_refresh_lock'):
                self._refresh_lock = threading.Lock()
                
            # 尝试获取锁，如果获取不到就跳过这次刷新
            if self._refresh_lock.acquire(blocking=False):
                try:
                    self._refresh_progress_window()
                    self.progress_window.refresh()
                except (curses.error, AttributeError):
                    pass  # 忽略刷新错误
                finally:
                    self._refresh_lock.release()
    
    def start_background_refresh(self):
        """启动后台刷新线程，让动画连续显示"""
        if hasattr(self, '_refresh_thread') and self._refresh_thread.is_alive():
            return  # 已经在运行
            
        self._refresh_stop_event = threading.Event()
        self._refresh_thread = threading.Thread(target=self._background_refresh_loop, daemon=True)
        self._refresh_thread.start()
    
    def stop_background_refresh(self):
        """停止后台刷新线程"""
        if hasattr(self, '_refresh_stop_event'):
            self._refresh_stop_event.set()
        if hasattr(self, '_refresh_thread') and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=1.0)
    
    def _background_refresh_loop(self):
        """后台刷新循环"""
        while not self._refresh_stop_event.is_set():
            try:
                if self.spinner_active and self.stdscr:
                    # 更新动画索引
                    self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
                    # 使用非阻塞方式尝试刷新
                    self.refresh_if_active()
                time.sleep(0.3)  # 减慢刷新频率，避免过度刷新
            except Exception:
                # 忽略任何刷新错误，继续循环
                time.sleep(0.3)
    
    def _refresh_info_window(self):
        """刷新信息窗口（上方栏）- 支持滚动"""
        self.info_window.clear()
        
        # 添加标题栏，包含滚动提示
        scroll_hint = ""
        if len(self.info_messages) > 0:
            total_lines = sum(len(self._wrap_text(msg.content, self.width - 4)) for msg in self.info_messages)
            visible_lines = self.info_window.getmaxyx()[0] - 3
            
            if total_lines > visible_lines:
                scroll_hint = f" (↑↓滚动 {self.info_scroll_offset + 1}/{max(1, total_lines - visible_lines + 1)})"
        
        title = f"📊 安装信息和总结{scroll_hint}"
        try:
            self.info_window.addstr(0, 2, title, self.colors.get('info', 0) | curses.A_BOLD)
            self.info_window.addstr(1, 2, "─" * (self.width - 4), self.colors.get('info', 0))
        except curses.error:
            pass
        try:
            self.info_window.addstr(0, 2, title, self.colors.get('info', 0) | curses.A_BOLD)
            self.info_window.addstr(1, 2, "─" * (self.width - 4), self.colors.get('info', 0))
        except curses.error:
            pass
        
        # 准备所有要显示的行
        all_display_lines = []
        for msg in self.info_messages:
            color = self.colors.get(msg.msg_type, 0)
            
            # 添加图标
            icon = self._get_message_icon(msg.msg_type)
            if icon:
                content = f"{icon} {msg.content}"
            else:
                content = msg.content
            
            # 处理长消息换行
            lines = self._wrap_text(content, self.width - 4)
            for line in lines:
                all_display_lines.append((line, color))
        
        # 更新最大滚动偏移量
        max_visible_lines = self.info_window.getmaxyx()[0] - 3
        self.max_scroll_offset = max(0, len(all_display_lines) - max_visible_lines)
        
        # 确保滚动偏移量在有效范围内
        self.info_scroll_offset = max(0, min(self.info_scroll_offset, self.max_scroll_offset))
        
        # 根据滚动偏移量显示消息
        start_line = self.info_scroll_offset
        end_line = start_line + max_visible_lines
        
        display_lines = all_display_lines[start_line:end_line]
        
        line_count = 2  # 从第3行开始（0-based索引）
        for line, color in display_lines:
            if line_count >= max_visible_lines + 2:
                break
            try:
                # 确保不会超出窗口边界
                display_line = line[:self.width-4] if len(line) > self.width-4 else line
                self.info_window.addstr(line_count, 2, display_line, color)
                line_count += 1
            except curses.error:
                break  # 窗口满了
    
    def _refresh_progress_window(self):
        """刷新进度窗口（中间栏）- 四行格式，避免频繁重绘边框"""
        # 只清空内容区域，不清空边框
        max_height, max_width = self.progress_window.getmaxyx()
        
        # 清空内容区域（保留边框）
        for i in range(1, max_height - 1):
            try:
                self.progress_window.addstr(i, 1, " " * (max_width - 2))
            except curses.error:
                pass
        
        # 重新绘制边框（每次都重绘确保边框完整）
        try:
            self.progress_window.box()
        except curses.error:
            pass
        
        content_width = max_width - 4  # 减去左右边框和空隙
        
        try:
            # 第一行：保留原有的导航标题
            title = "🔄 当前执行步骤"
            self.progress_window.addstr(1, 2, title[:content_width], self.colors.get('progress', 0) | curses.A_BOLD)
            
            # 第二行：旋转动画 + 当前操作说明
            if self.current_operation:
                spinner = self.spinner_chars[self.spinner_index] if self.spinner_active else "⏸"
                operation_line = f"  {spinner} {self.current_operation}"
                if len(operation_line) > content_width:
                    operation_line = operation_line[:content_width-3] + "..."
                self.progress_window.addstr(2, 2, operation_line[:content_width], self.colors.get('progress', 0))
            
            # 第三行：整体任务进度条
            if self.overall_progress["total"] > 0:
                current = self.overall_progress["current"]
                total = self.overall_progress["total"]
                progress_percent = (current / total) * 100
                
                # 计算进度条长度（留出空间给百分比文字）
                progress_bar_width = max(20, content_width - 20)
                filled = int(progress_bar_width * current / total)
                
                # 创建进度条
                bar = "█" * filled + "░" * (progress_bar_width - filled)
                progress_line = f"  [{bar}] {progress_percent:.1f}% ({current}/{total})"
                
                if len(progress_line) > content_width:
                    # 如果太长，缩短进度条
                    progress_bar_width = max(10, content_width - 25)
                    filled = int(progress_bar_width * current / total)
                    bar = "█" * filled + "░" * (progress_bar_width - filled)
                    progress_line = f"  [{bar}] {progress_percent:.0f}%"
                
                self.progress_window.addstr(3, 2, progress_line[:content_width], self.colors.get('info', 0))
            
            # 第四行：具体步骤操作说明 - 统一格式
            if self.current_step_desc:
                step_line = f"  ▶ {self.current_step_desc}"
                if len(step_line) > content_width:
                    step_line = step_line[:content_width-3] + "..."
                self.progress_window.addstr(4, 2, step_line[:content_width], self.colors.get('info', 0))
                
        except curses.error:
            pass
    
    def _refresh_input_window(self):
        """刷新输入窗口（下方栏）- 紧凑布局，避免频繁重绘边框"""
        # 获取可用空间（去掉边框后只有3行）
        max_lines = self.input_window.getmaxyx()[0] - 2  # 去掉上下边框
        
        # 先清空内容区域，保留边框
        max_height, max_width = self.input_window.getmaxyx()
        for i in range(1, max_height - 1):
            try:
                self.input_window.addstr(i, 1, " " * (max_width - 2))
            except curses.error:
                pass
        
        # 重新绘制边框
        try:
            self.input_window.box()
        except curses.error:
            pass
        
        if self.input_mode:
            # 显示输入提示和当前输入（使用紧凑布局）
            max_width = self.width - 6
            
            # 处理提示文本（第1行）
            prompt_text = self.input_prompt
            if len(prompt_text) > max_width:
                prompt_text = prompt_text[:max_width-3] + "..."
            
            # 处理输入文本（第2行）
            input_display = f">>> {self.current_input}"
            if len(input_display) > max_width:
                input_display = input_display[:max_width-3] + "..."
            
            try:
                if max_lines >= 2:
                    self.input_window.addstr(1, 2, prompt_text[:max_width], self.colors.get('prompt', 0))
                    self.input_window.addstr(2, 2, input_display[:max_width])
                    
                    # 设置光标位置
                    cursor_x = min(6 + len(self.current_input), self.width - 3)
                    cursor_y = 2
                    self.input_window.move(cursor_y, cursor_x)
            except curses.error:
                pass
                
        elif self.menu_options:
            # 显示简化的菜单提示，不显示具体选项
            try:
                max_width = self.width - 6
                
                if max_lines >= 1:
                    self.input_window.addstr(1, 2, "请选择:", self.colors.get('prompt', 0))
                
                # 只显示选择范围，不显示具体选项内容
                if max_lines >= 2:
                    range_text = f"输入 1-{len(self.menu_options)}"
                    if self.menu_default:
                        range_text += f" (默认: {self.menu_default})"
                    
                    if len(range_text) <= max_width:
                        self.input_window.addstr(2, 2, range_text[:max_width], self.colors.get('info', 0))
                        
            except curses.error:
                pass
        else:
            # 显示简单状态信息和滚动提示
            try:
                if max_lines >= 1:
                    if self.scroll_mode_enabled:
                        status = "↑↓滚动查看 Home/End跳转 Enter继续"
                    else:
                        status = "等待操作... (Ctrl+C退出)"
                    
                    max_width = self.width - 6
                    if len(status) > max_width:
                        status = status[:max_width-3] + "..."
                    
                    self.input_window.addstr(1, 2, status[:max_width], self.colors.get('info', 0))
            except curses.error:
                pass
    
    def _get_message_icon(self, msg_type: str) -> str:
        """获取消息图标"""
        icons = {
            'info': 'ℹ️  ',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'progress': '🔄',
            'welcome': '',  # 欢迎框不显示图标
            'plain': ''     # 纯文本不显示图标
        }
        return icons.get(msg_type, 'ℹ️')
    
    def _wrap_text(self, text: str, width: int) -> List[str]:
        """文本换行处理"""
        if not text:
            return [""]
            
        # 移除可能的换行符
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        if len(text) <= width:
            return [text]
        
        lines = []
        current_pos = 0
        
        while current_pos < len(text):
            # 计算这一行能放多少字符
            end_pos = current_pos + width
            
            if end_pos >= len(text):
                # 最后一行
                lines.append(text[current_pos:])
                break
            
            # 尝试在空格处断行
            line_text = text[current_pos:end_pos]
            space_pos = line_text.rfind(' ')
            
            if space_pos > 0:
                # 在空格处断行
                lines.append(text[current_pos:current_pos + space_pos])
                current_pos += space_pos + 1  # 跳过空格
            else:
                # 强制断行
                lines.append(line_text)
                current_pos = end_pos
        
        return lines
    
    def _update_spinner(self):
        """更新旋转动画索引（仅在需要时调用）"""
        if self.spinner_active:
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
    
    def start_operation(self, operation_desc: str):
        """开始一个操作，启动动画"""
        self.current_operation = operation_desc
        self.spinner_active = True
        self.spinner_index = 0
        self.last_spinner_update = time.time()
        
        # 后台刷新线程应该已经在运行，不需要重复启动
        
        if self.stdscr:
            self._refresh_progress_window()
            self.progress_window.refresh()
    
    def stop_operation(self):
        """停止当前操作，停止动画"""
        self.spinner_active = False
        
        # 不要停止后台刷新线程，让它继续运行以备下次使用
        
        if self.stdscr:
            self._refresh_progress_window()
            self.progress_window.refresh()
    
    def update_overall_progress(self, current: int, total: int):
        """更新整体进度"""
        self.overall_progress = {"current": current, "total": total}
        if self.stdscr:
            self._refresh_progress_window()
            self.progress_window.refresh()
    
    def set_current_step_description(self, description: str):
        """设置当前步骤描述"""
        self.current_step_desc = description
        if self.stdscr:
            self._refresh_progress_window()
            self.progress_window.refresh()
    
    def update_progress_display(self, operation: str, current: int, total: int, step_desc: str = ""):
        """一次性更新所有进度信息"""
        self.current_operation = operation
        self.overall_progress = {"current": current, "total": total}
        if step_desc:
            self.current_step_desc = step_desc
        
        if not self.spinner_active:
            self.spinner_active = True
            self.last_spinner_update = time.time()
            
        if self.stdscr:
            self._refresh_progress_window()
            self.progress_window.refresh()
            
    def scroll_info_up(self):
        """向上滚动信息窗口"""
        if self.info_scroll_offset > 0:
            self.info_scroll_offset -= 1
            # 使用锁确保滚动时不与其他刷新冲突
            if hasattr(self, '_refresh_lock'):
                with self._refresh_lock:
                    self._refresh_info_window()
                    self.info_window.refresh()
            else:
                self._refresh_info_window()
                self.info_window.refresh()
    
    def scroll_info_down(self):
        """向下滚动信息窗口"""
        if self.info_scroll_offset < self.max_scroll_offset:
            self.info_scroll_offset += 1
            # 使用锁确保滚动时不与其他刷新冲突
            if hasattr(self, '_refresh_lock'):
                with self._refresh_lock:
                    self._refresh_info_window()
                    self.info_window.refresh()
            else:
                self._refresh_info_window()
                self.info_window.refresh()
    
    def scroll_to_bottom(self):
        """滚动到信息窗口底部"""
        self.info_scroll_offset = self.max_scroll_offset
        if hasattr(self, '_refresh_lock'):
            with self._refresh_lock:
                self._refresh_info_window()
                self.info_window.refresh()
        else:
            self._refresh_info_window()
            self.info_window.refresh()
    
    def scroll_to_top(self):
        """滚动到信息窗口顶部"""
        self.info_scroll_offset = 0
        if hasattr(self, '_refresh_lock'):
            with self._refresh_lock:
                self._refresh_info_window()
                self.info_window.refresh()
        else:
            self._refresh_info_window()
            self.info_window.refresh()
    
    def _add_message(self, content: str, msg_type: str = "info", target: str = "info"):
        """
        添加消息
        
        Args:
            content: 消息内容
            msg_type: 消息类型
            target: 目标窗口 ("info" 或 "progress")
        """
        msg = Message(content, msg_type)
        
        if target == "progress":
            self.progress_messages.append(msg)
            # 限制进度消息数量
            if len(self.progress_messages) > 100:
                self.progress_messages = self.progress_messages[-50:]
        else:
            self.info_messages.append(msg)
            # 限制信息消息数量
            if len(self.info_messages) > 500:
                self.info_messages = self.info_messages[-250:]
        
        # 只在curses有效时刷新
        if self.stdscr:
            # 如果添加新消息，自动滚动到底部（除非用户正在手动滚动）
            if target == "info" and self.info_scroll_offset == self.max_scroll_offset:
                # 用户当前在底部，保持在底部
                self._refresh_all()
                self.scroll_to_bottom()
            else:
                self._refresh_all()
    
    def _get_user_input(self, prompt: str, validator: Optional[Callable] = None) -> str:
        """获取用户输入"""
        self.input_mode = True
        self.input_prompt = prompt if prompt else "请按 Enter 键继续..."
        self.current_input = ""
        self.input_validator = validator
        self.input_result = None
        self.input_event = threading.Event()
        
        self._refresh_all()
        
        # 输入循环
        while True:
            try:
                # 检查input_window是否还有效
                if self.input_window is None:
                    raise KeyboardInterrupt("输入窗口已关闭")
                ch = self.input_window.getch()
                
                if ch == ord('\n') or ch == curses.KEY_ENTER or ch == 10:
                    # 回车确认
                    if self.input_validator:
                        if self.input_validator(self.current_input):
                            self.input_result = self.current_input
                            break
                        else:
                            self._add_message("输入无效，请重试", "error", "progress")
                            self.current_input = ""
                    else:
                        self.input_result = self.current_input
                        break
                
                elif ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8:
                    # 退格
                    if self.current_input:
                        self.current_input = self.current_input[:-1]
                
                elif ch == curses.KEY_UP:
                    # 只在滚动模式启用时才处理向上滚动
                    if self.scroll_mode_enabled:
                        self.scroll_info_up()
                        continue  # 不更新输入窗口
                
                elif ch == curses.KEY_DOWN:
                    # 只在滚动模式启用时才处理向下滚动
                    if self.scroll_mode_enabled:
                        self.scroll_info_down()
                        continue  # 不更新输入窗口
                
                elif ch == 27:  # ESC序列开始
                    # 处理转义序列（如鼠标滚轮）
                    if self.scroll_mode_enabled:
                        try:
                            # 检查input_window是否还有效
                            if self.input_window is None:
                                break
                            # 设置nodelay模式来读取转义序列
                            self.input_window.nodelay(True)
                            seq = []
                            
                            # 读取转义序列的剩余部分
                            for _ in range(10):  # 最多读取10个字符
                                if self.input_window is None:
                                    break
                                next_ch = self.input_window.getch()
                                if next_ch == -1:  # 没有更多字符
                                    break
                                seq.append(next_ch)
                            
                            # 恢复阻塞模式
                            if self.input_window is not None:
                                self.input_window.nodelay(False)
                            
                            # 检查是否为方向键的转义序列
                            if len(seq) >= 2 and seq[0] == ord('['):
                                if seq[1] == ord('A'):  # 上箭头 \e[A
                                    self.scroll_info_up()
                                    continue
                                elif seq[1] == ord('B'):  # 下箭头 \e[B
                                    self.scroll_info_down()
                                    continue
                                elif seq[1] == ord('H'):  # Home键 \e[H
                                    self.scroll_to_top()
                                    continue
                                elif seq[1] == ord('F'):  # End键 \e[F
                                    self.scroll_to_bottom()
                                    continue
                        except:
                            # 如果处理转义序列出错，恢复阻塞模式并继续
                            self.input_window.nodelay(False)
                    continue
                
                elif ch == curses.KEY_HOME:
                    # 只在滚动模式启用时才处理滚动到顶部
                    if self.scroll_mode_enabled:
                        self.scroll_to_top()
                        continue
                
                elif ch == curses.KEY_END:
                    # 只在滚动模式启用时才处理滚动到底部
                    if self.scroll_mode_enabled:
                        self.scroll_to_bottom()
                        continue
                
                elif ch == 3:  # Ctrl+C
                    raise KeyboardInterrupt()
                
                elif 32 <= ch <= 126:  # 可打印字符
                    self.current_input += chr(ch)
                
                self._refresh_input_window()
                self.input_window.refresh()
                
            except KeyboardInterrupt:
                self.cleanup()
                raise
        
        self.input_mode = False
        self.menu_options = []
        self._refresh_all()
        
        return self.input_result
    
    def _get_menu_choice(self, options: List[str], default: Optional[int] = None) -> int:
        """获取菜单选择"""
        self.menu_options = options
        self.menu_default = default
        self.menu_result = None
        
        self._refresh_all()
        
        while True:
            try:
                # 检查input_window是否还有效
                if self.input_window is None:
                    raise KeyboardInterrupt("输入窗口已关闭")
                ch = self.input_window.getch()
                
                if ch == 3:  # Ctrl+C
                    raise KeyboardInterrupt()
                
                elif ch == ord('\n') or ch == curses.KEY_ENTER or ch == 10:
                    # 如果没有输入且有默认值，使用默认值
                    if self.menu_default is not None:
                        self.menu_result = self.menu_default - 1
                        break
                
                elif ch == curses.KEY_UP:
                    # 只在滚动模式启用时才处理向上滚动
                    if self.scroll_mode_enabled:
                        self.scroll_info_up()
                        continue
                
                elif ch == curses.KEY_DOWN:
                    # 只在滚动模式启用时才处理向下滚动
                    if self.scroll_mode_enabled:
                        self.scroll_info_down()
                        continue
                
                elif ch == 27:  # ESC序列开始
                    # 处理转义序列（如鼠标滚轮）
                    if self.scroll_mode_enabled:
                        try:
                            # 设置nodelay模式来读取转义序列
                            self.input_window.nodelay(True)
                            seq = []
                            
                            # 读取转义序列的剩余部分
                            for _ in range(10):  # 最多读取10个字符
                                if self.input_window is None:
                                    break
                                next_ch = self.input_window.getch()
                                if next_ch == -1:  # 没有更多字符
                                    break
                                seq.append(next_ch)
                            
                            # 恢复阻塞模式
                            if self.input_window is not None:
                                self.input_window.nodelay(False)
                            
                            # 检查是否为方向键的转义序列
                            if len(seq) >= 2 and seq[0] == ord('['):
                                if seq[1] == ord('A'):  # 上箭头 \e[A
                                    self.scroll_info_up()
                                    continue
                                elif seq[1] == ord('B'):  # 下箭头 \e[B
                                    self.scroll_info_down()
                                    continue
                                elif seq[1] == ord('H'):  # Home键 \e[H
                                    self.scroll_to_top()
                                    continue
                                elif seq[1] == ord('F'):  # End键 \e[F
                                    self.scroll_to_bottom()
                                    continue
                        except:
                            # 如果处理转义序列出错，恢复阻塞模式并继续
                            self.input_window.nodelay(False)
                    continue
                
                elif ch == curses.KEY_HOME:
                    # 只在滚动模式启用时才处理滚动到顶部
                    if self.scroll_mode_enabled:
                        self.scroll_to_top()
                        continue
                
                elif ch == curses.KEY_END:
                    # 只在滚动模式启用时才处理滚动到底部
                    if self.scroll_mode_enabled:
                        self.scroll_to_bottom()
                        continue
                
                elif ord('1') <= ch <= ord('9'):
                    choice = ch - ord('0')
                    if 1 <= choice <= len(options):
                        self.menu_result = choice - 1
                        break
                    else:
                        self._add_message(f"请输入1-{len(options)}之间的数字", "error", "progress")
                
            except KeyboardInterrupt:
                self.cleanup()
                raise
        
        self.menu_options = []
        self._refresh_all()
        
        return self.menu_result
    
    def cleanup(self):
        """清理curses"""
        # 停止后台刷新线程
        self.stop_background_refresh()
        
        if self.stdscr:
            try:
                curses.nocbreak()
                self.stdscr.keypad(False)
                curses.echo()
                curses.endwin()
            except:
                pass  # 忽略清理时的错误
            finally:
                self.stdscr = None
                self.info_window = None
                self.progress_window = None
                self.input_window = None
    
    def is_active(self) -> bool:
        """检查界面是否仍然活跃"""
        return self.stdscr is not None and self.input_window is not None
    
    # 原始UserInterface接口的实现
    
    def show_welcome(self, title: str = "SAGE安装向导") -> None:
        """显示欢迎信息"""
        welcome_msg = f"🚀 {title}"
        # 计算合适的框宽度
        content_width = len(welcome_msg)
        box_width = min(content_width + 6, self.width - 4)  # 内容宽度加上边距
        
        # 创建边框
        border = "═" * (box_width + 3)
        
        # 计算居中位置
        center_offset = max(0, (self.width - box_width) // 2)
        
        # 创建居中的欢迎框，使用welcome类型不显示图标
        self._add_message("", "welcome")
        self._add_message(" " * center_offset + f"╔{border}╗", "welcome")
        self._add_message(" " * center_offset + f"║{welcome_msg.center(box_width-2)}║", "welcome")
        self._add_message(" " * center_offset + f"╚{border}╝", "welcome")
        self._add_message("", "welcome")
    
    def show_section(self, title: str, description: str = "") -> None:
        """显示章节标题"""
        section_msg = f"📋 {title}"
        if description:
            section_msg += f" - {description}"
        
        # 确保不超出屏幕宽度
        max_width = self.width - 10
        if len(section_msg) > max_width:
            section_msg = section_msg[:max_width-3] + "..."
        
        self._add_message("", "plain")
        self._add_message(section_msg, "plain")
        
        # 创建分隔线，长度适应内容但不超出屏幕
        separator_length = min(len(section_msg), max_width)
        self._add_message("─" * separator_length, "plain")
    
    def show_progress_section(self, title: str, current_step: int, total_steps: int) -> None:
        """显示进度章节（使用新的四行格式）"""
        # 更新整体进度和操作描述
        self.update_progress_display(
            operation=title,
            current=current_step,
            total=total_steps,
            step_desc=f"正在执行第 {current_step} 步（共 {total_steps} 步）：{title}"
        )
    
    def show_info(self, message: str, icon: str = "ℹ️") -> None:
        """显示信息（在上方栏）"""
        if self.stdscr is None:
            print(f"ℹ️  {message}")
            return
        self._add_message(message, "info", "info")
    
    def show_success(self, message: str) -> None:
        """显示成功消息（在上方栏）"""
        if self.stdscr is None:
            print(f"✅ {message}")
            return
        self._add_message(message, "success", "info")
    
    def show_warning(self, message: str) -> None:
        """显示警告（在上方栏）"""
        if self.stdscr is None:
            print(f"⚠️  {message}")
            return
        self._add_message(message, "warning", "info")
    
    def show_error(self, message: str) -> None:
        """显示错误（在上方栏）"""
        if self.stdscr is None:
            print(f"❌ {message}")
            return
        self._add_message(message, "error", "info")
    
    def show_progress_info(self, message: str) -> None:
        """显示进度相关信息（在中间栏）"""
        self._add_message(message, "info", "progress")
    
    def show_key_value(self, data: Dict[str, Any], title: Optional[str] = None) -> None:
        """显示键值对信息"""
        if title:
            self._add_message(f"📋 {title}", "plain")
        
        max_key_length = max(len(str(key)) for key in data.keys()) if data else 0
        
        for key, value in data.items():
            self._add_message(f"  {str(key):<{max_key_length}} | {value}", "plain")
    
    def show_progress_summary(self, summary: Dict[str, Any]) -> None:
        """显示进度摘要"""
        self._add_message("", "plain")
        self._add_message("📊 安装总结", "plain")
        self._add_message("=" * 30, "plain")
        
        stats = [
            f"总步骤数: {summary.get('total_steps', 0)}",
            f"✅ 成功: {summary.get('completed', 0)}",
            f"❌ 失败: {summary.get('failed', 0)}",
            f"⏱️ 总用时: {summary.get('total_time', 0):.1f}秒",
            f"📈 成功率: {summary.get('success_rate', 0):.1%}"
        ]
        
        for stat in stats:
            self._add_message(stat, "plain")
        
        if summary.get('failed', 0) == 0:
            self._add_message("🎉 安装成功完成！", "success")
        else:
            self._add_message(f"安装过程中有 {summary.get('failed', 0)} 个步骤失败", "warning")
    
    def show_menu(self, 
                  title: str, 
                  options: List[str], 
                  default: Optional[int] = None,
                  allow_custom: bool = False) -> int:
        """显示菜单并获取用户选择"""
        
        # 检查界面是否仍然活跃
        if not self.is_active():
            # 使用标准输入作为后备
            print(f"\n{title}")
            for i, option in enumerate(options, 1):
                marker = "👉" if default and i == default else "  "
                print(f"{marker} {i}. {option}")
            
            if allow_custom:
                print("   0. 自定义输入")
            
            while True:
                try:
                    choice = input("请选择 (按Enter使用默认选项): ").strip()
                    if not choice and default:
                        return default - 1
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(options):
                        return choice_num - 1
                    elif allow_custom and choice_num == 0:
                        return -1  # 自定义输入
                    else:
                        print(f"请输入1-{len(options)}之间的数字")
                except ValueError:
                    print("请输入有效的数字")
                except KeyboardInterrupt:
                    raise

        self._add_message(title, "plain")
        
        for i, option in enumerate(options, 1):
            marker = "👉" if default and i == default else "  "
            self._add_message(f"{marker} {i}. {option}", "plain")
        
        if allow_custom:
            self._add_message("   0. 自定义输入", "plain")
        
        return self._get_menu_choice(options, default)
    
    def get_input(self, 
                  prompt: str, 
                  default: Optional[str] = None,
                  validator: Optional[Callable[[str], bool]] = None,
                  error_message: str = "输入无效，请重试") -> str:
        """获取用户输入"""
        full_prompt = prompt
        if default:
            full_prompt += f" (默认: {default})"
        
        # 检查界面是否仍然活跃
        if not self.is_active():
            # 使用标准输入作为后备
            while True:
                try:
                    user_input = input(f"{full_prompt}: ").strip()
                    if not user_input and default is not None:
                        return default
                    if validator and not validator(user_input):
                        print(error_message)
                        continue
                    return user_input
                except KeyboardInterrupt:
                    raise
        
        def input_validator(user_input):
            # 使用默认值
            if not user_input and default is not None:
                return True
            
            # 验证输入
            if validator and not validator(user_input):
                return False
            
            return True
        
        result = self._get_user_input(full_prompt, input_validator)
        
        # 返回默认值或用户输入
        if not result and default is not None:
            return default
        
        return result
    
    def get_yes_no(self, 
                   prompt: str, 
                   default: Optional[bool] = None) -> bool:
        """获取是/否选择"""
        suffix = ""
        if default is True:
            suffix = " [Y/n]"
        elif default is False:
            suffix = " [y/N]"
        else:
            suffix = " [y/n]"
        
        full_prompt = f"{prompt}{suffix}"
        
        # 检查界面是否仍然活跃
        if not self.is_active():
            # 使用标准输入作为后备
            while True:
                try:
                    user_input = input(f"{full_prompt}: ").strip().lower()
                    if not user_input and default is not None:
                        return default
                    if user_input in ['y', 'yes', '是', '确定']:
                        return True
                    elif user_input in ['n', 'no', '否', '取消']:
                        return False
                    else:
                        print("请输入 y/yes/是/确定 或 n/no/否/取消")
                except KeyboardInterrupt:
                    raise
        
        def validator(user_input):
            user_input = user_input.strip().lower()
            
            if not user_input and default is not None:
                return True
            
            return user_input in ['y', 'yes', '是', '确定', 'n', 'no', '否', '取消']
        
        while True:
            result = self._get_user_input(full_prompt, validator)
            result = result.strip().lower()
            
            if not result and default is not None:
                return default
            
            if result in ['y', 'yes', '是', '确定']:
                return True
            elif result in ['n', 'no', '否', '取消']:
                return False
    
    # 简化的方法（某些功能在curses中不易实现，暂时简化）
    def clear_screen(self) -> None:
        """清屏 - 在curses中通过清空消息实现"""
        self.info_messages = []
        self.progress_messages = []
        self.current_step_info = ""
        self.info_scroll_offset = 0  # 重置滚动状态
        self.max_scroll_offset = 0
        self._refresh_all()
    
    def pause(self, message: str = "按Enter键继续...") -> None:
        """暂停等待用户确认，启用滚动功能审阅信息"""
        # 检查界面是否已清理
        if self.input_window is None or self.stdscr is None:
            print(f"\n{message}")
            try:
                input()  # 使用标准输入作为后备
            except KeyboardInterrupt:
                raise
            return
            
        # 添加明显的分隔线和提示
        self._add_message("", "plain", "info")
        self._add_message("─" * min(50, self.width - 10), "plain", "info")
        self._add_message(f"🔔 {message}", "prompt", "info")
        self._add_message("📜 您可以使用↑↓键滚动查看历史信息", "info", "info")
        self._add_message("🏠 Home键回到顶部 | End键跳到底部", "info", "info")
        self._add_message("─" * min(50, self.width - 10), "plain", "info")
        
        # 启用滚动模式
        self.scroll_mode_enabled = True
        
        try:
            # 等待用户按Enter
            self._get_user_input("", lambda x: True)
        except KeyboardInterrupt:
            # 如果被中断，重新抛出异常
            raise
        finally:
            # 关闭滚动模式
            self.scroll_mode_enabled = False
    
    def update_step_progress(self, step_name: str, message: str, step_type: str = "info"):
        """更新步骤进度信息，提供详细的阶段性说明"""
        # 根据步骤名称和类型提供详细说明
        detailed_desc = self._get_detailed_step_description(step_name, message, step_type)
        
        if step_type == "start":
            self.start_operation(f"{step_name}")
            self.set_current_step_description(detailed_desc)
            # 不再添加进度消息，只使用第四行显示
        elif step_type == "complete":
            self.stop_operation()
            self.set_current_step_description(f"✅ 已完成: {step_name}")
            # 不再添加进度消息，只使用第四行显示
        elif step_type == "error":
            self.stop_operation()
            self.set_current_step_description(f"❌ 失败: {step_name}")
            # 不再添加进度消息，只使用第四行显示
        else:
            # 对于普通信息，也提供详细说明
            self.set_current_step_description(detailed_desc)
            # 不再添加进度消息，只使用第四行显示
    
    def _get_detailed_step_description(self, step_name: str, message: str, step_type: str) -> str:
        """根据步骤名称和消息生成详细的步骤说明"""
        
        # 首先尝试从message中提取具体信息
        if step_type == "start" and message:
            # 提取具体的操作对象
            if "requirements" in message.lower():
                if "requirements-" in message:
                    req_file = message.split("requirements-")[-1].split(".")[0]
                    return f"加载依赖清单: {req_file} 配置文件"
                return "解析和安装项目依赖清单"
            elif "conda" in message.lower() and "包" in message:
                return "配置系统级软件包和环境依赖"
            elif "pip" in message.lower() or "python" in message.lower():
                return "安装Python生态系统组件和库"
            elif "sage" in message.lower():
                return "编译和安装SAGE核心框架组件"
            elif "submodule" in message.lower() or "子模块" in message.lower():
                return "同步和更新项目Git子模块依赖"
            elif "验证" in message or "validation" in message.lower():
                return "运行完整性检查和功能验证测试"
            elif "环境" in message:
                env_name = self._extract_env_name_from_message(message)
                if env_name:
                    return f"配置虚拟环境: {env_name}"
                return "初始化和配置Python虚拟环境"
            elif "依赖" in message or "dependency" in message.lower():
                return "扫描系统依赖项和必需软件组件"
        
        # 定义常见步骤的详细说明模板
        step_descriptions = {
            "dependency_check": {
                "start": "扫描系统依赖项和必需软件组件",
                "complete": "✅ 系统环境检查通过，满足安装要求",
                "error": "❌ 系统依赖检查失败，缺少必需组件"
            },
            "create_env": {
                "start": "初始化Python虚拟环境和包管理器",
                "complete": "✅ 虚拟环境创建完成，Python环境就绪",
                "error": "❌ 环境创建失败，请检查Conda配置"
            },
            "delete_env": {
                "start": "清理现有环境和冲突配置",
                "complete": "✅ 旧环境清理完成",
                "error": "❌ 环境清理失败，可能被其他进程占用"
            },
            "requirements_install": {
                "start": "解析和安装项目依赖清单",
                "complete": "✅ 依赖清单安装完成，所需组件已就绪",
                "error": "❌ 依赖安装过程出现错误，请检查网络"
            },
            "conda_packages": {
                "start": "配置系统级软件包和环境依赖",
                "complete": "✅ 系统级组件安装完成",
                "error": "❌ 系统包安装失败，请检查Conda源"
            },
            "pip_packages": {
                "start": "安装Python生态系统组件和库",
                "complete": "✅ Python依赖库安装完成",
                "error": "❌ 部分Python包安装失败"
            },
            "sage_packages": {
                "start": "编译和安装SAGE核心框架组件",
                "complete": "✅ SAGE核心模块安装完成", 
                "error": "❌ SAGE模块安装失败，请检查源代码"
            },
            "submodules": {
                "start": "同步和更新项目Git子模块依赖",
                "complete": "✅ Git子模块同步完成",
                "error": "❌ 子模块操作失败，请检查网络连接"
            },
            "validation": {
                "start": "运行完整性检查和功能验证测试",
                "complete": "✅ 安装验证通过，系统功能正常",
                "error": "❌ 验证发现问题，部分功能可能异常"
            }
        }
        
        # 查找匹配的步骤说明
        if step_name in step_descriptions:
            desc_map = step_descriptions[step_name]
            if step_type in desc_map:
                return desc_map[step_type]
        
        # 如果没有找到预定义说明，生成通用说明
        if step_type == "start":
            return f"执行操作: {message}"
        elif step_type == "complete":
            return f"✅ 操作完成: {step_name}"
        elif step_type == "error":
            return f"❌ 操作失败: {step_name}"
        else:
            return message
    
    def _extract_env_name_from_message(self, message: str) -> str:
        """从消息中提取环境名称"""
        import re
        # 匹配常见的环境名称模式
        patterns = [
            r"环境[：:]?\s*([a-zA-Z0-9_-]+)",
            r"environment[：:]?\s*([a-zA-Z0-9_-]+)",
            r"env[：:]?\s*([a-zA-Z0-9_-]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1)
        return ""
    
    def update_current_detail(self, detail: str):
        """更新第四行的具体操作详情"""
        formatted_detail = f"正在处理: {detail}"
        self.set_current_step_description(formatted_detail)
    
    def update_package_install_detail(self, package_name: str, action: str = "安装"):
        """更新包安装的具体详情"""
        detail = f"{action}软件包: {package_name}"
        self.set_current_step_description(detail)
    
    def update_file_operation_detail(self, filename: str, action: str = "处理"):
        """更新文件操作的具体详情"""
        detail = f"{action}文件: {filename}"
        self.set_current_step_description(detail)
    
    def update_validation_detail(self, component: str):
        """更新验证过程的具体详情"""
        detail = f"验证组件: {component}"
        self.set_current_step_description(detail)


def create_simple_menu(title: str, options: List[str]) -> int:
    """
    创建简单菜单的便捷函数
    """
    ui = CursesUserInterface()
    try:
        return ui.show_menu(title, options)
    finally:
        ui.cleanup()


def get_user_confirmation(message: str, default: bool = False) -> bool:
    """
    获取用户确认的便捷函数
    """
    ui = CursesUserInterface()
    try:
        return ui.get_yes_no(message, default)
    finally:
        ui.cleanup()
