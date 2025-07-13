import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Tuple, Optional
from uuid import uuid4
import time
from pathlib import Path

@dataclass
class AI_Template:
    # Packet metadata
    sequence: int = 0
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    # Generator content
    raw_question: str = None
    retriver_chunks: List[str] = field(default_factory=list)
    prompts: List[Dict[str, str]] = field(default_factory=list)
    response: str = None
    uuid: str = field(default_factory=lambda: str(uuid4()))

    def __str__(self) -> str:
        """
        格式化显示AI_Template内容，用于terminal输出
        """
        # 时间格式化
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', 
                                     time.localtime(self.timestamp / 1000))
        
        # 构建输出字符串
        output_lines = []
        output_lines.append("=" * 80)
        output_lines.append(f"🤖 AI Processing Result [ID: {self.uuid[:8]}]")
        output_lines.append(f"📅 Time: {timestamp_str} | Sequence: {self.sequence}")
        output_lines.append("=" * 80)
        
        # 原始问题
        if self.raw_question:
            output_lines.append(f"❓ Original Question:")
            output_lines.append(f"   {self.raw_question}")
            output_lines.append("")
        
        # 检索到的信息片段
        if self.retriver_chunks:
            output_lines.append(f"📚 Retrieved Information ({len(self.retriver_chunks)} sources):")
            for i, chunk in enumerate(self.retriver_chunks[:3], 1):  # 只显示前3个
                # 截取片段内容
                preview = chunk[:150] + "..." if len(chunk) > 150 else chunk
                output_lines.append(f"   [{i}] {preview}")
            
            if len(self.retriver_chunks) > 3:
                output_lines.append(f"   ... and {len(self.retriver_chunks) - 3} more sources")
            output_lines.append("")
        
        # AI响应
        if self.response:
            output_lines.append(f"🎯 AI Response:")
            # 格式化响应，添加适当的缩进
            response_lines = self.response.split('\n')
            for line in response_lines:
                output_lines.append(f"   {line}")
            output_lines.append("")
        
        # 处理步骤摘要
        if self.prompts:
            system_prompts = [p for p in self.prompts if p.get('role') == 'system']
            if system_prompts:
                output_lines.append(f"⚙️  Processing Steps: {len(system_prompts)} phases completed")
                output_lines.append("")
        
        output_lines.append("=" * 80)
        
        return '\n'.join(output_lines)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，用于序列化
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AI_Template':
        """
        从字典创建AI_Template实例
        """
        return cls(**data)

    def to_json(self) -> str:
        """
        转换为JSON字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'AI_Template':
        """
        从JSON字符串创建AI_Template实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save_to_file(self, file_path: str) -> None:
        """
        保存到文件
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, file_path: str) -> 'AI_Template':
        """
        从文件加载
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())