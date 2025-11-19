# agent/profile/profile.py
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaseProfile:
    """ """

    name: str = "BaseAgent"  # 人格名
    role: str = "general assistant"  # 角色定位
    goals: list[str] = field(default_factory=list)  # 长期/核心目标
    tasks: list[str] = field(default_factory=list)  # 常见任务模板
    backstory: str = ""  # 人设背景

    # 输出偏好
    language: str = "zh"  # "zh" / "en" / ...
    tone: str = "concise"  # "concise" / "detailed" / "socratic" / ...

    # ========== 便捷方法 ==========
    def render_system_prompt(self) -> str:
        """把 Profile 渲染为 System Prompt 一段文本，给 LLM/Planner 使用"""
        goals_txt = "\n".join(f"- {g}" for g in self.goals) or "- （未指定）"
        tasks_txt = "\n".join(f"- {t}" for t in self.tasks) or "- （未指定）"

        return (
            f"You are **{self.name}**, acting as **{self.role}**.\n"
            f"Language: {self.language}\n"
            f"Tone: {self.tone}\n\n"
            f"Backstory:\n{self.backstory or '(none)'}\n\n"
            f"Goals:\n{goals_txt}\n\n"
            f"Typical Tasks:\n{tasks_txt}\n\n"
            "Guidance:\n"
            "- Stay aligned with the role and goals.\n"
            "- Prefer structured, verifiable outputs.\n"
        )

    def to_dict(self) -> dict[str, Any]:
        """导出字典（方便存储/打印/日志）。"""
        return {
            "name": self.name,
            "role": self.role,
            "goals": list(self.goals),
            "tasks": list(self.tasks),
            "backstory": self.backstory,
            "language": self.language,
            "tone": self.tone,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseProfile":
        """从字典创建（若想从 JSON 加载就先 json.load 再丢进来）。"""
        return cls(
            name=data.get("name", "BaseAgent"),
            role=data.get("role", "general assistant"),
            goals=list(data.get("goals", [])),
            tasks=list(data.get("tasks", [])),
            backstory=data.get("backstory", ""),
            language=data.get("language", "zh"),
            tone=data.get("tone", "concise"),
        )

    def merged(self, **overrides) -> "BaseProfile":
        """
        轻量“覆写”方法：在现有人格上快速改几个字段生成新的人格。
        用法： coder = base.merged(name="Coder", role="software engineer")
        """
        d = self.to_dict()
        d.update({k: v for k, v in overrides.items() if v is not None})
        return BaseProfile.from_dict(d)

    def execute(self, data: Any = None) -> str:
        """
        将 Profile 映射为 Prompt。
        data 允许传入轻量覆写（可选）：如 {"tone": "detailed"}。
        """
        if isinstance(data, dict) and data:
            # 支持在 execute 调用时做一次性覆写
            return self.merged(**data).render_system_prompt()
        return self.render_system_prompt()
