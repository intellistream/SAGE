import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Tuple, Optional
from enum import Enum
from uuid import uuid4
import time
from pathlib import Path

from .quality_label import QualityLabel

@dataclass
class CriticEvaluation:
    """Critic评估结果"""
    label: QualityLabel
    confidence: float  # 0.0-1.0
    reasoning: str
    specific_issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    should_return_to_chief: bool = False
    ready_for_output: bool = False