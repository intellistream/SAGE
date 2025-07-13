import os
import json
import threading
from typing import Optional, Iterator, List
from pathlib import Path
from datetime import datetime
from sage_core.function.sink_function import SinkFunction
from sage_core.function.source_function import SourceFunction
from sage_utils.custom_logger import CustomLogger
from sage_library.utils.template import AI_Template


class TemplateFileSink(SinkFunction):
    """
    AI_Template文件持久化Sink
    支持多种保存格式和组织策略
    """
    
    @staticmethod
    def get_default_template_directory() -> str:
        """
        获取默认的模板数据目录，始终在项目根目录下创建
        项目根目录被定义为当前工作目录
        """
        project_root = Path(os.getcwd())  # 获取当前工作目录
        template_data_dir = project_root / "data" / "template_data"
        template_data_dir.mkdir(parents=True, exist_ok=True)
        return str(template_data_dir)
    
    def __init__(self, base_directory: str = None, 
                 file_format: str = "json",
                 organization: str = "date",  # "date", "sequence", "uuid"
                 max_files_per_dir: int = 1000,
                 create_index: bool = True, **kwargs):
        """
        初始化TemplateFileSink
        
        Args:
            base_directory: 基础保存目录，如果为None则使用默认目录 ./data/template_data
            file_format: 文件格式 ("json", "jsonl")
            organization: 文件组织方式
            max_files_per_dir: 每个目录最大文件数
            create_index: 是否创建索引文件
        """
        super().__init__(**kwargs)
        
        # 如果没有指定base_directory，使用默认目录
        if base_directory is None:
            base_directory = self.get_default_template_directory()
        
        self.base_directory = Path(base_directory)
        self.file_format = file_format
        self.organization = organization
        self.max_files_per_dir = max_files_per_dir
        self.create_index = create_index
        
        self.base_directory.mkdir(parents=True, exist_ok=True)
        
        # 索引管理
        self.index_file = self.base_directory / "template_index.json"
        self.index_lock = threading.Lock()
        self.saved_count = 0
        
        # 初始化索引
        if self.create_index and not self.index_file.exists():
            self._initialize_index()

    
    def runtime_init(self, ctx):
        super().runtime_init(ctx)
        self.logger.info(f"TemplateFileSink runtime initialized with context: {ctx}")
        self.logger.info(f"Template data directory: {self.base_directory}")


    def _initialize_index(self):
        """初始化索引文件"""
        index_data = {
            "created_at": datetime.now().isoformat(),
            "total_templates": 0,
            "organization": self.organization,
            "file_format": self.file_format,
            "base_directory": str(self.base_directory),
            "templates": {}
        }
        
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    def _get_file_path(self, template: AI_Template) -> Path:
        """
        根据组织策略确定文件路径
        
        Args:
            template: AI_Template实例
            
        Returns:
            Path: 文件路径
        """
        if self.organization == "date":
            # 按日期组织: YYYY/MM/DD/
            dt = datetime.fromtimestamp(template.timestamp / 1000)
            date_dir = self.base_directory / f"{dt.year:04d}" / f"{dt.month:02d}" / f"{dt.day:02d}"
            filename = f"template_{template.uuid}.{self.file_format}"
            final_dir = date_dir
            
        elif self.organization == "sequence":
            # 按序列号组织: seq_0000-0999/, seq_1000-1999/
            seq_range = (template.sequence // self.max_files_per_dir) * self.max_files_per_dir
            seq_dir = self.base_directory / f"seq_{seq_range:06d}-{seq_range + self.max_files_per_dir - 1:06d}"
            filename = f"template_{template.sequence:06d}_{template.uuid[:8]}.{self.file_format}"
            final_dir = seq_dir
            
        else:  # uuid organization
            # 按UUID前缀组织: ab/, cd/, ef/
            uuid_prefix = template.uuid[:2]
            uuid_dir = self.base_directory / uuid_prefix
            filename = f"template_{template.uuid}.{self.file_format}"
            final_dir = uuid_dir
        
        final_dir.mkdir(parents=True, exist_ok=True)
        return final_dir / filename

    def _update_index(self, template: AI_Template, file_path: Path):
        """更新索引文件"""
        if not self.create_index:
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
                    "file_path": str(file_path.relative_to(self.base_directory)),
                    "absolute_path": str(file_path),
                    "raw_question_preview": template.raw_question[:100] if template.raw_question else None,
                    "has_response": bool(template.response),
                    "chunks_count": len(template.retriver_chunks) if template.retriver_chunks else 0,
                    "organization": self.organization,
                    "file_format": self.file_format
                }
                
                index_data["templates"][template.uuid] = template_record
                
                # 保存更新后的索引
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                self.logger.error(f"Failed to update index: {e}")

    def execute(self, template: AI_Template) -> None:
        """
        保存AI_Template到文件
        
        Args:
            template: 要保存的AI_Template
        """
        try:
            # 确定文件路径
            file_path = self._get_file_path(template)
            
            # 保存模板
            if self.file_format == "json":
                template.save_to_file(str(file_path))
            elif self.file_format == "jsonl":
                # JSONL格式：每行一个JSON对象
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(template.to_json().replace('\n', '') + '\n')
            
            # 更新索引
            self._update_index(template, file_path)
            
            self.saved_count += 1
            
            self.logger.debug(f"Saved template {template.uuid} to {file_path}")
            
            # 每保存10个模板记录一次统计
            if self.saved_count % 10 == 0:
                self.logger.info(f"TemplateFileSink: {self.saved_count} templates saved to {self.base_directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to save template {template.uuid}: {e}")

    def get_storage_info(self) -> dict:
        """
        获取存储信息统计
        
        Returns:
            dict: 存储统计信息
        """
        return {
            "base_directory": str(self.base_directory),
            "organization": self.organization,
            "file_format": self.file_format,
            "saved_count": self.saved_count,
            "index_file": str(self.index_file),
            "index_exists": self.index_file.exists() if hasattr(self, 'index_file') else False
        }