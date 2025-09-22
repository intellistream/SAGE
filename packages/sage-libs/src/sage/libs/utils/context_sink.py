import os
import json
import threading
from typing import Optional, Iterator, List, Dict, Any
from pathlib import Path
from datetime import datetime
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.libs.context.model_context import ModelContext
import time

class ContextFileSink(SinkFunction):
    """
    ModelContext文件持久化Sink
    支持多种保存格式和组织策略
    """
    
    @staticmethod
    def get_default_template_directory() -> str:
        """
        获取默认的模板数据目录，始终在项目根目录下创建
        项目根目录被定义为当前工作目录
        """
        project_root = Path(os.getcwd())  # 获取当前工作目录
        template_data_dir = project_root / "data" / "model_context"
        template_data_dir.mkdir(parents=True, exist_ok=True)
        return str(template_data_dir)
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            Dict[str, Any]: 默认配置字典
        """
        return {
            "base_directory": None,  # None表示使用默认目录
            "stage_directory": "general",  # 处理阶段目录名
            "file_format": "json",  # "json", "jsonl"
            "organization": "date",  # "date", "sequence", "uuid"
            "max_files_per_dir": 1000,
            "create_index": True,
            "auto_create_dirs": True,
            "compress_old_files": False,  # 是否压缩旧文件
            "backup_index": True  # 是否备份索引文件
        }
    
    def __init__(self, config: Dict[str, Any], **kwargs):
        """
        初始化TemplateFileSink
        
        Args:
            config: 配置字典，包含所有设置项
                - base_directory: 基础保存目录，如果为None则使用默认目录
                - stage_directory: 处理阶段目录名，如 "questionbot", "retriever", "chief", "critic"
                - file_format: 文件格式 ("json", "jsonl")
                - organization: 文件组织方式 ("date", "sequence", "uuid")
                - max_files_per_dir: 每个目录最大文件数
                - create_index: 是否创建索引文件
                - auto_create_dirs: 是否自动创建目录
                - compress_old_files: 是否压缩旧文件
                - backup_index: 是否备份索引文件
            **kwargs: 其他参数（向后兼容）
        """
        super().__init__(**kwargs)

        # 合并配置
        self.config = self.get_default_config()
        if isinstance(config, dict):
            self.config.update(config)
        else:
            raise TypeError("Expected a dict for config, got {}".format(type(config)))
        if config:
            self.config.update(config)
        
        # 向后兼容：如果直接传递了参数，使用这些参数更新config
        legacy_params = {
            'base_directory': kwargs.get('base_directory'),
            'file_format': kwargs.get('file_format'),
            'organization': kwargs.get('organization'),
            'max_files_per_dir': kwargs.get('max_files_per_dir'),
            'create_index': kwargs.get('create_index'),
            'stage_directory': kwargs.get('stage_directory')
        }
        
        for key, value in legacy_params.items():
            if value is not None:
                self.config[key] = value
        
        # 构建完整的目录路径
        self._setup_directories()
        
        # 索引管理
        self.index_file = self.full_directory / "template_index.json"
        self.index_lock = threading.Lock()
        self.saved_count = 0
        
        # 初始化索引
        if self.config["create_index"] and not self.index_file.exists():
            self._initialize_index()

    def _setup_directories(self):
        """设置目录结构"""
        # 基础目录
        if self.config["base_directory"] is None:
            base_dir = self.get_default_template_directory()
        else:
            base_dir = self.config["base_directory"]
        
        self.base_directory = Path(base_dir)
        
        # 阶段目录
        stage_dir = self.config["stage_directory"]
        self.stage_directory = self.base_directory / stage_dir
        
        # 完整目录路径：./data/template_data/questionbot/
        self.full_directory = self.stage_directory
        
        # 自动创建目录
        if self.config["auto_create_dirs"]:
            self.full_directory.mkdir(parents=True, exist_ok=True)

    def runtime_init(self, ctx):
        """运行时初始化"""
        super().runtime_init(ctx)
        self.logger.info(f"TemplateFileSink runtime initialized with context: {ctx}")
        self.logger.info(f"Template base directory: {self.base_directory}")
        self.logger.info(f"Template stage directory: {self.stage_directory}")
        self.logger.info(f"Template full directory: {self.full_directory}")
        self.logger.info(f"File organization: {self.config['organization']}")
        self.logger.info(f"File format: {self.config['file_format']}")

    def _initialize_index(self):
        """初始化索引文件"""
        index_data = {
            "created_at": datetime.now().isoformat(),
            "total_templates": 0,
            "config": self.config.copy(),  # 保存完整配置
            "directory_structure": {
                "base_directory": str(self.base_directory),
                "stage_directory": str(self.stage_directory),
                "full_directory": str(self.full_directory)
            },
            "templates": {}
        }
        
        # 备份现有索引（如果存在）
        if self.config["backup_index"] and self.index_file.exists():
            backup_file = self.index_file.with_suffix(f'.backup_{int(time.time())}.json')
            try:
                import shutil
                shutil.copy2(self.index_file, backup_file)
                self.logger.info(f"Backed up existing index to {backup_file}")
            except Exception as e:
                self.logger.warning(f"Failed to backup index: {e}")
        
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    def _get_file_path(self, template: ModelContext) -> Path:
        """
        根据组织策略确定文件路径
        目录结构: base_directory/stage_directory/organization_structure/filename
        
        Args:
            template: ModelContext实例
            
        Returns:
            Path: 文件路径
        """
        organization = self.config["organization"]
        file_format = self.config["file_format"]
        max_files = self.config["max_files_per_dir"]
        
        if organization == "date":
            # 按日期组织: ./data/template_data/questionbot/2025/01/15/
            dt = datetime.fromtimestamp(template.timestamp / 1000)
            org_dir = self.full_directory / f"{dt.year:04d}" / f"{dt.month:02d}" / f"{dt.day:02d}"
            filename = f"template_{template.uuid}.{file_format}"
            
        elif organization == "sequence":
            # 按序列号组织: ./data/template_data/questionbot/seq_0000-0999/
            seq_range = (template.sequence // max_files) * max_files
            org_dir = self.full_directory / f"seq_{seq_range:06d}-{seq_range + max_files - 1:06d}"
            filename = f"template_{template.sequence:06d}_{template.uuid[:8]}.{file_format}"
            
        else:  # uuid organization
            # 按UUID前缀组织: ./data/template_data/questionbot/ab/cd/
            uuid_prefix1 = template.uuid[:2]
            uuid_prefix2 = template.uuid[2:4]
            org_dir = self.full_directory / uuid_prefix1 / uuid_prefix2
            filename = f"template_{template.uuid}.{file_format}"
        
        # 确保目录存在
        if self.config["auto_create_dirs"]:
            org_dir.mkdir(parents=True, exist_ok=True)
        
        return org_dir / filename

    def _update_index(self, template: ModelContext, file_path: Path):
        """更新索引文件"""
        if not self.config["create_index"]:
            return
        
        with self.index_lock:
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                # 更新索引信息
                index_data["total_templates"] += 1
                index_data["last_updated"] = datetime.now().isoformat()
                
                # 添加模板记录
                template_record = {
                    "uuid": template.uuid,
                    "sequence": template.sequence,
                    "timestamp": template.timestamp,
                    "file_path": str(file_path.relative_to(self.full_directory)),
                    "absolute_path": str(file_path),
                    "relative_to_base": str(file_path.relative_to(self.base_directory)),
                    "stage_directory": self.config["stage_directory"],
                    "raw_question_preview": template.raw_question[:100] if template.raw_question else None,
                    "has_response": bool(template.response),
                    "response_length": len(template.response) if template.response else 0,
                    "chunks_count": len(template.retriver_chunks) if template.retriver_chunks else 0,
                    "prompts_count": len(template.prompts) if template.prompts else 0,
                    "organization": self.config["organization"],
                    "file_format": self.config["file_format"],
                    "saved_at": datetime.now().isoformat()
                }
                
                index_data["templates"][template.uuid] = template_record
                
                # 保存更新后的索引
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                self.logger.error(f"Failed to update index: {e}")

    def execute(self, template: ModelContext) -> None:
        """
        保存ModelContext到文件
        
        Args:
            template: 要保存的ModelContext
        """
        try:
            # 确定文件路径
            file_path = self._get_file_path(template)
            
            # 保存模板
            if self.config["file_format"] == "json":
                template.save_to_file(str(file_path))
            elif self.config["file_format"] == "jsonl":
                # JSONL格式：每行一个JSON对象
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(template.to_json().replace('\n', '') + '\n')
            
            # 更新索引
            self._update_index(template, file_path)
            
            self.saved_count += 1
            
            self.logger.debug(f"Saved template {template.uuid} to {file_path}")
            
            # 每保存10个模板记录一次统计
            if self.saved_count % 10 == 0:
                self.logger.info(f"TemplateFileSink[{self.config['stage_directory']}]: "
                               f"{self.saved_count} templates saved to {self.full_directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to save template {template.uuid}: {e}")

    def set_stage_directory(self, stage_name: str):
        """
        动态设置阶段目录
        
        Args:
            stage_name: 新的阶段目录名
        """
        old_stage = self.config["stage_directory"]
        self.config["stage_directory"] = stage_name
        self._setup_directories()
        
        # 重新设置索引文件路径
        self.index_file = self.full_directory / "template_index.json"
        
        # 如果需要，初始化新的索引
        if self.config["create_index"] and not self.index_file.exists():
            self._initialize_index()
        
        self.logger.info(f"Stage directory changed from '{old_stage}' to '{stage_name}'")
        self.logger.info(f"New full directory: {self.full_directory}")

    def get_storage_info(self) -> Dict[str, Any]:
        """
        获取存储信息统计
        
        Returns:
            Dict[str, Any]: 存储统计信息
        """
        return {
            "config": self.config.copy(),
            "directory_structure": {
                "base_directory": str(self.base_directory),
                "stage_directory": str(self.stage_directory),
                "full_directory": str(self.full_directory)
            },
            "runtime_stats": {
                "saved_count": self.saved_count,
                "index_file": str(self.index_file),
                "index_exists": self.index_file.exists() if hasattr(self, 'index_file') else False,
                "directory_exists": self.full_directory.exists()
            }
        }

    def get_stage_statistics(self) -> Dict[str, Any]:
        """
        获取当前阶段的统计信息
        
        Returns:
            Dict[str, Any]: 阶段统计信息
        """
        try:
            if not self.index_file.exists():
                return {"error": "Index file does not exist"}
            
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            templates = list(index_data.get("templates", {}).values())
            
            # 统计信息
            stats = {
                "stage_directory": self.config["stage_directory"],
                "total_templates": len(templates),
                "with_response": sum(1 for t in templates if t.get("has_response")),
                "without_response": sum(1 for t in templates if not t.get("has_response")),
                "avg_response_length": 0,
                "avg_chunks": 0,
                "avg_prompts": 0,
                "date_range": {"earliest": None, "latest": None}
            }
            
            if templates:
                # 计算平均值
                response_lengths = [t.get("response_length", 0) for t in templates if t.get("has_response")]
                stats["avg_response_length"] = sum(response_lengths) / len(response_lengths) if response_lengths else 0
                
                stats["avg_chunks"] = sum(t.get("chunks_count", 0) for t in templates) / len(templates)
                stats["avg_prompts"] = sum(t.get("prompts_count", 0) for t in templates) / len(templates)
                
                # 时间范围
                timestamps = [t.get("timestamp", 0) for t in templates]
                stats["date_range"]["earliest"] = min(timestamps)
                stats["date_range"]["latest"] = max(timestamps)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get stage statistics: {e}")
            return {"error": str(e)}