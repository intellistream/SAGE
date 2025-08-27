import os
import json
from typing import Optional, List, Tuple
from pathlib import Path
from datetime import datetime
from sage.core.api.function.source_function import SourceFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.libs.context.model_context import ModelContext

class ContextFileSource(SourceFunction):
    """
    从文件加载ModelContext的数据源
    每次execute读取一个模板文件并返回
    """
    
    @staticmethod
    def get_default_template_directory() -> str:
        """
        获取默认的模板数据目录，与TemplateFileSink保持一致
        """
        project_root = Path(os.getcwd())  # 获取当前工作目录
        template_data_dir = project_root / "data" / "template_data"
        return str(template_data_dir)
    
    def __init__(self, base_directory: str = None,
                 load_mode: str = "sequential",  # "sequential", "recent", "random"
                 time_range: Optional[Tuple[int, int]] = None,
                 sequence_range: Optional[Tuple[int, int]] = None,
                 include_pattern: Optional[str] = None,
                 auto_reset: bool = True, **kwargs):
        """
        初始化TemplateFileSource
        
        Args:
            base_directory: 模板文件基础目录，如果为None则使用默认目录
            load_mode: 加载模式 ("sequential", "recent", "random")
            time_range: 时间范围过滤 (start_timestamp, end_timestamp)
            sequence_range: 序列号范围过滤
            include_pattern: 文件名包含模式
            auto_reset: 当所有文件读完后是否自动重置到开始
        """
        super().__init__(**kwargs)
        
        # 如果没有指定base_directory，使用默认目录
        if base_directory is None:
            base_directory = self.get_default_template_directory()
        
        self.base_directory = Path(base_directory)
        self.load_mode = load_mode
        self.time_range = time_range
        self.sequence_range = sequence_range
        self.include_pattern = include_pattern
        self.auto_reset = auto_reset
        
        self.index_file = self.base_directory / "template_index.json"
        
        # 内部状态管理
        self.loaded_count = 0
        self.current_file_index = 0
        self.template_files = []
        self.index_data = None
        
        # 初始化文件列表
        self._initialize_file_list()
        
        # self.logger.info(f"ContextFileSource initialized: {base_directory}, mode: {load_mode}")
        # self.logger.info(f"Found {len(self.template_files)} template files")

    def _initialize_file_list(self):
        """初始化文件列表"""
        # 检查目录是否存在
        if not self.base_directory.exists():
            self.logger.warning(f"Template directory does not exist: {self.base_directory}")
            self.template_files = []
            return
        
        # 加载索引文件（如果存在）
        self.index_data = self._load_index()
        
        if self.load_mode == "recent" and self.index_data:
            # 基于索引按时间排序
            templates_info = list(self.index_data.get("templates", {}).values())
            templates_info.sort(key=lambda x: x["timestamp"], reverse=True)
            
            self.template_files = []
            for template_info in templates_info:
                file_path = self.base_directory / template_info["file_path"]
                if file_path.exists():
                    self.template_files.append(file_path)
        else:
            # 直接扫描文件系统
            self.template_files = self._find_template_files()
            
            if self.load_mode == "sequential":
                # 按文件修改时间排序
                self.template_files.sort(key=lambda f: f.stat().st_mtime)
            elif self.load_mode == "random":
                # 随机打乱
                import random
                random.shuffle(self.template_files)

    def _load_index(self) -> Optional[dict]:
        """加载索引文件"""
        if not self.index_file.exists():
            self.logger.debug(f"Index file not found: {self.index_file}")
            return None
        
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load index: {e}")
            return None

    def _find_template_files(self) -> List[Path]:
        """查找所有模板文件"""
        template_files = []
        
        # 递归搜索所有JSON文件
        for json_file in self.base_directory.rglob("*.json"):
            if json_file.name == "template_index.json":
                continue
            
            # 应用文件名过滤
            if self.include_pattern and self.include_pattern not in json_file.name:
                continue
            
            template_files.append(json_file)
        
        return template_files

    def _load_template_from_file(self, file_path: Path) -> Optional[ModelContext]:
        """从文件加载单个模板"""
        try:
            template = ModelContext.load_from_file(str(file_path))
            
            # 应用过滤条件
            if not self._filter_template(template):
                return None
                
            return template
        except Exception as e:
            self.logger.error(f"Failed to load template from {file_path}: {e}")
            return None

    def _filter_template(self, template: ModelContext) -> bool:
        """根据条件过滤单个模板"""
        # 时间范围过滤
        if self.time_range:
            start_time, end_time = self.time_range
            if not (start_time <= template.timestamp <= end_time):
                return False
        
        # 序列号范围过滤
        if self.sequence_range:
            start_seq, end_seq = self.sequence_range
            if not (start_seq <= template.sequence <= end_seq):
                return False
        
        return True

    def _get_next_file(self) -> Optional[Path]:
        """获取下一个要读取的文件"""
        if not self.template_files:
            return None
        
        # 检查是否已经读完所有文件
        if self.current_file_index >= len(self.template_files):
            if self.auto_reset:
                self.logger.info("All template files processed, resetting to beginning")
                self.current_file_index = 0
                
                # 如果是随机模式，重新洗牌
                if self.load_mode == "random":
                    import random
                    random.shuffle(self.template_files)
            else:
                self.logger.info("All template files processed, no more files to read")
                return None
        
        # 返回当前文件并递增索引
        file_path = self.template_files[self.current_file_index]
        self.current_file_index += 1
        
        return file_path

    def execute(self) -> Optional[ModelContext]:
        """
        读取下一个ModelContext
        
        Returns:
            Optional[ModelContext]: 加载的模板，如果没有更多文件则返回None
        """
        # 最多尝试读取10个文件（避免无限循环）
        max_attempts = 10
        attempts = 0
        
        while attempts < max_attempts:
            attempts += 1
            
            # 获取下一个文件
            file_path = self._get_next_file()
            
            if file_path is None:
                # 没有更多文件可读
                return None
            
            # 尝试加载模板
            template = self._load_template_from_file(file_path)
            
            if template is not None:
                self.loaded_count += 1
                self.logger.debug(f"Loaded template {template.uuid} from {file_path.name}")
                
                # 每加载10个模板记录一次统计
                if self.loaded_count % 10 == 0:
                    self.logger.info(f"ContextFileSource: {self.loaded_count} templates loaded")
                
                return template
            
            # 如果当前文件加载失败，继续尝试下一个文件
            self.logger.debug(f"Failed to load template from {file_path}, trying next file")
        
        # 尝试次数用完，返回None
        self.logger.warning(f"Failed to load template after {max_attempts} attempts")
        return None

    def reset(self):
        """重置数据源到初始状态"""
        self.current_file_index = 0
        self.loaded_count = 0
        self.logger.info("ContextFileSource reset to initial state")

    def skip_to_index(self, index: int):
        """跳转到指定的文件索引"""
        if 0 <= index < len(self.template_files):
            self.current_file_index = index
            self.logger.info(f"ContextFileSource skipped to index {index}")
        else:
            self.logger.warning(f"Invalid index {index}, valid range: 0-{len(self.template_files)-1}")

    def get_source_info(self) -> dict:
        """
        获取数据源信息
        
        Returns:
            dict: 数据源统计信息
        """
        return {
            "base_directory": str(self.base_directory),
            "load_mode": self.load_mode,
            "total_files": len(self.template_files),
            "current_index": self.current_file_index,
            "loaded_count": self.loaded_count,
            "directory_exists": self.base_directory.exists(),
            "index_exists": self.index_file.exists(),
            "auto_reset": self.auto_reset,
            "has_more_files": self.current_file_index < len(self.template_files)
        }

    def has_more_data(self) -> bool:
        """
        检查是否还有更多数据可读
        
        Returns:
            bool: 是否还有更多数据
        """
        if self.auto_reset:
            # 如果自动重置，总是有数据（除非没有文件）
            return len(self.template_files) > 0
        else:
            # 否则检查是否还有未读文件
            return self.current_file_index < len(self.template_files)

