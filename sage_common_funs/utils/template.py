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
    response: str = None
    retriver_chunks: List[str] = field(default_factory=list)
    prompts: List[Dict[str, str]] = field(default_factory=list)

    uuid: str = field(default_factory=lambda: str(uuid4()))




    def __str__(self) -> str:
        retriver_preview = "\n    ".join(self.retriver_chunks[:3]) + ("..." if len(self.retriver_chunks) > 3 else "")
        prompt_pairs = "\n    ".join(f"{role}: {content[:80]}{'...' if len(content) > 80 else ''}" for role, content in self.prompts)
        
        return (
            f"[AI_Template Debug Info]\n"
            f"🆔 UUID: {self.uuid}\n"
            f"🔢 Sequence: {self.sequence} | 🕒 Timestamp: {self.timestamp}\n"
            f"❓ Raw Question: {self.raw_question}\n"
            f"📚 Retriever Chunks ({len(self.retriver_chunks)}):\n    {retriver_preview}\n"
            f"🧾 Prompt Messages:\n    {prompt_pairs}\n"
            f"🎯 Flattened Prompt:\n    {self.prompt[:120]}{'...' if len(self.prompt) > 120 else ''}\n"
            f"💬 Answer:\n    {self.answer[:120]}{'...' if len(self.answer) > 120 else ''}"
        )