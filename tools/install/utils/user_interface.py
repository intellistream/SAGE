#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE用户界面工具
提供交互式菜单、用户输入处理和信息显示功能
"""

import os
import sys
import shutil
from typing import List, Dict, Optional, Callable, Any


class UserInterface:
    """用户界面管理器"""
    
    def __init__(self, quiet_mode: bool = False):
        """
        初始化用户界面
        
        Args:
            quiet_mode: 静默模式，减少交互
        """
        self.quiet_mode = quiet_mode
        self.terminal_width = self._get_terminal_width()
        
        # 确保UTF-8编码输出
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            except:
                pass
    
    def set_current_step(self, step_info: str):
        """设置当前步骤信息（兼容curses接口）"""
        if not self.quiet_mode:
            print(f"🔄 {step_info}")
    
    def show_progress_info(self, message: str):
        """显示进度信息（兼容curses接口）"""
        if not self.quiet_mode:
            print(f"  📋 {message}")
    
    def update_step_progress(self, step_name: str, message: str, step_type: str = "info"):
        """更新步骤进度信息（兼容curses接口）"""
        if step_type == "start":
            self.show_info(f"🔄 开始: {message}")
        elif step_type == "complete":
            self.show_success(f"✅ 完成: {message}")
        elif step_type == "error":
            self.show_error(f"❌ 错误: {message}")
        else:
            self.show_info(message)
        
    def _get_terminal_width(self) -> int:
        """获取终端宽度 - 为了兼容VS Code xterm.js，使用固定宽度"""
        # VS Code的xterm.js环境下，shutil.get_terminal_size()可能返回不准确的值
        # 统一使用固定宽度以确保一致的显示效果
        return 80
            
    def _left_align_text(self, text: str, width: Optional[int] = None) -> str:
        """左对齐文本 - 替代居中对齐以兼容VS Code环境"""
        # 简单返回原文本，不进行任何对齐处理
        # 这样可以避免在VS Code xterm.js环境下的显示问题
        return text
    
    def _create_box(self, content: str, style: str = "double") -> str:
        """创建文本框 - 左对齐版本，兼容VS Code环境"""
        lines = content.split('\n')
        max_width = max(len(line) for line in lines) if lines else 0
        # 使用固定的合理宽度，避免依赖终端宽度检测
        box_width = min(max_width + 4, 76)  # 为边框预留4个字符，总宽度不超过76
        
        if style == "double":
            top = "╔" + "═" * (box_width - 2) + "╗"
            bottom = "╚" + "═" * (box_width - 2) + "╝"
            side = "║"
        else:  # single
            top = "┌" + "─" * (box_width - 2) + "┐"
            bottom = "└" + "─" * (box_width - 2) + "┘"
            side = "│"
        
        result = [top]
        for line in lines:
            # 左对齐内容，而不是居中
            if len(line) > box_width - 2:
                # 如果内容太长，截断处理
                padded_line = line[:box_width - 2]
            else:
                # 左对齐，右侧填充空格
                padded_line = line + " " * (box_width - 2 - len(line))
            result.append(f"{side}{padded_line}{side}")
        result.append(bottom)
        
        return '\n'.join(result)
    
    def clear_screen(self) -> None:
        """清屏"""
        if not self.quiet_mode:
            os.system('clear' if os.name == 'posix' else 'cls')
    
    def show_welcome(self, title: str = "SAGE安装向导") -> None:
        """
        显示欢迎信息 - 左对齐版本
        
        Args:
            title: 标题
        """
        if self.quiet_mode:
            return
        
        self.clear_screen()
        
        # 创建美化的标题
        welcome_text = f"🚀 {title}"
        box = self._create_box(welcome_text, "double")
        
        print("\n" * 2)
        print(box)
        print("\n" * 2)
    
    def show_section(self, title: str, description: str = "") -> None:
        """
        显示章节标题
        
        Args:
            title: 章节标题
            description: 描述信息
        """
        if self.quiet_mode:
            return
        
        print()
        section_text = f"📋 {title}"
        if description:
            section_text += f"\n{description}"
        
        box = self._create_box(section_text, "single")
        print(box)
        print()
    
    def show_progress_section(self, title: str, current_step: int, total_steps: int) -> None:
        """
        显示进度章节 - 左对齐版本
        
        Args:
            title: 章节标题  
            current_step: 当前步骤
            total_steps: 总步骤数
        """
        if self.quiet_mode:
            return
        
        print()
        
        # 创建进度条 - 使用固定宽度
        progress_percent = (current_step / total_steps) * 100
        progress_width = 40  # 固定进度条宽度
        filled = int(progress_width * current_step / total_steps)
        bar = "█" * filled + "░" * (progress_width - filled)
        
        section_text = f"📋 {title}"
        progress_text = f"进度: [{bar}] {progress_percent:.1f}% ({current_step}/{total_steps})"
        
        full_text = f"{section_text}\n{progress_text}"
        box = self._create_box(full_text, "single")
        print(box)
        print()
    
    def show_info(self, message: str) -> None:
        """显示信息"""
        print(f"ℹ️ {message}")
    
    def show_success(self, message: str) -> None:
        """显示成功消息"""
        print(f"✅ {message}")
    
    def show_warning(self, message: str) -> None:
        """显示警告"""
        print(f"⚠️ {message}")
    
    def show_error(self, message: str) -> None:
        """显示错误"""
        print(f"❌ {message}")
    
    def show_key_value(self, data: Dict[str, Any], title: str = "") -> None:
        """
        显示键值对信息
        
        Args:
            data: 键值对数据
            title: 可选标题
        """
        if self.quiet_mode:
            return
        
        if title:
            print(f"\n📋 {title}")
        
        # 计算最大键长度
        max_key_length = max(len(str(key)) for key in data.keys()) if data else 0
        
        for key, value in data.items():
            print(f"  {str(key):<{max_key_length}} | {value}")
    
    def show_progress_summary(self, summary: Dict[str, Any]) -> None:
        """
        显示进度摘要
        
        Args:
            summary: 进度摘要数据
        """
        if self.quiet_mode:
            return
        
        print("\n")
        summary_text = "📊 安装总结"
        
        # 创建摘要内容
        content_lines = [
            summary_text,
            "",
            f"项目     | 数值    ",
            "---------------",
            f"总步骤数   | {summary.get('total_steps', 0):<5}",
            f"✅ 成功   | {summary.get('completed', 0):<5}",
            f"❌ 失败   | {summary.get('failed', 0):<5}",
            f"⏱️ 总用时 | {summary.get('total_time', 0):.1f}秒",
            f"📈 成功率  | {summary.get('success_rate', 0):.1%} ",
            "",
        ]
        
        if summary.get('completed', 0) == summary.get('total_steps', 0) and summary.get('failed', 0) == 0:
            content_lines.append("✅ 🎉 安装成功完成！")
        elif summary.get('failed', 0) > 0:
            content_lines.append("❌ 安装过程中有失败项")
        
        content = '\n'.join(content_lines)
        box = self._create_box(content, "double")
        
        print(box)
        print()
    
    def show_menu(self, 
                  title: str, 
                  options: List[str], 
                  default: Optional[int] = None,
                  allow_custom: bool = False) -> int:
        """
        显示菜单并获取用户选择
        
        Args:
            title: 菜单标题
            options: 选项列表
            default: 默认选项（从1开始）
            allow_custom: 是否允许自定义输入
            
        Returns:
            用户选择的选项索引（从0开始），-1表示自定义输入
        """
        if self.quiet_mode and default is not None:
            return default - 1
        
        print(f"\n{title}")
        for i, option in enumerate(options, 1):
            marker = "👉" if default and i == default else "  "
            print(f"{marker} {i}. {option}")
        
        if allow_custom:
            print(f"   0. 自定义输入")
        
        print()
        
        while True:
            try:
                prompt = "请选择"
                if default:
                    prompt += f" (默认: {default})"
                prompt += ": "
                
                user_input = input(prompt).strip()
                
                # 处理默认值
                if not user_input and default is not None:
                    return default - 1
                
                choice = int(user_input)
                
                # 处理自定义输入
                if choice == 0 and allow_custom:
                    return -1
                
                # 验证选择范围
                if 1 <= choice <= len(options):
                    return choice - 1
                else:
                    print(f"❌ 请输入1-{len(options)}之间的数字")
                    
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n\n👋 安装已取消")
                sys.exit(0)
    
    def get_input(self, 
                  prompt: str, 
                  default: Optional[str] = None,
                  validator: Optional[Callable[[str], bool]] = None,
                  error_message: str = "输入无效，请重试") -> str:
        """
        获取用户输入
        
        Args:
            prompt: 提示信息
            default: 默认值
            validator: 验证函数
            error_message: 验证失败时的错误信息
            
        Returns:
            用户输入的字符串
        """
        if self.quiet_mode and default is not None:
            return default
        
        full_prompt = prompt
        if default:
            full_prompt += f" (默认: {default})"
        full_prompt += ": "
        
        while True:
            try:
                user_input = input(full_prompt).strip()
                
                # 使用默认值
                if not user_input and default is not None:
                    user_input = default
                
                # 验证输入
                if validator and not validator(user_input):
                    print(f"❌ {error_message}")
                    continue
                
                return user_input
                
            except KeyboardInterrupt:
                print("\n\n👋 安装已取消")
                sys.exit(0)
    
    def get_yes_no(self, 
                   prompt: str, 
                   default: Optional[bool] = None) -> bool:
        """
        获取是/否选择
        
        Args:
            prompt: 提示信息
            default: 默认值
            
        Returns:
            用户选择结果
        """
        if self.quiet_mode and default is not None:
            return default
        
        suffix = ""
        if default is True:
            suffix = " [Y/n]"
        elif default is False:
            suffix = " [y/N]"
        else:
            suffix = " [y/n]"
        
        full_prompt = f"{prompt}{suffix}: "
        
        while True:
            try:
                user_input = input(full_prompt).strip().lower()
                
                if not user_input and default is not None:
                    return default
                
                if user_input in ['y', 'yes', '是', '确定']:
                    return True
                elif user_input in ['n', 'no', '否', '取消']:
                    return False
                else:
                    print("❌ 请输入 y/yes 或 n/no")
                    
            except KeyboardInterrupt:
                print("\n\n👋 安装已取消")
                sys.exit(0)
    
    def show_info(self, message: str, icon: str = "ℹ️") -> None:
        """
        显示信息
        
        Args:
            message: 消息内容
            icon: 图标
        """
        if not self.quiet_mode:
            print(f"{icon} {message}")
    
    def show_warning(self, message: str) -> None:
        """
        显示警告
        
        Args:
            message: 警告消息
        """
        print(f"⚠️ {message}")
    
    def show_error(self, message: str) -> None:
        """
        显示错误
        
        Args:
            message: 错误消息
        """
        print(f"❌ {message}")
    
    def show_success(self, message: str) -> None:
        """
        显示成功消息
        
        Args:
            message: 成功消息
        """
        if not self.quiet_mode:
            print(f"✅ {message}")
    
    def show_table(self, 
                   headers: List[str], 
                   rows: List[List[str]], 
                   title: Optional[str] = None) -> None:
        """
        显示表格
        
        Args:
            headers: 表头
            rows: 行数据
            title: 表格标题
        """
        if self.quiet_mode:
            return
        
        if title:
            print(f"\n📊 {title}")
        
        # 计算列宽
        col_widths = [len(header) for header in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # 打印表头
        header_row = " | ".join(
            header.ljust(col_widths[i]) for i, header in enumerate(headers)
        )
        print(f"\n{header_row}")
        print("-" * len(header_row))
        
        # 打印数据行
        for row in rows:
            data_row = " | ".join(
                str(cell).ljust(col_widths[i]) 
                for i, cell in enumerate(row[:len(col_widths)])
            )
            print(data_row)
        print()
    
    def show_list(self, 
                  items: List[str], 
                  title: Optional[str] = None,
                  bullet: str = "•") -> None:
        """
        显示列表
        
        Args:
            items: 列表项
            title: 列表标题
            bullet: 项目符号
        """
        if self.quiet_mode:
            return
        
        if title:
            print(f"\n📝 {title}")
        
        for item in items:
            print(f"  {bullet} {item}")
        print()
    
    def show_key_value(self, 
                       data: Dict[str, Any], 
                       title: Optional[str] = None) -> None:
        """
        显示键值对
        
        Args:
            data: 键值对数据
            title: 标题
        """
        if self.quiet_mode:
            return
        
        if title:
            print(f"\n📋 {title}")
        
        max_key_length = max(len(str(key)) for key in data.keys()) if data else 0
        
        for key, value in data.items():
            print(f"  {str(key).ljust(max_key_length)}: {value}")
        print()
    
    def clear_screen(self) -> None:
        """清屏"""
        if not self.quiet_mode:
            os.system('cls' if os.name == 'nt' else 'clear')
    
    def pause(self, message: str = "按Enter键继续...") -> None:
        """
        暂停等待用户确认
        
        Args:
            message: 提示消息
        """
        if not self.quiet_mode:
            try:
                input(f"\n{message}")
            except KeyboardInterrupt:
                print("\n\n👋 安装已取消")
                sys.exit(0)
    
    def show_progress_summary(self, summary: Dict[str, Any]) -> None:
        """
        显示进度摘要
        
        Args:
            summary: 进度摘要数据
        """
        if self.quiet_mode:
            return
        
        print("\n" + "=" * 50)
        print("📊 安装总结")
        print("=" * 50)
        
        # 显示统计信息
        stats = [
            ["总步骤数", summary.get('total_steps', 0)],
            ["✅ 成功", summary.get('completed', 0)],
            ["❌ 失败", summary.get('failed', 0)],
            ["⏱️ 总用时", f"{summary.get('total_time', 0):.1f}秒"],
            ["📈 成功率", f"{summary.get('success_rate', 0):.1%}"]
        ]
        
        self.show_table(["项目", "数值"], stats)
        
        # 显示结果
        if summary.get('failed', 0) == 0:
            self.show_success("🎉 安装成功完成！")
        else:
            self.show_warning(f"安装过程中有 {summary.get('failed', 0)} 个步骤失败")


def create_simple_menu(title: str, options: List[str]) -> int:
    """
    创建简单菜单的便捷函数
    
    Args:
        title: 菜单标题
        options: 选项列表
        
    Returns:
        用户选择的索引（从0开始）
    """
    ui = UserInterface()
    return ui.show_menu(title, options)


def get_user_confirmation(message: str, default: bool = False) -> bool:
    """
    获取用户确认的便捷函数
    
    Args:
        message: 确认消息
        default: 默认值
        
    Returns:
        用户确认结果
    """
    ui = UserInterface()
    return ui.get_yes_no(message, default)