class TemplateIndexManager:
    """
    模板索引管理器，提供高级查询功能
    """
    
    def __init__(self, base_directory: str = None):
        if base_directory is None:
            base_directory = ContextFileSource.get_default_template_directory()
        
        self.base_directory = Path(base_directory)
        self.index_file = self.base_directory / "template_index.json"
    
    def search_templates(self, 
                        question_contains: Optional[str] = None,
                        has_response: Optional[bool] = None,
                        min_chunks: Optional[int] = None,
                        time_after: Optional[int] = None) -> List[dict]:
        """
        搜索模板记录
        
        Args:
            question_contains: 问题包含的文本
            has_response: 是否有响应
            min_chunks: 最小chunk数量
            time_after: 时间戳之后
            
        Returns:
            List[dict]: 匹配的模板记录
        """
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            templates = list(index_data.get("templates", {}).values())
            
            # 应用过滤条件
            if question_contains:
                templates = [t for t in templates 
                           if t.get("raw_question_preview") and 
                           question_contains.lower() in t["raw_question_preview"].lower()]
            
            if has_response is not None:
                templates = [t for t in templates 
                           if t.get("has_response") == has_response]
            
            if min_chunks is not None:
                templates = [t for t in templates 
                           if t.get("chunks_count", 0) >= min_chunks]
            
            if time_after is not None:
                templates = [t for t in templates 
                           if t.get("timestamp", 0) > time_after]
            
            return templates
            
        except Exception as e:
            logger = CustomLogger(__name__)
            logger.error(f"Failed to search templates: {e}")
            return []
    
    def get_statistics(self) -> dict:
        """获取模板统计信息"""
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            templates = list(index_data.get("templates", {}).values())
            
            stats = {
                "total_templates": len(templates),
                "with_response": sum(1 for t in templates if t.get("has_response")),
                "without_response": sum(1 for t in templates if not t.get("has_response")),
                "avg_chunks": sum(t.get("chunks_count", 0) for t in templates) / len(templates) if templates else 0,
                "earliest_timestamp": min(t.get("timestamp", 0) for t in templates) if templates else 0,
                "latest_timestamp": max(t.get("timestamp", 0) for t in templates) if templates else 0
            }
            
            return stats
            
        except Exception as e:
            logger = CustomLogger(__name__)
            logger.error(f"Failed to get statistics: {e}")
            return {}