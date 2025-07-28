#!/usr/bin/env python3
"""
容器化用户代码执行服务
"""

import docker
import tempfile
import os
import json
from pathlib import Path
from typing import Dict, Any
import shutil

class ContainerizedJobManager:
    """
    使用Docker容器隔离用户代码执行
    """
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.container_image = "sage-user-runtime:latest"
        
    def execute_user_pipeline(self, pipeline_config: Dict[str, Any], user_files: Dict[str, str]) -> Dict[str, Any]:
        """
        在容器中安全执行用户流水线
        
        Args:
            pipeline_config: 流水线配置
            user_files: 用户文件映射 {filename: content}
        """
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 准备用户文件
            user_dir = temp_path / "user_files"
            user_dir.mkdir()
            
            for filename, content in user_files.items():
                # 安全文件名检查
                if self._is_safe_filename(filename):
                    file_path = user_dir / filename
                    with open(file_path, 'w') as f:
                        f.write(content)
            
            # 准备配置文件
            config_file = temp_path / "pipeline_config.json"
            with open(config_file, 'w') as f:
                json.dump(pipeline_config, f)
            
            # 在容器中执行
            try:
                container = self.docker_client.containers.run(
                    image=self.container_image,
                    volumes={
                        str(temp_path): {'bind': '/app/workspace', 'mode': 'rw'}
                    },
                    working_dir='/app/workspace',
                    command=['python', '/app/run_pipeline.py', 'pipeline_config.json'],
                    remove=True,
                    network_mode='none',  # 禁用网络访问
                    mem_limit='512m',     # 限制内存
                    cpu_period=100000,    # CPU限制
                    cpu_quota=50000,      # 50% CPU
                    user='1000:1000',     # 非root用户
                    detach=True
                )
                
                # 等待容器完成
                result = container.wait()
                logs = container.logs().decode('utf-8')
                
                return {
                    "status": "success" if result['StatusCode'] == 0 else "error",
                    "exit_code": result['StatusCode'],
                    "logs": logs
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Container execution failed: {str(e)}"
                }
    
    def _is_safe_filename(self, filename: str) -> bool:
        """检查文件名是否安全"""
        # 禁止路径遍历
        if '..' in filename or filename.startswith('/'):
            return False
        
        # 只允许特定扩展名
        allowed_extensions = {'.py', '.txt', '.json', '.csv', '.yaml', '.yml'}
        extension = Path(filename).suffix.lower()
        
        return extension in allowed_extensions
