"""
结果加载器 - 负责读取和解析实验结果 JSON 文件
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List


class ResultLoader:
    """实验结果加载器
    
    功能：
    1. 扫描目录下所有 JSON 文件
    2. 解析 JSON 文件内容
    3. 验证数据格式
    4. 提供统一的数据访问接口
    """
    
    def __init__(self, folder_path: str):
        """初始化结果加载器
        
        Args:
            folder_path: 实验结果文件夹路径
        """
        self.folder_path = Path(folder_path)
        if not self.folder_path.exists():
            raise FileNotFoundError(f"结果文件夹不存在: {folder_path}")
        
        self.results: List[Dict[str, Any]] = []
        self._load_all_results()
    
    def _load_all_results(self) -> None:
        """加载文件夹下所有 JSON 结果文件"""
        json_files = list(self.folder_path.rglob("*.json"))
        
        if not json_files:
            print(f"⚠️  未在 {self.folder_path} 找到任何 JSON 文件")
            return
        
        print(f"📂 找到 {len(json_files)} 个结果文件")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 添加文件路径信息
                    data['_file_path'] = str(json_file)
                    data['_file_name'] = json_file.name
                    self.results.append(data)
                    print(f"✅ 加载成功: {json_file.name}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析失败: {json_file.name} - {e}")
            except Exception as e:
                print(f"❌ 加载失败: {json_file.name} - {e}")
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """获取所有加载的结果
        
        Returns:
            List[Dict]: 所有实验结果列表
        """
        return self.results
    
    def get_result_by_task_id(self, task_id: str) -> Dict[str, Any] | None:
        """根据 task_id 获取单个结果
        
        Args:
            task_id: 任务ID（如 "conv-26"）
        
        Returns:
            Dict | None: 匹配的结果，未找到返回 None
        """
        for result in self.results:
            if result.get("experiment_info", {}).get("task_id") == task_id:
                return result
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """获取加载结果的摘要信息
        
        Returns:
            Dict: 包含文件数量、任务列表等信息
        """
        task_ids = [
            r.get("experiment_info", {}).get("task_id", "unknown")
            for r in self.results
        ]
        
        return {
            "total_files": len(self.results),
            "task_ids": task_ids,
            "folder_path": str(self.folder_path),
        }
    
    def validate_result_format(self, result: Dict[str, Any]) -> bool:
        """验证结果文件格式是否正确
        
        Args:
            result: 单个结果字典
        
        Returns:
            bool: 格式正确返回 True，否则返回 False
        """
        required_keys = ["experiment_info", "test_results"]
        
        for key in required_keys:
            if key not in result:
                print(f"❌ 缺少必需字段: {key}")
                return False
        
        # 验证 test_results 结构
        test_results = result.get("test_results", [])
        if not isinstance(test_results, list):
            print("❌ test_results 应为列表")
            return False
        
        return True
