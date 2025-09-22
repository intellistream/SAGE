import json
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

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
