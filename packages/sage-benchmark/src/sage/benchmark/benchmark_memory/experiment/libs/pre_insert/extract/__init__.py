"""Extract Action 子模块

信息抽取相关的 Action 策略。
"""

from .entity import EntityExtractAction
from .keyword import KeywordExtractAction
from .noun import NounExtractAction
from .triple import TripleExtractAction

__all__ = [
    "KeywordExtractAction",
    "EntityExtractAction",
    "NounExtractAction",
    "TripleExtractAction",
]
