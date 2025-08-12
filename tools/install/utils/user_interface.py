"""
SAGE用户界面工具
提供交互式菜单、用户输入处理和信息显示功能
"""

import os
import sys
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
        
    def show_welcome(self, title: str = "SAGE安装向导") -> None:
        """
        显示欢迎信息
        
        Args:
            title: 标题
        """
        if self.quiet_mode:
            return
            
        width = max(50, len(title) + 10)
        print("=" * width)
        print(f"🚀 {title}".center(width))
        print("=" * width)
        print()
    
    def show_section(self, title: str, description: str = "") -> None:
        """
        显示章节标题
        
        Args:
            title: 章节标题
            description: 描述信息
        """
        if self.quiet_mode:
            return
            
        print(f"\n📋 {title}")
        print("-" * (len(title) + 5))
        if description:
            print(f"{description}\n")
    
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
