#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Issues管理工具配置管理器
"""

import argparse
import json
from pathlib import Path
from config import Config

class ConfigManager:
    def __init__(self):
        self.config = Config()
        self.config_file = self.config.metadata_path / "settings.json"
        self.settings = self._load_settings()
        
    def _load_settings(self):
        """加载设置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载设置文件失败: {e}")
        
        # 默认设置
        return {
            "sync_update_history": True,
            "auto_backup": True,
            "verbose_output": False
        }
    
    def _save_settings(self):
        """保存设置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            print(f"✅ 设置已保存到: {self.config_file}")
        except Exception as e:
            print(f"❌ 保存设置失败: {e}")
    
    def show_current_settings(self):
        """显示当前设置"""
        print("📋 当前配置:")
        print("=" * 40)
        
        print(f"📤 同步更新记录到GitHub: {'是' if self.settings.get('sync_update_history', True) else '否'}")
        print(f"💾 自动备份: {'是' if self.settings.get('auto_backup', True) else '否'}")
        print(f"🔍 详细输出: {'是' if self.settings.get('verbose_output', False) else '否'}")
        
        print()
        print("💡 说明:")
        if self.settings.get('sync_update_history', True):
            print("  • 更新记录将包含在同步到GitHub的内容中")
            print("  • 这样可以保持管理历史的连续性")
        else:
            print("  • 更新记录仅保存在本地")
            print("  • GitHub上只保存原始issue内容")
    
    def set_sync_update_history(self, enable):
        """设置是否同步更新记录"""
        self.settings['sync_update_history'] = enable
        self._save_settings()
        
        if enable:
            print("✅ 已启用更新记录同步到GitHub")
            print("   下次同步时，更新记录将包含在issue内容中")
        else:
            print("✅ 已禁用更新记录同步到GitHub")
            print("   下次同步时，只会上传原始issue内容")
    
    def set_auto_backup(self, enable):
        """设置是否自动备份"""
        self.settings['auto_backup'] = enable
        self._save_settings()
        
        print(f"✅ 自动备份功能已{'启用' if enable else '禁用'}")
    
    def set_verbose_output(self, enable):
        """设置详细输出"""
        self.settings['verbose_output'] = enable
        self._save_settings()
        
        print(f"✅ 详细输出已{'启用' if enable else '禁用'}")
    
    def interactive_config(self):
        """交互式配置"""
        print("🔧 交互式配置向导")
        print("=" * 30)
        print()
        
        # 更新记录同步设置
        print("📤 更新记录同步设置:")
        print("   将本地的issue更新记录同步到GitHub可以:")
        print("   ✅ 保持管理历史的连续性")
        print("   ✅ 让团队成员看到完整的管理过程")
        print("   ❌ 会在GitHub issue中增加额外内容")
        print()
        
        current = self.settings.get('sync_update_history', True)
        choice = input(f"是否同步更新记录到GitHub? (当前: {'是' if current else '否'}) [y/N]: ").strip().lower()
        
        if choice in ['y', 'yes', '是']:
            self.set_sync_update_history(True)
        elif choice in ['n', 'no', '否']:
            self.set_sync_update_history(False)
        else:
            print("保持当前设置")
        
        print()
        
        # 其他设置...
        print("💾 自动备份设置:")
        current_backup = self.settings.get('auto_backup', True)
        backup_choice = input(f"是否启用自动备份? (当前: {'是' if current_backup else '否'}) [Y/n]: ").strip().lower()
        
        if backup_choice in ['n', 'no', '否']:
            self.set_auto_backup(False)
        elif backup_choice in ['y', 'yes', '是', '']:
            self.set_auto_backup(True)
        else:
            print("保持当前设置")

def main():
    parser = argparse.ArgumentParser(description='Issues管理工具配置管理器')
    parser.add_argument('--show', action='store_true', help='显示当前配置')
    parser.add_argument('--sync-history', choices=['on', 'off'], help='设置是否同步更新记录')
    parser.add_argument('--auto-backup', choices=['on', 'off'], help='设置是否自动备份')
    parser.add_argument('--verbose', choices=['on', 'off'], help='设置是否详细输出')
    parser.add_argument('--interactive', action='store_true', help='交互式配置')
    
    args = parser.parse_args()
    
    config_manager = ConfigManager()
    
    if args.show:
        config_manager.show_current_settings()
    elif args.sync_history:
        config_manager.set_sync_update_history(args.sync_history == 'on')
    elif args.auto_backup:
        config_manager.set_auto_backup(args.auto_backup == 'on')
    elif args.verbose:
        config_manager.set_verbose_output(args.verbose == 'on')
    elif args.interactive:
        config_manager.interactive_config()
    else:
        # 默认显示当前设置
        config_manager.show_current_settings()
        print()
        print("💡 使用 --interactive 进行交互式配置")
        print("   或使用 --sync-history on/off 等参数直接设置")

if __name__ == '__main__':
    main()
