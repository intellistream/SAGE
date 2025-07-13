from dataclasses import dataclass, field
from typing import Any, List, Dict, Tuple
from uuid import uuid4
import time
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