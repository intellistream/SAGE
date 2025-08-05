#!/usr/bin/env python3
"""
SAGE 商业许可管理工具
Simple and elegant commercial license management
"""

import os
import sys
import json
import hashlib
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# 配置
SAGE_CONFIG_DIR = Path.home() / '.sage'
LICENSE_FILE = SAGE_CONFIG_DIR / 'license.key'
CONFIG_FILE = SAGE_CONFIG_DIR / 'config.json'

class SageLicense:
    """SAGE商业许可管理器"""
    
    def __init__(self):
        self.config_dir = SAGE_CONFIG_DIR
        self.license_file = LICENSE_FILE
        self.config_file = CONFIG_FILE
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
    
    def install_license(self, license_key: str) -> bool:
        """安装许可密钥"""
        try:
            # 验证密钥格式
            if not self._validate_key_format(license_key):
                print("❌ 无效的许可密钥格式")
                return False
            
            # 解析密钥信息
            license_info = self._parse_license_key(license_key)
            if not license_info:
                print("❌ 许可密钥解析失败")
                return False
            
            # 保存许可信息
            with open(self.license_file, 'w') as f:
                f.write(license_key)
            
            # 保存配置
            config = {
                'license_type': 'commercial',
                'installed_at': datetime.now().isoformat(),
                'expires_at': license_info.get('expires_at'),
                'features': license_info.get('features', [])
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print("✅ 商业许可安装成功!")
            print(f"   类型: {license_info.get('type', 'Commercial')}")
            print(f"   到期: {license_info.get('expires_at', 'N/A')}")
            print(f"   功能: {', '.join(license_info.get('features', []))}")
            
            return True
            
        except Exception as e:
            print(f"❌ 许可安装失败: {e}")
            return False
    
    def check_license(self) -> Dict[str, Any]:
        """检查当前许可状态"""
        # 检查环境变量
        env_key = os.getenv('SAGE_LICENSE_KEY')
        if env_key:
            info = self._parse_license_key(env_key)
            if info:
                return {
                    'has_license': True,
                    'source': 'environment',
                    'type': 'commercial',
                    **info
                }
        
        # 检查许可文件
        if self.license_file.exists():
            try:
                with open(self.license_file, 'r') as f:
                    file_key = f.read().strip()
                
                info = self._parse_license_key(file_key)
                if info:
                    return {
                        'has_license': True,
                        'source': 'file',
                        'type': 'commercial',
                        **info
                    }
            except:
                pass
        
        # 无许可，返回开源版
        return {
            'has_license': False,
            'source': 'none',
            'type': 'open-source'
        }
    
    def remove_license(self) -> bool:
        """移除许可"""
        try:
            if self.license_file.exists():
                self.license_file.unlink()
            if self.config_file.exists():
                self.config_file.unlink()
            print("✅ 许可已移除，切换到开源版本")
            return True
        except Exception as e:
            print(f"❌ 移除许可失败: {e}")
            return False
    
    def status(self) -> None:
        """显示许可状态"""
        info = self.check_license()
        
        print("🔍 SAGE 许可状态")
        print("=" * 30)
        print(f"类型: {info['type']}")
        print(f"来源: {info['source']}")
        
        if info['has_license']:
            print(f"到期时间: {info.get('expires_at', 'N/A')}")
            print(f"可用功能: {', '.join(info.get('features', []))}")
            
            # 检查是否即将过期
            expires_str = info.get('expires_at')
            if expires_str and expires_str != 'N/A':
                try:
                    expires = datetime.fromisoformat(expires_str)
                    days_left = (expires - datetime.now()).days
                    if days_left < 30:
                        print(f"⚠️  许可将在 {days_left} 天后过期")
                except:
                    pass
        else:
            print("功能: 开源版本功能")
            print("💡 获取商业版本: 联系sales@sage.com")
    
    def _validate_key_format(self, key: str) -> bool:
        """验证密钥格式"""
        # 简单格式检查: SAGE-COMM-XXXX-XXXX-XXXX
        parts = key.split('-')
        return len(parts) >= 3 and parts[0] == 'SAGE' and parts[1] == 'COMM'
    
    def _parse_license_key(self, key: str) -> Optional[Dict[str, Any]]:
        """解析许可密钥信息"""
        try:
            # 这里是简化的解析逻辑
            # 实际应该包含加密验证
            parts = key.split('-')
            
            if len(parts) < 5:
                return None
            
            # 解析基本信息
            license_type = parts[1]  # COMM
            version = parts[2]       # 版本
            
            # 模拟解析结果
            return {
                'type': 'Commercial',
                'version': version,
                'expires_at': (datetime.now() + timedelta(days=365)).isoformat(),
                'features': ['high-performance', 'enterprise-db', 'advanced-analytics']
            }
            
        except Exception:
            return None

def main():
    """主函数"""
    license_mgr = SageLicense()
    
    if len(sys.argv) < 2:
        print("SAGE 商业许可管理工具")
        print("")
        print("使用方法:")
        print("  sage-license install <license-key>  # 安装商业许可")
        print("  sage-license status                 # 查看许可状态")
        print("  sage-license remove                 # 移除许可")
        print("")
        print("示例:")
        print("  sage-license install SAGE-COMM-2024-ABCD-EFGH")
        return
    
    command = sys.argv[1]
    
    if command == 'install':
        if len(sys.argv) < 3:
            print("❌ 请提供许可密钥")
            print("用法: sage-license install <license-key>")
            return
        
        license_key = sys.argv[2]
        license_mgr.install_license(license_key)
    
    elif command == 'status':
        license_mgr.status()
    
    elif command == 'remove':
        license_mgr.remove_license()
    
    else:
        print(f"❌ 未知命令: {command}")
        print("可用命令: install, status, remove")

if __name__ == '__main__':
    main()
